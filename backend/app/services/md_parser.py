"""Parser for curriculos-priorizados-completo.md structured markdown file.

Reads the hierarchical Markdown and returns flat dicts suitable for
populating AprendizagemEssencial, CurriculumSkill, CurriculumContent
and skill_content tables.
"""
from __future__ import annotations

import re
from pathlib import Path

YEAR_RE = re.compile(r"^##\s+(\d{1,2})\s*[ºª°]\s*(Ano|Série)\s*$", re.IGNORECASE)
AE_RE = re.compile(r"^###\s+(AE\d+)\s*[-–—]\s*(.+)$")
SKILL_CODE_RE = re.compile(
    r"(EF\d{2}[A-Z]{2}\d{2,3}[A-Z]?|EM\d{2}[A-Z]{3}\d{3})", re.IGNORECASE
)
DASH_ONLY_RE = re.compile(r"^[—–\-]+$")

DISCIPLINE_NAMES = {
    "Arte", "Matemática", "Língua Portuguesa", "Educação Física",
    "Geografia", "Biologia", "Ciências", "Filosofia", "Física",
    "Química", "Sociologia",
}


def _infer_level(year_label: str) -> str:
    """Ano → Anos Finais, Série → Ensino Médio."""
    if "série" in year_label.lower() or "serie" in year_label.lower():
        return "Ensino Médio"
    m = re.search(r"(\d+)", year_label)
    if not m:
        return "Ensino Fundamental: Anos Finais"
    year = int(m.group(1))
    if year <= 5:
        return "Ensino Fundamental: Anos Iniciais"
    return "Ensino Fundamental: Anos Finais"


def _extract_codes(text: str) -> list[str]:
    """Return uppercased skill codes found in *text*."""
    if DASH_ONLY_RE.match(text.strip()):
        return []
    return [c.upper() for c in SKILL_CODE_RE.findall(text)]


def _normalize_year(number: int, label: str) -> str:
    ordinal = "ª" if label.lower() == "série" else "º"
    return f"{number}{ordinal} {label.capitalize()}"


def parse_curriculum_markdown(file_path: str | Path) -> list[dict]:
    """Parse *file_path* and return a list of flat row dicts.

    Each dict represents one (skill, content) pair with all context
    fields needed by the import pipeline.
    """
    lines = Path(file_path).read_text(encoding="utf-8").splitlines()

    discipline: str | None = None
    year: str | None = None
    ae: dict | None = None
    section: str | None = None
    all_aes: list[dict] = []

    def _flush_ae():
        nonlocal ae
        if ae and ae.get("discipline") and ae.get("year"):
            all_aes.append(ae)
        ae = None

    for raw_line in lines:
        stripped = raw_line.strip()

        # ── H2: discipline or year/series ──
        if stripped.startswith("## ") and not stripped.startswith("### "):
            heading = stripped[3:].strip()

            ym = YEAR_RE.match(stripped)
            if ym:
                _flush_ae()
                year = _normalize_year(int(ym.group(1)), ym.group(2))
                section = None
                continue

            if heading in DISCIPLINE_NAMES:
                _flush_ae()
                discipline = heading
                year = None
                section = None
                continue

            # Unknown h2 (index, etc.) – ignore
            continue

        # ── H3: Aprendizagem Essencial ──
        am = AE_RE.match(stripped)
        if am:
            _flush_ae()
            ae = {
                "codigo": am.group(1),
                "descricao": am.group(2).strip(),
                "discipline": discipline,
                "year": year,
                "priorizada": [],
                "relacionada": [],
                "previo": [],
                "conteudos": [],
            }
            section = None
            continue

        if ae is None:
            continue

        # ── Field markers ──
        if stripped.startswith("- **Habilidade Priorizada"):
            section = "priorizada"
            val = stripped.split(":**", 1)[1].strip() if ":**" in stripped else ""
            ae["priorizada"].extend(_extract_codes(val))
            continue

        if stripped.startswith("- **Habilidade") and "Relacionada" in stripped:
            section = "relacionada"
            val = stripped.split(":**", 1)[1].strip() if ":**" in stripped else ""
            ae["relacionada"].extend(_extract_codes(val))
            continue

        if stripped.startswith("- **Conhecimento") and "Prévio" in stripped:
            section = "previo"
            val = stripped.split(":**", 1)[1].strip() if ":**" in stripped else ""
            ae["previo"].extend(_extract_codes(val))
            continue

        if stripped.startswith("- **Conteúdos:**") or stripped.startswith("- **Bloco Temático:**"):
            section = "conteudos"
            continue

        # ── Content bullet items (indented) ──
        if section == "conteudos" and stripped.startswith("- "):
            content = stripped[2:].strip()
            if content:
                ae["conteudos"].append(content)
            continue

    _flush_ae()

    # ── Build flat rows ──
    return _build_all_rows(all_aes)


def _build_all_rows(all_aes: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for ae in all_aes:
        nivel = _infer_level(ae["year"])
        base = {
            "nivel_ensino": nivel,
            "disciplina": ae["discipline"],
            "ano_serie": ae["year"],
            "ae_codigo": ae["codigo"],
            "ae_descricao": ae["descricao"],
        }

        for content in ae["conteudos"]:
            for code in ae["priorizada"]:
                rows.append({
                    **base,
                    "habilidade_codigo": code,
                    "habilidade_descricao": ae["descricao"],
                    "skill_category": "habilidade_priorizada",
                    "objetos_conhecimento": content,
                    "unidade_tematica": None,
                })
            for code in ae["relacionada"]:
                rows.append({
                    **base,
                    "habilidade_codigo": code,
                    "habilidade_descricao": "",
                    "skill_category": "habilidade_relacionada",
                    "objetos_conhecimento": content,
                    "unidade_tematica": None,
                })
            for code in ae["previo"]:
                rows.append({
                    **base,
                    "habilidade_codigo": code,
                    "habilidade_descricao": "",
                    "skill_category": "conhecimento_previo",
                    "objetos_conhecimento": content,
                    "unidade_tematica": None,
                })
    return rows
