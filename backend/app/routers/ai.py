from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurriculumLearningSkill, CurriculumSkill
from app.schemas import PlanGenerateRequest, PlanGenerateResponse
from app.services.openrouter import generate_lesson_plan


router = APIRouter(prefix="/api/ai", tags=["ai"])


def map_v2_skill_to_prompt_skill(v2_skill: CurriculumLearningSkill):
    objective = v2_skill.learning_objective
    skill_code = v2_skill.skill_code
    return SimpleNamespace(
        id=v2_skill.id,
        codigo=(skill_code.codigo if skill_code else None) or objective.ae_codigo,
        descricao=(skill_code.descricao_referencia if skill_code else None) or objective.descricao,
        tipo=v2_skill.categoria,
        aprendizagem_essencial=SimpleNamespace(
            codigo=objective.ae_codigo,
            descricao=objective.descricao,
        ),
    )


def map_v1_skill_to_prompt_skill(v1_skill: CurriculumSkill):
    ae = v1_skill.aprendizagem_essencial
    return SimpleNamespace(
        id=v1_skill.id,
        codigo=v1_skill.codigo,
        descricao=v1_skill.descricao,
        tipo=v1_skill.tipo,
        aprendizagem_essencial=SimpleNamespace(
            codigo=ae.codigo if ae else None,
            descricao=ae.descricao if ae else None,
        ),
    )


def dedupe_prompt_skills(skills: list[SimpleNamespace]) -> list[SimpleNamespace]:
    seen_codes: set[str] = set()
    unique: list[SimpleNamespace] = []
    for skill in skills:
        code = (skill.codigo or "").strip().upper()
        key = code or f"id:{skill.id}"
        if key in seen_codes:
            continue
        seen_codes.add(key)
        unique.append(skill)
    return unique


@router.post("/generate", response_model=PlanGenerateResponse)
async def generate_plan(
    payload: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    selected_v1_skills = (
        db.query(CurriculumSkill)
        .filter(CurriculumSkill.id.in_(payload.habilidades_ids))
        .all()
    )

    selected_v1_by_id = {skill.id: skill for skill in selected_v1_skills}
    selected_skills = [
        map_v1_skill_to_prompt_skill(selected_v1_by_id[skill_id])
        for skill_id in payload.habilidades_ids
        if skill_id in selected_v1_by_id
    ]

    # V2 compatibility: selected skill IDs now come from curriculum_learning_skills.
    if not selected_skills:
        selected_v2_skills = (
            db.query(CurriculumLearningSkill)
            .filter(CurriculumLearningSkill.id.in_(payload.habilidades_ids))
            .all()
        )
        selected_v2_by_id = {skill.id: skill for skill in selected_v2_skills}
        selected_skills = [
            map_v2_skill_to_prompt_skill(selected_v2_by_id[skill_id])
            for skill_id in payload.habilidades_ids
            if skill_id in selected_v2_by_id
        ]

    selected_skills = dedupe_prompt_skills(selected_skills)

    if not selected_skills:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma habilidade válida.")

    response = await generate_lesson_plan(payload, selected_skills, db)
    return PlanGenerateResponse(**response)
