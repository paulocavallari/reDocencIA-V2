from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import CurriculumDiscipline, CurriculumGradeLevel, CurriculumLearningObjective, CurriculumSkillCode, CurriculumLearningSkill, Setting
from app.routers import ai as ai_router
from app.services import openrouter as openrouter_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

session = TestingSessionLocal()

# Seed minimal curriculum V2 entities used by /api/ai/generate
session.add(Setting(key="openrouter_api_key", value="fake-key"))
discipline = CurriculumDiscipline(nome="Língua Portuguesa")
grade = CurriculumGradeLevel(nivel_ensino="Ensino Fundamental: Anos Finais", ano_serie="6º Ano", sort_order=1)
session.add_all([discipline, grade])
session.flush()

objective = CurriculumLearningObjective(
    discipline_id=discipline.id,
    grade_level_id=grade.id,
    ae_codigo="AE1",
    descricao="Analisar as características de textos do campo jornalístico-midiático.",
    sort_order=1,
)
session.add(objective)
session.flush()

code1 = CurriculumSkillCode(codigo="EF69LP16A", descricao_referencia="Analisar textos jornalísticos.")
code2 = CurriculumSkillCode(codigo="EF04LP15A", descricao_referencia="Relacionar ideias principais.")
session.add_all([code1, code2])
session.flush()

skill1 = CurriculumLearningSkill(
    learning_objective_id=objective.id,
    skill_code_id=code1.id,
    categoria="habilidade_priorizada",
    sort_order=1,
)
skill2 = CurriculumLearningSkill(
    learning_objective_id=objective.id,
    skill_code_id=code2.id,
    categoria="habilidade_relacionada",
    sort_order=2,
)
session.add_all([skill1, skill2])
session.commit()

async def fake_call_openrouter(client, *, api_key, model, prompt):
    # Return markdown that follows the requested structure.
    markdown = """# Dados Gerais\n- **Disciplina:** Língua Portuguesa\n- **Turma:** 6º Ano\n\n# Estrutura da Aula\n\n## Introdução (10 minutos)\nAbertura da aula com contextualização do tema.\n\n## Desenvolvimento (30 minutos)\nAtividade guiada com avaliação formativa.\n\n## Conclusão (10 minutos)\nSíntese dos aprendizados e fechamento.\n\n# Exemplos de Adaptação para a Educação Especial\n\n## Deficiência Intelectual (DI)\nExemplo de adaptação.\n\n## Deficiência Auditiva (DA)\nExemplo de adaptação.\n\n## Surdez\nExemplo de adaptação.\n\n## Deficiência Visual (DV)\nExemplo de adaptação.\n\n## Cegueira\nExemplo de adaptação.\n\n## Deficiência Física (DF)\nExemplo de adaptação.\n\n## Autismo\n- **Nível 1** — exemplo\n- **Nível 2** — exemplo\n- **Nível 3** — exemplo\n"""
    return markdown, "stop"

openrouter_service.call_openrouter = fake_call_openrouter

app = FastAPI()
app.include_router(ai_router.router)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

payload = {
    "nivel_ensino": "Ensino Fundamental: Anos Finais",
    "bimestre": 1,
    "ano_serie": "6º Ano",
    "disciplina": "Língua Portuguesa",
    "ae_id": objective.id,
    "conteudos": ["Leitura de comentários"],
    "habilidades_ids": [skill1.id, skill2.id],
    "objetivos": "Desenvolver leitura crítica e análise de efeitos de sentido.",
    "duracao": "50 minutos",
    "orientacoes": "Usar exemplos do cotidiano.",
    "material_context": None,
}

resp = client.post("/api/ai/generate", json=payload)
print("status:", resp.status_code)
body = resp.json()
print("prompt_length:", len(body.get("prompt", "")))
print("html_length:", len(body.get("html", "")))
print("prompt_preview:")
print(body.get("prompt", "")[:700])
print("html_preview:")
print(body.get("html", "")[:700])

session.close()
