-- Curriculum V2 relational model
-- Keeps the current V1 tables intact and adds normalized structures

CREATE TABLE IF NOT EXISTS curriculum_disciplines (
    id BIGSERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curriculum_grade_levels (
    id BIGSERIAL PRIMARY KEY,
    nivel_ensino TEXT NOT NULL,
    ano_serie TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (nivel_ensino, ano_serie)
);

CREATE TABLE IF NOT EXISTS curriculum_learning_objectives (
    id BIGSERIAL PRIMARY KEY,
    discipline_id BIGINT NOT NULL REFERENCES curriculum_disciplines(id) ON DELETE RESTRICT,
    grade_level_id BIGINT NOT NULL REFERENCES curriculum_grade_levels(id) ON DELETE RESTRICT,
    ae_codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (discipline_id, grade_level_id, ae_codigo)
);

CREATE TABLE IF NOT EXISTS curriculum_skill_codes (
    id BIGSERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    descricao_referencia TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curriculum_learning_skills (
    id BIGSERIAL PRIMARY KEY,
    learning_objective_id BIGINT NOT NULL REFERENCES curriculum_learning_objectives(id) ON DELETE CASCADE,
    skill_code_id BIGINT NOT NULL REFERENCES curriculum_skill_codes(id) ON DELETE RESTRICT,
    categoria TEXT NOT NULL CHECK (categoria IN ('habilidade_priorizada', 'habilidade_relacionada', 'conhecimento_previo')),
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (learning_objective_id, skill_code_id, categoria)
);

CREATE TABLE IF NOT EXISTS curriculum_content_items (
    id BIGSERIAL PRIMARY KEY,
    descricao TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curriculum_learning_contents (
    id BIGSERIAL PRIMARY KEY,
    learning_objective_id BIGINT NOT NULL REFERENCES curriculum_learning_objectives(id) ON DELETE CASCADE,
    content_item_id BIGINT NOT NULL REFERENCES curriculum_content_items(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (learning_objective_id, content_item_id)
);

CREATE TABLE IF NOT EXISTS curriculum_learning_dependencies (
    id BIGSERIAL PRIMARY KEY,
    learning_objective_id BIGINT NOT NULL REFERENCES curriculum_learning_objectives(id) ON DELETE CASCADE,
    prerequisite_learning_objective_id BIGINT NOT NULL REFERENCES curriculum_learning_objectives(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL CHECK (dependency_type IN ('sequencial', 'opcional', 'reforco')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (learning_objective_id, prerequisite_learning_objective_id, dependency_type),
    CHECK (learning_objective_id <> prerequisite_learning_objective_id)
);

CREATE INDEX IF NOT EXISTS idx_curriculum_grade_levels_sort_order
    ON curriculum_grade_levels (sort_order);

CREATE INDEX IF NOT EXISTS idx_curriculum_learning_objectives_filter
    ON curriculum_learning_objectives (discipline_id, grade_level_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_curriculum_learning_skills_lookup
    ON curriculum_learning_skills (learning_objective_id, categoria, sort_order);

CREATE INDEX IF NOT EXISTS idx_curriculum_learning_contents_lookup
    ON curriculum_learning_contents (learning_objective_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_curriculum_learning_dependencies_lookup
    ON curriculum_learning_dependencies (learning_objective_id, dependency_type);
