from __future__ import annotations

import json
import os
import re

import httpx
import markdown
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AprendizagemEssencial, CurriculumLearningObjective, Setting


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_model_candidates(configured_models: list[str]) -> list[str]:
    candidates = configured_models[:3]
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def get_setting(db: Session, key: str) -> str | None:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else None


def get_configured_models(db: Session) -> list[str]:
    configured = [
        get_setting(db, "openrouter_model_1"),
        get_setting(db, "openrouter_model_2"),
        get_setting(db, "openrouter_model_3"),
    ]

    if not any(configured):
        configured = [get_setting(db, "openrouter_model")]

    normalized: list[str] = []
    for model in configured:
        candidate = (model or "").strip()
        if candidate:
            normalized.append(candidate)

    return build_model_candidates(normalized) if normalized else ["google/gemini-2.0-flash-001"]


def compact_context(value: str | None, max_chars: int = 3500) -> str | None:
    if not value:
        return None
    compact = "\n".join(line.strip() for line in value.splitlines() if line.strip())
    return compact[:max_chars] if compact else None


async def call_openrouter(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    model: str,
    prompt: str,
) -> tuple[str, str | None]:
    body = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": "Você é um especialista em design instrucional com foco no Currículo Paulista."},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "redocencia",
            },
            json=body,
        )
    except httpx.TimeoutException as error:
        raise HTTPException(
            status_code=504,
            detail="OpenRouter: tempo limite excedido ao gerar o plano. Tente novamente com menos conteúdos/habilidades.",
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="OpenRouter: falha de comunicação com o provedor de IA.",
        ) from error

    if response.status_code >= 400:
        try:
            error_payload = response.json()
            error_message = error_payload.get("error", {}).get("message") or response.text
        except json.JSONDecodeError:
            error_message = response.text

        if response.status_code in {400, 401, 402, 403, 429}:
            raise HTTPException(status_code=response.status_code, detail=f"OpenRouter: {error_message}")
        raise HTTPException(status_code=502, detail=f"Erro OpenRouter: {error_message}")

    data = response.json()
    if data.get("error"):
        error_code = data["error"].get("code")
        error_message = data["error"].get("message", "Erro retornado pelo provedor.")
        if error_code == 524:
            raise HTTPException(
                status_code=504,
                detail="OpenRouter: o provedor excedeu o tempo limite para esse modelo/prompt. Tente novamente ou use um modelo mais rápido.",
            )
        raise HTTPException(status_code=502, detail=f"OpenRouter: {error_message}")

    choices = data.get("choices") or []
    if not choices:
        raise HTTPException(status_code=502, detail="OpenRouter: resposta sem conteúdo utilizável.")

    first_choice = choices[0]
    if first_choice.get("error"):
        choice_error = first_choice["error"].get("message", "Erro retornado pelo modelo.")
        raise HTTPException(status_code=502, detail=f"OpenRouter: {choice_error}")

    message = first_choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not content:
        raise HTTPException(status_code=502, detail="OpenRouter: resposta vazia do modelo.")
    return content, first_choice.get("finish_reason")


def _extract_minutes(duration: str | None) -> int:
    if not duration:
        return 50
    matched = re.search(r"(\d+)", duration)
    return int(matched.group(1)) if matched else 50


def _split_minutes(total: int) -> tuple[int, int, int]:
    intro = max(10, round(total * 0.2))
    conclusion = max(10, round(total * 0.2))
    development = max(20, total - intro - conclusion)
    return intro, development, conclusion


def _lines_for_category(selected_skills, category: str) -> list[str]:
    lines: list[str] = []
    for skill in selected_skills:
        if skill.tipo != category:
            continue
        code = skill.codigo or "Sem código"
        description = skill.descricao or "Sem descrição"
        lines.append(f"{code} - {description}")
    return lines


def _format_lines(lines: list[str]) -> str:
    if not lines:
        return "Não selecionada"
    return "; ".join(lines)


def _resolve_ae_text(payload, db: Session) -> str:
    if not getattr(payload, "ae_id", None):
        return "Não selecionada"

    v2_ae = db.query(CurriculumLearningObjective).filter(CurriculumLearningObjective.id == payload.ae_id).first()
    if v2_ae:
        return f"{v2_ae.ae_codigo} - {v2_ae.descricao}"

    v1_ae = db.query(AprendizagemEssencial).filter(AprendizagemEssencial.id == payload.ae_id).first()
    if v1_ae:
        return f"{v1_ae.codigo} - {v1_ae.descricao}"

    return "Não selecionada"


def build_prompt(payload, selected_skills, ae_text: str) -> str:
    prioritized = _format_lines(_lines_for_category(selected_skills, "habilidade_priorizada"))
    related = _format_lines(_lines_for_category(selected_skills, "habilidade_relacionada"))
    prior_knowledge = _format_lines(_lines_for_category(selected_skills, "conhecimento_previo"))

    minutes = _extract_minutes(payload.duracao)
    intro_minutes, development_minutes, conclusion_minutes = _split_minutes(minutes)

    support_data = []
    if payload.orientacoes:
        support_data.append(f"Orientações adicionais do usuário: {payload.orientacoes}")
    if payload.material_context:
        support_data.append(f"Material de apoio anexado (resumo): {payload.material_context}")
    support_text = "\n".join(f"- {item}" for item in support_data) if support_data else "- Nenhum dado adicional."

    return f"""<system>
Você é um especialista em planejamento pedagógico com 20 anos de experiência em design instrucional, educação inclusiva e BNCC/currículo paulista. Sua tarefa é produzir UM plano de aula completo, prático e pronto para aplicação em sala.
</system>

<input>
- Disciplina: {payload.disciplina}
- Turma: {payload.ano_serie}
- Aprendizagem Essencial (AE): {ae_text}
- Habilidade Priorizada: {prioritized}
- Habilidade(s) Relacionada(s): {related}
- Conhecimento(s) Prévio(s): {prior_knowledge}
- Conteúdo(s): {', '.join(payload.conteudos)}
- Objetivo(s): {payload.objetivos}
- Duração total: {minutes} minutos (Introdução: {intro_minutes} | Desenvolvimento: {development_minutes} | Conclusão: {conclusion_minutes})
</input>

<support>
Dados complementares para enriquecer APENAS as seções já definidas. NÃO crie seções ou subtítulos além dos listados no template:
{support_text}
</support>

<instructions>
Responda EXCLUSIVAMENTE em Markdown, seguindo o template abaixo SEM alterações estruturais — mesmos títulos, mesma ordem, mesma hierarquia. Antes de redigir cada seção, raciocine internamente sobre: (a) coerência com a habilidade priorizada, (b) progressão cognitiva do aluno e (c) viabilidade prática no tempo alocado.

OBRIGAÇÕES:
1. Toda seção e subseção deve conter conteúdo substantivo (mínimo 3 frases por subseção, mínimo 1 parágrafo denso por seção principal).
2. Na "Estrutura da Aula", inclua: ações do professor, ações esperadas dos alunos, recursos/materiais e pelo menos um instrumento de avaliação formativa embutido no Desenvolvimento.
3. Nas adaptações para Educação Especial, forneça estratégias concretas e exemplificadas (materiais, recursos, mediações), não apenas enunciados genéricos.
4. Na subseção "Autismo", diferencie explicitamente estratégias para Nível 1, Nível 2 e Nível 3 de suporte (DSM-5), com pelo menos um exemplo prático por nível.
5. Use linguagem pedagógica clara, objetiva e aplicável — evite jargão desnecessário.

PROIBIÇÕES:
- NÃO use tabelas.
- NÃO adicione seções, subtítulos ou apêndices além dos definidos no template.
- NÃO inclua metadados, comentários sobre o prompt ou explicações fora do plano.
- NÃO invente habilidades, códigos BNCC ou referências que não constem nos dados de entrada.
</instructions>

<template>
# Dados Gerais
- **Disciplina:** {payload.disciplina}
- **Turma:** {payload.ano_serie}
- **Aprendizagem Essencial:** {ae_text}
- **Habilidade Priorizada:** {prioritized}
- **Habilidade(s) Relacionada(s):** {related}
- **Conhecimento(s) Prévio(s):** {prior_knowledge}
- **Conteúdo(s):** {', '.join(payload.conteudos)}
- **Objetivo(s):** {payload.objetivos}

# Estrutura da Aula

## Introdução ({intro_minutes} minutos)
[Descreva a abertura da aula: acolhimento, estratégia de engajamento inicial e ativação de conhecimentos prévios. Indique a ação do professor e a participação esperada dos alunos.]

## Desenvolvimento ({development_minutes} minutos)
[Descreva a sequência didática completa: etapas progressivas, metodologias ativas utilizadas, recursos e materiais necessários, momentos de interação e pelo menos um ponto de avaliação formativa integrada ao processo. Explicite o que o professor faz e o que os alunos fazem em cada etapa.]

## Conclusão ({conclusion_minutes} minutos)
[Descreva a sistematização dos aprendizados, a verificação da aprendizagem (instrumento ou dinâmica) e o fechamento da aula com conexão ao próximo encontro, quando aplicável.]

# Exemplos de Adaptação para a Educação Especial

## Deficiência Intelectual (DI)
[Estratégias concretas com exemplos de materiais e mediações.]

## Deficiência Auditiva (DA)
[Estratégias concretas com exemplos de materiais e mediações.]

## Surdez
[Estratégias concretas com exemplos de materiais e mediações.]

## Deficiência Visual (DV)
[Estratégias concretas com exemplos de materiais e mediações.]

## Cegueira
[Estratégias concretas com exemplos de materiais e mediações.]

## Deficiência Física (DF)
[Estratégias concretas com exemplos de materiais e mediações.]

## Autismo
[Estratégias diferenciadas por nível de suporte:
- **Nível 1** — exemplo prático
- **Nível 2** — exemplo prático
- **Nível 3** — exemplo prático]
</template>"""


async def generate_lesson_plan(payload, selected_skills, db: Session) -> dict[str, str]:
    api_key = get_setting(db, "openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave OpenRouter não configurada.")

    payload.material_context = compact_context(getattr(payload, "material_context", None))
    ae_text = _resolve_ae_text(payload, db)
    prompt = build_prompt(payload, selected_skills, ae_text)
    model_candidates = get_configured_models(db)

    # Vercel serverless functions have a maxDuration of 60s (configured in vercel.json).
    # Reserve ~8s for FastAPI overhead; httpx must complete within ~50s.
    async with httpx.AsyncClient(timeout=50) as client:
        content: str | None = None
        last_error: HTTPException | None = None

        for candidate_model in model_candidates:
            try:
                content, _finish_reason = await call_openrouter(
                    client,
                    api_key=api_key,
                    model=candidate_model,
                    prompt=prompt,
                )
                break
            except HTTPException as error:
                # Retry without material context if the provider rejects the payload.
                if payload.material_context and error.status_code in {400, 413, 422, 502, 504}:
                    payload.material_context = None
                    prompt = build_prompt(payload, selected_skills, ae_text)
                    try:
                        content, _finish_reason = await call_openrouter(
                            client,
                            api_key=api_key,
                            model=candidate_model,
                            prompt=prompt,
                        )
                        break
                    except HTTPException as retry_error:
                        last_error = retry_error
                        continue

                last_error = error
                continue

        if content is None:
            if last_error is not None:
                raise last_error
            raise HTTPException(status_code=502, detail="OpenRouter: falha ao gerar resposta.")

    html = markdown.markdown(
        content,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html",
    )
    return {"html": html, "prompt": prompt}
