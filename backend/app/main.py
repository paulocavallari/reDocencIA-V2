from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect
from sqlalchemy import distinct

from app.database import Base, DATABASE_URL, SessionLocal, engine, is_postgres_url, is_sqlite_url
from app.models import CurriculumData, Setting, User
from app.routers import admin, ai, auth, curriculum, plans
from app.security import hash_password
from app.services.curriculum_import_state import get_import_state, update_import_state
from app.services.pdf_parser import GUIDE_PREFIX, parse_curriculum_pdf


app = FastAPI(title="redocêncIA API", version="0.1.0")
IMPORT_LOCK = Lock()
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
app.state.startup_error = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def discover_guide_files(workspace_root: Path | None) -> list[Path]:
    guide_files: dict[str, Path] = {}
    search_roots = []
    if workspace_root is not None:
        search_roots.append(workspace_root)
    uploads_root = Path(__file__).resolve().parent / "uploads"
    if uploads_root.exists():
        search_roots.append(uploads_root)

    for root in search_roots:
        for candidate in root.glob(f"{GUIDE_PREFIX}*.pdf"):
            guide_files[candidate.name.lower()] = candidate
    return list(guide_files.values())


def seed_defaults() -> None:
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user is None:
            db.add(
                User(
                    nome="Administrador",
                    email="admin@redocencia.com",
                    username="admin",
                    password_hash=hash_password("admin"),
                    is_admin=True,
                )
            )
        elif admin_user.email.endswith(".local"):
            admin_user.email = "admin@redocencia.com"

        for key, value in {
            "openrouter_model": "liquid/lfm-2.5-1.2b-thinking:free",
            "openrouter_model_1": "liquid/lfm-2.5-1.2b-thinking:free",
            "openrouter_model_2": "liquid/lfm-2.5-1.2b-instruct:free",
            "openrouter_model_3": "inclusionai/ling-2.6-flash:free",
            "guide_path": None,
        }.items():
            if db.query(Setting).filter(Setting.key == key).first() is None:
                db.add(Setting(key=key, value=value))

        db.commit()
    finally:
        db.close()


def import_curriculum_data(guide_paths: list[Path], reset: bool = False) -> None:
    if not guide_paths:
        update_import_state(status="idle", total_guides=0, processed_guides=0, completed_at=datetime.utcnow().isoformat())
        return

    if not IMPORT_LOCK.acquire(blocking=False):
        return

    update_import_state(
        status="in_progress",
        total_guides=len(guide_paths),
        processed_guides=0,
        last_error=None,
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )

    db = SessionLocal()
    try:
        if reset:
            db.query(CurriculumData).delete(synchronize_session=False)
            db.commit()

        imported_paths: list[str] = []
        seen_keys: set[tuple] = set()
        for index, guide_path in enumerate(guide_paths, start=1):
            parsed_rows = parse_curriculum_pdf(guide_path)
            for row in parsed_rows:
                row_key = (
                    row["disciplina"],
                    row["ano_serie"],
                    row["bimestre"],
                    row["objetos_conhecimento"],
                    row["habilidade_codigo"],
                    row["skill_category"],
                )
                if row_key in seen_keys:
                    continue
                seen_keys.add(row_key)
                db.add(CurriculumData(**row))
            db.commit()
            imported_paths.append(str(guide_path))
            update_import_state(processed_guides=index)

        guide_setting = db.query(Setting).filter(Setting.key == "guide_path").first()
        manifest = "\n".join(imported_paths) if imported_paths else None
        if guide_setting is None:
            db.add(Setting(key="guide_path", value=manifest))
        else:
            guide_setting.value = manifest
        db.commit()
        update_import_state(status="completed", completed_at=datetime.utcnow().isoformat())
    except Exception as error:
        db.rollback()
        update_import_state(status="failed", last_error=str(error), completed_at=datetime.utcnow().isoformat())
        raise
    finally:
        db.close()
        IMPORT_LOCK.release()


def schedule_curriculum_import(guide_paths: list[Path], reset: bool = False) -> None:
    state = get_import_state()
    if state.get("status") == "in_progress":
        return

    worker = Thread(target=import_curriculum_data, args=(guide_paths, reset), daemon=True)
    worker.start()


def curriculum_requires_rebuild(expected_guides: list[Path]) -> bool:
    inspector = inspect(engine)
    if "curriculum_data" not in inspector.get_table_names():
        return False

    columns = {column["name"] for column in inspector.get_columns("curriculum_data")}
    if "skill_category" not in columns:
        return True

    db = SessionLocal()
    try:
        has_curriculum = db.query(CurriculumData).first() is not None
        if not expected_guides:
            return False
        if not has_curriculum:
            return True

        guide_manifest = db.query(Setting).filter(Setting.key == "guide_path").first()
        current_sources = set((guide_manifest.value or "").splitlines()) if guide_manifest and guide_manifest.value else set()
        expected_sources = {str(path) for path in expected_guides}
        if current_sources != expected_sources:
            return True

        missing_category = any(
            db.query(CurriculumData).filter(CurriculumData.skill_category == category).first() is None
            for category in ["habilidade_priorizada", "conhecimento_previo", "habilidade_relacionada"]
        )
        return missing_category
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    workspace_guides = discover_guide_files(WORKSPACE_ROOT)
    Base.metadata.info["workspace_guides"] = workspace_guides
    try:
        Base.metadata.create_all(bind=engine)
        seed_defaults()

        needs_rebuild = curriculum_requires_rebuild(workspace_guides)
        if needs_rebuild:
            schedule_curriculum_import(workspace_guides, reset=True)
        else:
            update_import_state(
                status="completed" if workspace_guides else "idle",
                total_guides=len(workspace_guides),
                processed_guides=len(workspace_guides),
                last_error=None,
                completed_at=datetime.utcnow().isoformat() if workspace_guides else None,
            )
    except Exception as error:
        app.state.startup_error = str(error)


@app.get("/api/health")
def health_check():
    if is_postgres_url(DATABASE_URL):
        db_engine = "postgres"
    elif is_sqlite_url(DATABASE_URL):
        db_engine = "sqlite"
    else:
        db_engine = "unknown"

    startup_error = getattr(app.state, "startup_error", None)
    status_value = "degraded" if startup_error else "ok"
    return {"status": status_value, "db_engine": db_engine, "startup_error": startup_error}


app.include_router(auth.router)
app.include_router(curriculum.router)
app.include_router(ai.router)
app.include_router(plans.router)
app.include_router(admin.router)


if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")


    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_app(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")

        requested_path = FRONTEND_DIST_DIR / full_path
        if requested_path.is_file():
            return FileResponse(requested_path)

        return FileResponse(FRONTEND_DIST_DIR / "index.html")


class ApiPrefixCompatApp:
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app
        self.passthrough_paths = {"/docs", "/openapi.json", "/redoc"}

    def __getattr__(self, name):
        return getattr(self.asgi_app, name)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.asgi_app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path and not path.startswith("/api") and path not in self.passthrough_paths:
            rewritten = dict(scope)
            rewritten["path"] = f"/api{path}" if path.startswith("/") else f"/api/{path}"
            await self.asgi_app(rewritten, receive, send)
            return

        await self.asgi_app(scope, receive, send)


if os.getenv("VERCEL"):
    app = ApiPrefixCompatApp(app)