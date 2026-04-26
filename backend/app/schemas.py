from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=4, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    username: str
    is_admin: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RegisterResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    user: UserRead | None = None
    pending_confirmation: bool = False
    assisted_login: bool = False
    email: EmailStr | None = None


class SettingRead(BaseModel):
    key: str
    value: str | None


class SettingUpdate(BaseModel):
    value: str


class SettingModelsUpdate(BaseModel):
    values: list[str | None] = Field(min_length=1, max_length=3)


class CurriculumContentRead(BaseModel):
    id: int
    objetos_conhecimento: str
    unidade_tematica: str | None


class CurriculumSkillRead(BaseModel):
    id: int
    habilidade_codigo: str
    habilidade_descricao: str
    skill_category: str
    matriz_nivel: str | None
    matriz_descritor: str | None
    objetos_conhecimento: str


class CurriculumAERead(BaseModel):
    id: int
    ae_codigo: str
    descricao: str


class PlanGenerateRequest(BaseModel):
    nivel_ensino: str
    bimestre: int
    ano_serie: str
    disciplina: str
    ae_id: int | None = None
    conteudos: list[str]
    habilidades_ids: list[int]
    objetivos: str
    duracao: str
    orientacoes: str | None = None
    material_context: str | None = None


class PlanGenerateResponse(BaseModel):
    html: str
    prompt: str


class SavedPlanCreate(BaseModel):
    titulo: str
    disciplina: str
    ano_serie: str
    nivel_ensino: str
    bimestre: int
    conteudos: list[str]
    habilidades: list[str]
    duracao: str
    orientacoes: str | None = None
    plano_html: str


class SavedPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    disciplina: str
    ano_serie: str
    nivel_ensino: str
    bimestre: int
    conteudos: str
    habilidades: str
    duracao: str
    orientacoes: str | None
    plano_html: str
    created_at: datetime
    updated_at: datetime
