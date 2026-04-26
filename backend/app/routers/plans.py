from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavedPlan, User
from app.schemas import SavedPlanCreate, SavedPlanRead
from app.security import get_current_user
from app.services.export import build_docx, build_pdf


router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("", response_model=SavedPlanRead)
def create_plan(payload: SavedPlanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = SavedPlan(
        user_id=current_user.id,
        titulo=payload.titulo,
        disciplina=payload.disciplina,
        ano_serie=payload.ano_serie,
        nivel_ensino=payload.nivel_ensino,
        bimestre=payload.bimestre,
        conteudos="\n".join(payload.conteudos),
        habilidades="\n".join(payload.habilidades),
        duracao=payload.duracao,
        orientacoes=payload.orientacoes,
        plano_html=payload.plano_html,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[SavedPlanRead])
def list_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(SavedPlan)
        .filter(SavedPlan.user_id == current_user.id)
        .order_by(SavedPlan.updated_at.desc())
        .all()
    )


@router.get("/{plan_id}", response_model=SavedPlanRead)
def get_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id, SavedPlan.user_id == current_user.id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    return plan


@router.put("/{plan_id}", response_model=SavedPlanRead)
def update_plan(plan_id: int, payload: SavedPlanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id, SavedPlan.user_id == current_user.id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    plan.titulo = payload.titulo
    plan.disciplina = payload.disciplina
    plan.ano_serie = payload.ano_serie
    plan.nivel_ensino = payload.nivel_ensino
    plan.bimestre = payload.bimestre
    plan.conteudos = "\n".join(payload.conteudos)
    plan.habilidades = "\n".join(payload.habilidades)
    plan.duracao = payload.duracao
    plan.orientacoes = payload.orientacoes
    plan.plano_html = payload.plano_html
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id, SavedPlan.user_id == current_user.id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    db.delete(plan)
    db.commit()


@router.get("/{plan_id}/export")
def export_plan(
    plan_id: int,
    format: str = Query(pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id, SavedPlan.user_id == current_user.id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    if format == "pdf":
        buffer = build_pdf(plan.titulo, plan.plano_html)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{plan.titulo}.pdf"'},
        )

    buffer = build_docx(plan.titulo, plan.plano_html)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{plan.titulo}.docx"'},
    )
