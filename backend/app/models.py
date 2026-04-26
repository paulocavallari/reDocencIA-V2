from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    saved_plans: Mapped[list[SavedPlan]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CurriculumData(Base):
    __tablename__ = "curriculum_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nivel_ensino: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    disciplina: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ano_serie: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    unidade_tematica: Mapped[str] = mapped_column(Text, nullable=True)
    objetos_conhecimento: Mapped[str] = mapped_column(Text, nullable=False)
    habilidade_codigo: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    habilidade_descricao: Mapped[str] = mapped_column(Text, nullable=True)
    skill_category: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    objetivos: Mapped[str] = mapped_column(Text, nullable=True)
    matriz_nivel: Mapped[str] = mapped_column(Text, nullable=True)
    matriz_descritor: Mapped[str] = mapped_column(Text, nullable=True)
    ae_codigo: Mapped[str] = mapped_column(Text, nullable=True)
    ae_descricao: Mapped[str] = mapped_column(Text, nullable=True)
    source_file: Mapped[str] = mapped_column(Text, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


from sqlalchemy import Table

skill_content_association = Table(
    "skill_content",
    Base.metadata,
    Column("skill_id", Integer, ForeignKey("curriculum_skills.id", ondelete="CASCADE")),
    Column("content_id", Integer, ForeignKey("curriculum_contents.id", ondelete="CASCADE")),
)


class AprendizagemEssencial(Base):
    __tablename__ = "aprendizagens_essenciais"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nivel_ensino: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    disciplina: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    ano_serie: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    bimestre: Mapped[int] = mapped_column(Integer, index=True, nullable=True)

    codigo: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    habilidades: Mapped[list[CurriculumSkill]] = relationship(
        "CurriculumSkill", back_populates="aprendizagem_essencial", cascade="all, delete-orphan"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CurriculumSkill(Base):
    __tablename__ = "curriculum_skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    aprendizagem_essencial_id: Mapped[int] = mapped_column(
        ForeignKey("aprendizagens_essenciais.id", ondelete="CASCADE"), nullable=False, index=True
    )

    codigo: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)

    aprendizagem_essencial: Mapped[AprendizagemEssencial] = relationship(
        "AprendizagemEssencial", back_populates="habilidades"
    )
    conteudos: Mapped[list[CurriculumContent]] = relationship(
        "CurriculumContent", secondary=skill_content_association, back_populates="habilidades"
    )


class CurriculumContent(Base):
    __tablename__ = "curriculum_contents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    unidade_tematica: Mapped[str] = mapped_column(Text, nullable=True)

    habilidades: Mapped[list[CurriculumSkill]] = relationship(
        "CurriculumSkill", secondary=skill_content_association, back_populates="conteudos"
    )


class SavedPlan(Base):
    __tablename__ = "saved_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    disciplina: Mapped[str] = mapped_column(Text, nullable=False)
    ano_serie: Mapped[str] = mapped_column(Text, nullable=False)
    nivel_ensino: Mapped[str] = mapped_column(Text, nullable=False)
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    conteudos: Mapped[str] = mapped_column(Text, nullable=False)
    habilidades: Mapped[str] = mapped_column(Text, nullable=False)
    duracao: Mapped[str] = mapped_column(Text, nullable=False)
    orientacoes: Mapped[str] = mapped_column(Text, nullable=True)
    plano_html: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="saved_plans")


class CurriculumDiscipline(Base):
    __tablename__ = "curriculum_disciplines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CurriculumGradeLevel(Base):
    __tablename__ = "curriculum_grade_levels"

    __table_args__ = (UniqueConstraint("nivel_ensino", "ano_serie", name="uq_curriculum_grade_levels_nivel_ano"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nivel_ensino: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ano_serie: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CurriculumLearningObjective(Base):
    __tablename__ = "curriculum_learning_objectives"

    __table_args__ = (UniqueConstraint("discipline_id", "grade_level_id", "ae_codigo", name="uq_curriculum_lo"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_disciplines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    grade_level_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_grade_levels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ae_codigo: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    discipline: Mapped[CurriculumDiscipline] = relationship("CurriculumDiscipline")
    grade_level: Mapped[CurriculumGradeLevel] = relationship("CurriculumGradeLevel")


class CurriculumSkillCode(Base):
    __tablename__ = "curriculum_skill_codes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    descricao_referencia: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CurriculumLearningSkill(Base):
    __tablename__ = "curriculum_learning_skills"

    __table_args__ = (
        UniqueConstraint("learning_objective_id", "skill_code_id", "categoria", name="uq_curriculum_learning_skills"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learning_objective_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_learning_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_code_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_skill_codes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    categoria: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    learning_objective: Mapped[CurriculumLearningObjective] = relationship("CurriculumLearningObjective")
    skill_code: Mapped[CurriculumSkillCode] = relationship("CurriculumSkillCode")


class CurriculumContentItem(Base):
    __tablename__ = "curriculum_content_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CurriculumLearningContent(Base):
    __tablename__ = "curriculum_learning_contents"

    __table_args__ = (UniqueConstraint("learning_objective_id", "content_item_id", name="uq_curriculum_learning_contents"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learning_objective_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_learning_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_content_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    learning_objective: Mapped[CurriculumLearningObjective] = relationship("CurriculumLearningObjective")
    content_item: Mapped[CurriculumContentItem] = relationship("CurriculumContentItem")


class CurriculumLearningDependency(Base):
    __tablename__ = "curriculum_learning_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "learning_objective_id",
            "prerequisite_learning_objective_id",
            "dependency_type",
            name="uq_curriculum_learning_dependencies",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learning_objective_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_learning_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prerequisite_learning_objective_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_learning_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependency_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
