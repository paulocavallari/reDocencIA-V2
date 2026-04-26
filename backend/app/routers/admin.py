from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import DATABASE_URL, engine, get_db, is_postgres_url, is_sqlite_url, uses_transaction_pooler
from app.models import CurriculumData, Setting, User
from app.schemas import SettingModelsUpdate, SettingUpdate
from app.services.curriculum_import_state import get_import_state
from app.security import require_admin
from app.services.pdf_parser import parse_curriculum_pdf


router = APIRouter(prefix="/api/admin", tags=["admin"])
UPLOADS_DIR = Path(os.getenv("REDOCENCIA_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads"))


def upsert_setting(db: Session, key: str, value: str | None):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting is None:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
    db.refresh(setting)
    return setting


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 6:
        return "*" * len(secret)
    return f"{secret[:3]}{'*' * (len(secret) - 6)}{secret[-3:]}"


def get_database_engine_label(database_url: str) -> str:
    if is_postgres_url(database_url):
        return "postgres"
    if is_sqlite_url(database_url):
        return "sqlite"
    return "unknown"


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    settings = {item.key: item.value for item in db.query(Setting).all()}
    openrouter_models = [settings.get("openrouter_model_1"), settings.get("openrouter_model_2"), settings.get("openrouter_model_3")]
    primary_model = next((model for model in openrouter_models if model), None) or settings.get("openrouter_model")
    record_count = db.query(CurriculumData).count()
    guide_files = sorted({item.source_file for item in db.query(CurriculumData.source_file).all() if item.source_file})
    disciplines = sorted({item.disciplina for item in db.query(CurriculumData.disciplina).all() if item.disciplina})
    import_state = get_import_state().copy()
    return {
        "openrouter_api_key": mask_secret(settings.get("openrouter_api_key")),
        "openrouter_model": primary_model,
        "openrouter_models": openrouter_models,
        "guide_path": settings.get("guide_path"),
        "guide_uploaded": bool(settings.get("guide_path")),
        "guide_files": guide_files,
        "curriculum_disciplines": disciplines,
        "curriculum_records": record_count,
        "curriculum_import": import_state,
    }


@router.get("/db-status")
def get_db_status(_: User = Depends(require_admin)):
    parsed = urlsplit(DATABASE_URL)
    engine_name = get_database_engine_label(DATABASE_URL)
    database_name = Path(parsed.path).name if parsed.path else None
    host = parsed.hostname if parsed.hostname else "local file"
    is_supabase = "supabase" in (host or "")
    pool_mode = "transaction" if uses_transaction_pooler(DATABASE_URL) else "session"
    ssl_mode = os.getenv("REDOCENCIA_DB_SSLMODE", "require") if engine_name == "postgres" else "off"
    connection_ok = False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        connection_ok = True
    except Exception:
        connection_ok = False

    return {
        "engine": engine_name,
        "is_supabase": is_supabase,
        "host": host,
        "database_name": database_name,
        "pool_mode": pool_mode,
        "ssl": ssl_mode,
        "connection_ok": connection_ok,
    }


@router.put("/settings/api-key")
def save_api_key(payload: SettingUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    setting = upsert_setting(db, "openrouter_api_key", payload.value)
    return {"message": "Chave salva com sucesso.", "key": setting.key}


@router.put("/settings/model")
def save_model(payload: SettingUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    value = payload.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Informe ao menos um modelo válido.")

    setting = upsert_setting(db, "openrouter_model", value)
    upsert_setting(db, "openrouter_model_1", value)
    return {"message": "Modelo salvo com sucesso.", "key": setting.key, "value": setting.value}


@router.put("/settings/models")
def save_models(payload: SettingModelsUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    cleaned: list[str] = []
    for value in payload.values:
        normalized = (value or "").strip()
        if normalized:
            cleaned.append(normalized)

    deduped: list[str] = []
    seen: set[str] = set()
    for model in cleaned:
        if model in seen:
            continue
        seen.add(model)
        deduped.append(model)

    if not deduped:
        raise HTTPException(status_code=400, detail="Informe ao menos um modelo válido.")

    selected = deduped[:3]
    for index in range(1, 4):
        model_value = selected[index - 1] if index <= len(selected) else None
        upsert_setting(db, f"openrouter_model_{index}", model_value)

    upsert_setting(db, "openrouter_model", selected[0])
    return {"message": "Modelos salvos com sucesso.", "values": selected}


@router.post("/upload-guide")
async def upload_guide(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOADS_DIR / file.filename
    content = await file.read()
    destination.write_bytes(content)

    parsed_rows = parse_curriculum_pdf(destination)
    if not parsed_rows:
        raise HTTPException(status_code=400, detail="Nenhum dado curricular foi extraído do PDF.")

    discipline = parsed_rows[0]["disciplina"]
    imported_levels = sorted({row["nivel_ensino"] for row in parsed_rows})
    db.query(CurriculumData).filter(
        CurriculumData.disciplina == discipline,
        CurriculumData.nivel_ensino.in_(imported_levels),
    ).delete(synchronize_session=False)
    for row in parsed_rows:
        db.add(CurriculumData(**row))
    db.commit()

    upsert_setting(db, "guide_path", str(destination))
    return {"message": "Guia importado com sucesso.", "records": len(parsed_rows), "disciplina": discipline}
