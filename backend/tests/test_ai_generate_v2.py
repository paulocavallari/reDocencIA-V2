from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (
    CurriculumDiscipline,
    CurriculumGradeLevel,
    CurriculumLearningObjective,
    CurriculumLearningSkill,
    CurriculumSkillCode,
)
from app.routers.ai import router as ai_router


def _build_ai_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(ai_router)

    def _override_get_db():
        db = SessionTesting()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionTesting


def _seed_v2_skill(session_factory):
    with session_factory() as session:
        discipline = CurriculumDiscipline(nome="Matemática")
        level = CurriculumGradeLevel(nivel_ensino="Ensino Fundamental: Anos Finais", ano_serie="6º Ano", sort_order=1)
        session.add_all([discipline, level])
        session.flush()

        objective = CurriculumLearningObjective(
            discipline_id=discipline.id,
            grade_level_id=level.id,
            ae_codigo="EF06MA01",
            descricao="Resolver problemas de adição e subtração",
            sort_order=1,
        )
        code = CurriculumSkillCode(codigo="EF06MA01", descricao_referencia="Resolver problemas com números naturais")
        session.add_all([objective, code])
        session.flush()

        skill = CurriculumLearningSkill(
            learning_objective_id=objective.id,
            skill_code_id=code.id,
            categoria="habilidade_priorizada",
            sort_order=1,
        )
        session.add(skill)
        session.commit()
        return skill.id


def test_generate_accepts_v2_skill_ids(monkeypatch):
    app, session_factory = _build_ai_client()
    skill_id = _seed_v2_skill(session_factory)

    from app.routers import ai as ai_module

    async def fake_generate_lesson_plan(payload, selected_skills, db):
        assert selected_skills
        assert selected_skills[0].codigo == "EF06MA01"
        return {"html": "<p>ok</p>", "prompt": "prompt"}

    monkeypatch.setattr(ai_module, "generate_lesson_plan", fake_generate_lesson_plan)

    client = TestClient(app)
    payload = {
        "nivel_ensino": "Ensino Fundamental: Anos Finais",
        "bimestre": 1,
        "ano_serie": "6º Ano",
        "disciplina": "Matemática",
        "ae_id": None,
        "conteudos": ["Números naturais"],
        "habilidades_ids": [skill_id],
        "objetivos": "Consolidar o entendimento sobre operações com números naturais.",
        "duracao": "50 minutos",
        "orientacoes": "",
        "material_context": None,
    }

    response = client.post(
        "/api/ai/generate",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["html"] == "<p>ok</p>"
