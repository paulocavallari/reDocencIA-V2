from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (
    AprendizagemEssencial,
    CurriculumContent,
    CurriculumContentItem,
    CurriculumDiscipline,
    CurriculumGradeLevel,
    CurriculumLearningContent,
    CurriculumLearningObjective,
    CurriculumLearningSkill,
    CurriculumSkill,
    CurriculumSkillCode,
)
from app.routers.curriculum import router as curriculum_router


def _build_test_client_with_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(curriculum_router)

    def _override_get_db():
        db = SessionTesting()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionTesting


def _seed_v2_data(session):
    discipline = CurriculumDiscipline(nome="Língua Portuguesa")
    level = CurriculumGradeLevel(
        nivel_ensino="Ensino Fundamental: Anos Finais",
        ano_serie="6º Ano",
        sort_order=1,
    )
    session.add_all([discipline, level])
    session.flush()

    objective = CurriculumLearningObjective(
        discipline_id=discipline.id,
        grade_level_id=level.id,
        ae_codigo="EF06LP01",
        descricao="Analisar textos narrativos.",
        sort_order=1,
    )
    session.add(objective)
    session.flush()

    code = CurriculumSkillCode(codigo="EF06LP01", descricao_referencia="Identificar elementos narrativos")
    content = CurriculumContentItem(descricao="Gêneros narrativos")
    session.add_all([code, content])
    session.flush()

    session.add(
        CurriculumLearningSkill(
            learning_objective_id=objective.id,
            skill_code_id=code.id,
            categoria="habilidade_priorizada",
            sort_order=1,
        )
    )
    session.add(
        CurriculumLearningContent(
            learning_objective_id=objective.id,
            content_item_id=content.id,
            sort_order=1,
        )
    )
    session.commit()


def _seed_v1_data(session):
    ae = AprendizagemEssencial(
        nivel_ensino="Ensino Fundamental: Anos Finais",
        disciplina="Língua Portuguesa",
        ano_serie="6º Ano",
        bimestre=1,
        codigo="EF06LP01",
        descricao="Analisar textos narrativos.",
    )
    content = CurriculumContent(descricao="Gêneros narrativos", unidade_tematica="Leitura")
    skill = CurriculumSkill(codigo="EF06LP01", descricao="Identificar elementos narrativos", tipo="habilidade_priorizada")
    ae.habilidades.append(skill)
    skill.conteudos.append(content)
    session.add(ae)
    session.commit()


def test_curriculum_endpoints_v2_smoke_with_realistic_filters():
    app, session_factory = _build_test_client_with_db()
    with session_factory() as session:
        _seed_v2_data(session)

    client = TestClient(app)

    nivel = "Ensino Fundamental: Anos Finais"
    ano = "6º Ano"
    disciplina = "Língua Portuguesa"

    anos = client.get("/api/curriculum/anos", params={"nivel": nivel})
    disciplinas = client.get("/api/curriculum/disciplinas", params={"nivel": nivel, "ano": ano})
    conteudos = client.get(
        "/api/curriculum/conteudos",
        params={"nivel": nivel, "ano": ano, "disciplina": disciplina},
    )
    habilidades = client.get(
        "/api/curriculum/habilidades",
        params={"nivel": nivel, "ano": ano, "disciplina": disciplina},
    )

    assert anos.status_code == 200
    assert disciplinas.status_code == 200
    assert conteudos.status_code == 200
    assert habilidades.status_code == 200

    assert ano in anos.json()
    assert disciplina in disciplinas.json()
    assert len(conteudos.json()) > 0
    assert len(habilidades.json()) > 0
    assert conteudos.json()[0]["objetos_conhecimento"] == "Gêneros narrativos"
    assert habilidades.json()[0]["habilidade_codigo"] == "EF06LP01"


def test_curriculum_endpoints_fallback_to_v1_when_v2_is_empty():
    app, session_factory = _build_test_client_with_db()
    with session_factory() as session:
        _seed_v1_data(session)

    client = TestClient(app)

    response = client.get(
        "/api/curriculum/conteudos",
        params={
            "nivel": "Ensino Fundamental: Anos Finais",
            "ano": "6º Ano",
            "disciplina": "Língua Portuguesa",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["objetos_conhecimento"] == "Gêneros narrativos"
    # unidade_tematica vem preenchida apenas no caminho V1, confirmando fallback.
    assert payload[0]["unidade_tematica"] == "Leitura"
