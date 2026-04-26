from __future__ import annotations

from sqlalchemy import case
from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AprendizagemEssencial,
    CurriculumSkill,
    CurriculumContent,
    CurriculumDiscipline,
    CurriculumGradeLevel,
    CurriculumLearningObjective,
    CurriculumSkillCode,
    CurriculumLearningSkill,
    CurriculumContentItem,
    CurriculumLearningContent,
)
from app.schemas import CurriculumAERead, CurriculumContentRead, CurriculumSkillRead


router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])

LEVELS = [
    "Ensino Fundamental: Anos Iniciais",
    "Ensino Fundamental: Anos Finais",
    "Ensino Médio",
    "Ensino Médio Noturno",
]


def _curriculum_v2_ready(db: Session) -> bool:
    try:
        return db.query(CurriculumLearningObjective.id).limit(1).first() is not None
    except Exception:
        return False


@router.get("/niveis")
def list_levels():
    return LEVELS


@router.get("/bimestres")
def list_bimesters():
    return [1, 2, 3, 4]


@router.get("/anos")
def list_years(nivel: str, db: Session = Depends(get_db)):
    nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
    if _curriculum_v2_ready(db):
        rows = (
            db.query(distinct(CurriculumGradeLevel.ano_serie), CurriculumGradeLevel.sort_order)
            .filter(CurriculumGradeLevel.nivel_ensino == nivel_db)
            .order_by(CurriculumGradeLevel.sort_order, CurriculumGradeLevel.ano_serie)
            .all()
        )
        return [row[0] for row in rows]

    rows = (
        db.query(distinct(AprendizagemEssencial.ano_serie))
        .filter(AprendizagemEssencial.nivel_ensino == nivel_db)
        .order_by(AprendizagemEssencial.ano_serie)
        .all()
    )
    return [row[0] for row in rows]


@router.get("/disciplinas")
def list_subjects(nivel: str, ano: str, db: Session = Depends(get_db)):
    nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
    if _curriculum_v2_ready(db):
        rows = (
            db.query(distinct(CurriculumDiscipline.nome))
            .join(CurriculumLearningObjective, CurriculumLearningObjective.discipline_id == CurriculumDiscipline.id)
            .join(CurriculumGradeLevel, CurriculumGradeLevel.id == CurriculumLearningObjective.grade_level_id)
            .filter(
                CurriculumGradeLevel.nivel_ensino == nivel_db,
                CurriculumGradeLevel.ano_serie == ano,
            )
            .order_by(CurriculumDiscipline.nome)
            .all()
        )
        return [row[0] for row in rows]

    rows = (
        db.query(distinct(AprendizagemEssencial.disciplina))
        .filter(
            AprendizagemEssencial.nivel_ensino == nivel_db,
            AprendizagemEssencial.ano_serie == ano,
        )
        .order_by(AprendizagemEssencial.disciplina)
        .all()
    )
    return [row[0] for row in rows]


@router.get("/aes", response_model=list[CurriculumAERead])
def list_learning_objectives(
    nivel: str,
    ano: str,
    disciplina: str,
    bimestre: int | None = None,
    db: Session = Depends(get_db),
):
    nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
    if _curriculum_v2_ready(db):
        rows = (
            db.query(CurriculumLearningObjective)
            .join(CurriculumGradeLevel, CurriculumGradeLevel.id == CurriculumLearningObjective.grade_level_id)
            .join(CurriculumDiscipline, CurriculumDiscipline.id == CurriculumLearningObjective.discipline_id)
            .filter(
                CurriculumGradeLevel.nivel_ensino == nivel_db,
                CurriculumGradeLevel.ano_serie == ano,
                CurriculumDiscipline.nome == disciplina,
            )
            .order_by(CurriculumLearningObjective.sort_order, CurriculumLearningObjective.ae_codigo)
            .all()
        )
        return [
            CurriculumAERead(
                id=row.id,
                ae_codigo=row.ae_codigo,
                descricao=row.descricao,
            )
            for row in rows
        ]

    query = db.query(AprendizagemEssencial).filter(
        AprendizagemEssencial.nivel_ensino == nivel_db,
        AprendizagemEssencial.ano_serie == ano,
        AprendizagemEssencial.disciplina == disciplina,
    )
    if bimestre is not None:
        query = query.filter(AprendizagemEssencial.bimestre == bimestre)

    rows = query.order_by(AprendizagemEssencial.codigo).all()
    return [
        CurriculumAERead(
            id=row.id,
            ae_codigo=row.codigo,
            descricao=row.descricao,
        )
        for row in rows
    ]


@router.get("/conteudos", response_model=list[CurriculumContentRead])
def list_contents(nivel: str, ano: str, disciplina: str, ae_id: int | None = None, db: Session = Depends(get_db)):
    nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
    if _curriculum_v2_ready(db):
        query = (
            db.query(CurriculumContentItem)
            .join(CurriculumLearningContent, CurriculumLearningContent.content_item_id == CurriculumContentItem.id)
            .join(CurriculumLearningObjective, CurriculumLearningObjective.id == CurriculumLearningContent.learning_objective_id)
            .join(CurriculumGradeLevel, CurriculumGradeLevel.id == CurriculumLearningObjective.grade_level_id)
            .join(CurriculumDiscipline, CurriculumDiscipline.id == CurriculumLearningObjective.discipline_id)
            .filter(
                CurriculumGradeLevel.nivel_ensino == nivel_db,
                CurriculumGradeLevel.ano_serie == ano,
                CurriculumDiscipline.nome == disciplina,
            )
        )
        if ae_id is not None:
            query = query.filter(CurriculumLearningObjective.id == ae_id)

        rows = query.order_by(CurriculumContentItem.descricao).all()

        seen: dict[str, CurriculumContentRead] = {}
        for row in rows:
            seen.setdefault(
                row.descricao,
                CurriculumContentRead(
                    id=row.id,
                    objetos_conhecimento=row.descricao,
                    unidade_tematica=None,
                ),
            )
        return list(seen.values())

    query = (
        db.query(CurriculumContent)
        .join(CurriculumSkill.conteudos)
        .join(AprendizagemEssencial)
        .filter(
            AprendizagemEssencial.nivel_ensino == nivel_db,
            AprendizagemEssencial.ano_serie == ano,
            AprendizagemEssencial.disciplina == disciplina,
        )
    )
    if ae_id is not None:
        query = query.filter(AprendizagemEssencial.id == ae_id)

    rows = query.order_by(CurriculumContent.descricao).all()

    seen: dict[str, CurriculumContentRead] = {}
    for row in rows:
        seen.setdefault(
            row.descricao,
            CurriculumContentRead(
                id=row.id,
                objetos_conhecimento=row.descricao,
                unidade_tematica=row.unidade_tematica,
            ),
        )
    return list(seen.values())


@router.get("/habilidades", response_model=list[CurriculumSkillRead])
def list_skills(
    nivel: str | None = None,
    ano: str | None = None,
    disciplina: str | None = None,
    ae_id: int | None = None,
    content_ids: list[int] = Query(default=[]),
    conteudos: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    if _curriculum_v2_ready(db):
        query = (
            db.query(
                CurriculumLearningSkill,
                CurriculumSkillCode,
                CurriculumLearningObjective,
                CurriculumContentItem,
            )
            .join(
                CurriculumLearningObjective,
                CurriculumLearningObjective.id == CurriculumLearningSkill.learning_objective_id,
            )
            .join(
                CurriculumSkillCode,
                CurriculumSkillCode.id == CurriculumLearningSkill.skill_code_id,
            )
            .join(
                CurriculumLearningContent,
                CurriculumLearningContent.learning_objective_id == CurriculumLearningObjective.id,
            )
            .join(
                CurriculumContentItem,
                CurriculumContentItem.id == CurriculumLearningContent.content_item_id,
            )
            .join(
                CurriculumGradeLevel,
                CurriculumGradeLevel.id == CurriculumLearningObjective.grade_level_id,
            )
            .join(
                CurriculumDiscipline,
                CurriculumDiscipline.id == CurriculumLearningObjective.discipline_id,
            )
        )

        if nivel:
            nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
            query = query.filter(CurriculumGradeLevel.nivel_ensino == nivel_db)
        if ano:
            query = query.filter(CurriculumGradeLevel.ano_serie == ano)
        if disciplina:
            query = query.filter(CurriculumDiscipline.nome == disciplina)
        if ae_id is not None:
            query = query.filter(CurriculumLearningObjective.id == ae_id)

        if content_ids:
            content_rows = db.query(CurriculumContentItem).filter(CurriculumContentItem.id.in_(content_ids)).all()
            conteudos = list({row.descricao for row in content_rows} | set(conteudos))

        if conteudos:
            query = query.filter(CurriculumContentItem.descricao.in_(conteudos))

        category_order = case(
            (CurriculumLearningSkill.categoria == "habilidade_priorizada", 0),
            (CurriculumLearningSkill.categoria == "conhecimento_previo", 1),
            else_=2,
        )

        rows = query.order_by(
            CurriculumContentItem.descricao,
            category_order,
            CurriculumSkillCode.codigo,
        ).all()

        return [
            CurriculumSkillRead(
                id=skill.id,
                habilidade_codigo=code.codigo,
                habilidade_descricao=code.descricao_referencia or "",
                skill_category=skill.categoria,
                matriz_nivel=objective.ae_codigo,
                matriz_descritor=objective.descricao,
                objetos_conhecimento=content.descricao,
            )
            for skill, code, objective, content in rows
        ]

    query = db.query(CurriculumSkill, CurriculumContent, AprendizagemEssencial).join(CurriculumSkill.conteudos).join(AprendizagemEssencial)

    if nivel:
        nivel_db = "Ensino Médio" if nivel == "Ensino Médio Noturno" else nivel
        query = query.filter(AprendizagemEssencial.nivel_ensino == nivel_db)
    if ano:
        query = query.filter(AprendizagemEssencial.ano_serie == ano)
    if disciplina:
        query = query.filter(AprendizagemEssencial.disciplina == disciplina)
    if ae_id is not None:
        query = query.filter(AprendizagemEssencial.id == ae_id)

    if content_ids:
        content_rows = db.query(CurriculumContent).filter(CurriculumContent.id.in_(content_ids)).all()
        conteudos = list({row.descricao for row in content_rows} | set(conteudos))

    if conteudos:
        query = query.filter(CurriculumContent.descricao.in_(conteudos))

    category_order = case(
        (CurriculumSkill.tipo == "habilidade_priorizada", 0),
        (CurriculumSkill.tipo == "conhecimento_previo", 1),
        else_=2,
    )
    rows = query.order_by(CurriculumContent.descricao, category_order, CurriculumSkill.codigo).all()
    
    return [
        CurriculumSkillRead(
            id=skill.id,
            habilidade_codigo=skill.codigo,
            habilidade_descricao=skill.descricao,
            skill_category=skill.tipo,
            matriz_nivel=ae.codigo,
            matriz_descritor=ae.descricao,
            objetos_conhecimento=content.descricao,
        )
        for skill, content, ae in rows
    ]
