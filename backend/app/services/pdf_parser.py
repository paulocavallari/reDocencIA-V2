from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pdfplumber


GUIDE_PREFIX = "Guia do Currículo Priorizado - "
GUIDE_SUFFIX_PATTERN = re.compile(r"\s+-\s+(AF|EM)$", re.IGNORECASE)

YEAR_PATTERN = re.compile(r"(\d{1,2})\s*[ºª°]\s*(Ano|Série)", re.IGNORECASE)
BIMESTER_PATTERN = re.compile(r"(\d)\s*[ºª°]\s*Bimestre", re.IGNORECASE)
SHORT_BIMESTER_PATTERN = re.compile(r"(\d)\s*[ºª°]\s*bim\.?\s*:", re.IGNORECASE)
SKILL_CODE_REGEX = r"(?:EF\d{2}[A-Z]{2}\d{2,3}[A-Z]?(?:\*)?|EM\d{2}[A-Z]{3}\d{3}(?:\*)?)"
SKILL_CODE_PATTERN = re.compile(SKILL_CODE_REGEX, re.IGNORECASE)
SKILL_PATTERN = re.compile(
    rf'({SKILL_CODE_REGEX})\s*[-–:]?\s*(.*?)(?={SKILL_CODE_REGEX}|$)',
    re.IGNORECASE | re.DOTALL,
)
DESCRIPTOR_PATTERN = re.compile(r"(D\d{2})")
PRIORITIZED_CATEGORY = "habilidade_priorizada"
PRIOR_KNOWLEDGE_CATEGORY = "conhecimento_previo"
RELATED_CATEGORY = "habilidade_relacionada"

DISCIPLINE_ALIASES = {
    "ciencias": "Ciências",
    "ciências": "Ciências",
    "biologia": "Biologia",
    "matematica": "Matemática",
    "matemática": "Matemática",
    "arte": "Arte",
    "educacao fisica": "Educação Física",
    "educação física": "Educação Física",
    "filosofia": "Filosofia",
    "fisica": "Física",
    "física": "Física",
    "geografia": "Geografia",
    "historia": "História",
    "história": "História",
    "lingua inglesa": "Língua Inglesa",
    "língua inglesa": "Língua Inglesa",
    "lingua portuguesa": "Língua Portuguesa",
    "língua portuguesa": "Língua Portuguesa",
    "quimica": "Química",
    "química": "Química",
    "sociologia": "Sociologia",
}


def infer_level(year_label: str) -> str:
    if "série" in year_label.lower() or "serie" in year_label.lower():
        return "Ensino Médio"
    match = YEAR_PATTERN.search(year_label)
    if not match:
        return "Ensino Fundamental: Anos Finais"
    year = int(match.group(1))
    if year <= 5:
        return "Ensino Fundamental: Anos Iniciais"
    if year <= 9:
        return "Ensino Fundamental: Anos Finais"
    return "Ensino Médio"


def infer_year_from_skill_code(skill_code: str) -> str | None:
    match = re.search(r"EF(\d{2})", skill_code or "", re.IGNORECASE)
    if not match:
        return None
    year = int(match.group(1))
    if 1 <= year <= 9:
        return f"{year}º Ano"
    return None


def extract_guide_subject_name(file_path: str | Path) -> str:
    stem = Path(file_path).stem
    if stem.startswith(GUIDE_PREFIX):
        stem = stem[len(GUIDE_PREFIX) :]
    stem = GUIDE_SUFFIX_PATTERN.sub("", stem).strip()
    return stem


def detect_curriculum_discipline(file_path: str | Path, first_page_text: str = "") -> str:
    subject_name = extract_guide_subject_name(file_path)
    normalized_subject = normalize_matching_text(subject_name)
    for alias, discipline in DISCIPLINE_ALIASES.items():
        if alias == normalized_subject:
            return discipline

    normalized_path = normalize_matching_text(str(file_path))
    for alias, discipline in DISCIPLINE_ALIASES.items():
        if alias in normalized_path:
            return discipline

    normalized_page = normalize_matching_text(first_page_text)
    for alias, discipline in DISCIPLINE_ALIASES.items():
        if alias in normalized_page:
            return discipline

    return "Ciências"


def normalize_year(text: str | None) -> str | None:
    if not text:
        return None
    match = YEAR_PATTERN.search(text)
    if not match:
        return None
    number = int(match.group(1))
    label = match.group(2).capitalize()
    ordinal = "ª" if label.lower() == "série" else "º"
    return f"{number}{ordinal} {label}"


def extract_skill_entries(raw_text: str) -> list[tuple[str, str]]:
    entries = []
    for code, description in SKILL_PATTERN.findall(raw_text.replace("\n", " ")):
        cleaned = re.sub(r"\s+", " ", description).strip(" -–:")
        entries.append((code.upper(), cleaned or "Descrição não identificada."))
    return entries


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.replace("\u200b", " ")).strip(" .")


def clean_content_text(value: str | None) -> str:
    text = clean_text(value)
    text = re.sub(r"^(Materiais|Digitais|Livro do Estudante|Bloco temático|Bloco tematico)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(^|\s)[•\-]+\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def normalize_matching_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    without_symbols = re.sub(r"[^a-zA-Z0-9]+", " ", without_accents.lower())
    return re.sub(r"\s+", " ", without_symbols).strip()


def extract_codes(raw_text: str) -> list[str]:
    codes = []
    seen = set()
    for match in SKILL_CODE_PATTERN.findall(raw_text or ""):
        normalized = match.upper()
        if normalized not in seen:
            seen.add(normalized)
            codes.append(normalized)
    return codes


def extract_section(raw_text: str, start_marker: str, end_markers: list[str]) -> str:
    if start_marker not in raw_text:
        return ""
    section = raw_text.split(start_marker, 1)[1]
    cut_index = len(section)
    for marker in end_markers:
        marker_index = section.find(marker)
        if marker_index != -1:
            cut_index = min(cut_index, marker_index)
    return section[:cut_index]


def should_ignore_skill_line(line: str) -> bool:
    lowered = normalize_matching_text(line)
    ignored_fragments = [
        "de olho na prova paulista",
        "de olho no provao paulista",
        "de olho no saeb",
        "de olho no saresp",
        "em desenvolvimento",
        "links",
    ]
    return any(fragment in lowered for fragment in ignored_fragments)


def parse_skill_section(raw_text: str) -> list[tuple[str, str]]:
    lines = [clean_text(line) for line in (raw_text or "").splitlines() if clean_text(line)]
    if not lines:
        return []

    entries = []
    pending_lines = []
    current_codes: list[str] = []
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_codes, current_parts, pending_lines
        if not current_codes:
            return
        description = clean_text(" ".join(current_parts)) or "Descrição curricular identificada no Guia do Currículo Priorizado."
        for code in current_codes:
            entries.append((code, description))
        current_codes = []
        current_parts = []
        pending_lines = []

    for raw_line in lines:
        cleaned_line = re.sub(r"^[•\-]+\s*", "", raw_line).strip()
        if not cleaned_line or should_ignore_skill_line(cleaned_line):
            continue
        if normalize_matching_text(cleaned_line) == "nao ha":
            return []

        codes = extract_codes(cleaned_line)
        if codes:
            flush_current()
            current_codes = codes
            remaining_text = clean_text(SKILL_CODE_PATTERN.sub(" ", cleaned_line))
            current_parts = [part for part in [*pending_lines, remaining_text] if part]
            continue

        if current_codes:
            current_parts.append(cleaned_line)
        else:
            pending_lines.append(cleaned_line)

    flush_current()
    return entries


def parse_ae_contents(page_text: str) -> list[dict[str, str | int]]:
    lines = [clean_text(line) for line in page_text.splitlines() if clean_text(line)]
    start_index = next(
        (index for index, line in enumerate(lines) if "Conteúdos" in line or "Conteudos" in line or "Bloco temático" in line or "Bloco tematico" in line),
        None,
    )
    if start_index is None:
        return []

    rows = []
    buffer = ""
    for line in lines[start_index + 1 :]:
        if line.startswith("AE") and "Para desenvolver" not in line:
            break
        if line in {
            "Materiais Digitais",
            "Livro do Estudante",
            "Materiais",
            "Digitais Estudante",
            "Digitais",
            "Estudante",
            "Livro do",
        }:
            continue

        buffer = f"{buffer} {line}".strip()
        bimester_match = SHORT_BIMESTER_PATTERN.search(buffer) or BIMESTER_PATTERN.search(buffer)
        if not bimester_match:
            continue

        content_value = clean_content_text(buffer[: bimester_match.start()])
        if content_value:
            rows.append({"content": content_value, "bimestre": int(bimester_match.group(1))})
        buffer = ""
    return rows


def extract_matrix_header_skill(table: list[list[str | None]]) -> tuple[str, str] | None:
    if not table or not table[0] or len(table[0]) < 2:
        return None
    skill_cell = clean_text(table[0][1])
    codes = extract_codes(skill_cell)
    if not codes:
        return None
    description = clean_text(SKILL_CODE_PATTERN.sub("", skill_cell)).lstrip("-–: ")
    return codes[0], description


def normalize_table_headers(table: list[list[str | None]]) -> tuple[list[str], int]:
    if not table:
        return [], 1

    first_row = [re.sub(r"\s+", " ", (cell or "")).strip().lower() for cell in table[0]]
    first_row_text = " | ".join(first_row)
    if len(table) > 1:
        second_row = [re.sub(r"\s+", " ", (cell or "")).strip().lower() for cell in table[1]]
        non_empty_first = sum(1 for cell in first_row if cell)
        second_has_aula = any(cell == "aula" for cell in second_row if cell)
        first_is_sparse_scope_header = second_has_aula and non_empty_first <= 3 and any(
            keyword in first_row_text for keyword in ["habilidade", "objetivo", "aprendizagem essencial"]
        )
        if first_is_sparse_scope_header:
            max_len = max(len(first_row), len(second_row))
            combined = []
            for index in range(max_len):
                parts = []
                if index < len(second_row) and second_row[index]:
                    parts.append(second_row[index])
                if index < len(first_row) and first_row[index]:
                    parts.append(first_row[index])
                combined.append(" ".join(parts).strip())
            return combined, 2

    if any(keyword in first_row_text for keyword in ["conteúdo", "conteudo", "habilidade", "grupo", "objetivo"]):
        return first_row, 1

    if len(table) < 2:
        return first_row, 1

    second_row = [re.sub(r"\s+", " ", (cell or "")).strip().lower() for cell in table[1]]
    max_len = max(len(first_row), len(second_row))
    combined = []
    for index in range(max_len):
        parts = []
        if index < len(first_row) and first_row[index]:
            parts.append(first_row[index])
        if index < len(second_row) and second_row[index]:
            parts.append(second_row[index])
        combined.append(" ".join(parts).strip())

    if any(keyword in " | ".join(combined) for keyword in ["conteúdo", "conteudo", "habilidade", "grupo", "objetivo"]):
        return combined, 2
    return first_row, 1


def detect_sparse_scope_layout(table: list[list[str | None]], headers: list[str], header_rows: int) -> dict[str, int | None] | None:
    if len(table) <= header_rows:
        return None

    row_for_structure = table[header_rows]
    objectives_index = next((i for i, header in enumerate(headers) if "objetivo" in header), None)
    skill_index = next((i for i, header in enumerate(headers) if "habilidade" in header), None)
    ae_index = next((i for i, header in enumerate(headers) if "aprendizagem essencial" in header), None)
    has_aula_header = header_rows > 1 and any(clean_text(cell).lower() == "aula" for cell in table[1] if cell)

    if not has_aula_header or objectives_index is None or skill_index is None or ae_index is None:
        return None

    title_index = 1 if len(row_for_structure) > 1 else 0
    content_candidates = [
        index
        for index in range(title_index + 1, objectives_index)
        if index < len(row_for_structure) and clean_text(row_for_structure[index])
    ]
    if not content_candidates:
        return None

    return {
        "unit_index": None,
        "content_index": content_candidates[0],
        "objectives_index": objectives_index,
        "skill_index": skill_index,
        "title_index": title_index,
        "data_start": header_rows,
    }


def split_content_fragments(content_value: str) -> list[str]:
    return [
        fragment
        for fragment in (normalize_matching_text(part) for part in re.split(r"\.\s*", content_value))
        if len(fragment) >= 6
    ]


def resolve_related_scope_rows(scope_rows: list[dict], year: str | None, bimestre: int, content_value: str) -> list[dict]:
    normalized_target = normalize_matching_text(content_value)
    fragments = split_content_fragments(content_value)
    matches = []

    for row in scope_rows:
        if row["bimestre"] != bimestre:
            continue
        if year is not None and row["ano_serie"] != year:
            continue
        candidate = row["objetos_conhecimento"]
        normalized_candidate = normalize_matching_text(candidate)
        if not normalized_candidate:
            continue
        if (
            normalized_candidate == normalized_target
            or normalized_candidate in normalized_target
            or normalized_target in normalized_candidate
            or any(fragment in normalized_candidate for fragment in fragments)
        ):
            key = (row["ano_serie"], candidate, row.get("unidade_tematica"))
            if key not in {(item["ano_serie"], item["objetos_conhecimento"], item.get("unidade_tematica")) for item in matches}:
                matches.append(row)

    return matches


def resolve_related_contents(scope_rows: list[dict], year: str | None, bimestre: int, content_value: str) -> list[str]:
    matches = resolve_related_scope_rows(scope_rows, year, bimestre, content_value)
    return [row["objetos_conhecimento"] for row in matches] or [clean_content_text(content_value)]


def parse_ae_page(page_text: str, current_year: str | None) -> dict | None:
    if "Habilidade priorizada" not in page_text or "Conhecimentos Prévios" not in page_text:
        return None

    # Try to extract AE code and description
    ae_codigo = ""
    ae_descricao = ""
    lines = page_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("AE") and "-" in line:
            parts = line.split("-", 1)
            ae_codigo = parts[0].strip()
            desc_part = parts[1].strip()
            # sometimes the description spans multiple lines
            if i + 1 < len(lines) and "Habilidade priorizada" not in lines[i+1]:
                desc_part += " " + lines[i+1].strip()
            ae_descricao = clean_text(desc_part)
            break

    prioritized_section = page_text.split("Habilidade priorizada:", 1)[1]
    prioritized_codes = extract_codes(prioritized_section)
    if not prioritized_codes:
        return None

    resolved_year = current_year
    prior_knowledge_section = extract_section(
        page_text,
        "Conhecimentos Prévios",
        ["Para desenvolver a aprendizagem:", "AE1 AE2", "AE1 AE2 AE3", "AE1 AE2 AE3 AE4", "AE3 AE4 AE5 AE6"],
    )
    related_section = extract_section(page_text, "Habilidades Relacionadas", ["Conhecimentos Prévios"])
    contents = parse_ae_contents(page_text)
    if not contents:
        return None

    return {
        "ano_serie": resolved_year,
        "ae_codigo": ae_codigo or "AE?",
        "ae_descricao": ae_descricao or "Descrição da Aprendizagem Essencial.",
        "prioritized_code": prioritized_codes[0],
        "related_entries": parse_skill_section(related_section),
        "prior_knowledge_entries": parse_skill_section(prior_knowledge_section),
        "contents": contents,
    }


def parse_curriculum_pdf(file_path: str | Path) -> list[dict]:
    current_year: str | None = None
    current_bimester: int | None = None
    matrix_by_skill: dict[str, dict[str, str | None]] = {}
    skill_descriptions: dict[str, str] = {}
    prioritized_rows: list[dict] = []
    ae_pages: list[dict] = []
    source_file = str(file_path)
    discipline = "Ciências"

    with pdfplumber.open(file_path) as pdf:
        first_page_text = pdf.pages[1].extract_text() if len(pdf.pages) > 1 else pdf.pages[0].extract_text()
        discipline = detect_curriculum_discipline(file_path, first_page_text or "")
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            normalized_text = re.sub(r"\s+", " ", page_text)

            year = normalize_year(normalized_text)
            if year:
                current_year = year

            bimester_match = BIMESTER_PATTERN.search(normalized_text)
            if bimester_match:
                current_bimester = int(bimester_match.group(1))

            ae_page = parse_ae_page(page_text, current_year)
            if ae_page is not None:
                ae_pages.append(ae_page)

            tables = page.extract_tables() or []
            for table in tables:
                if not table or len(table) < 2:
                    continue

                headers, header_rows = normalize_table_headers(table)
                is_scope_table = any("conteúdo" in header or "conteudo" in header for header in headers) and any(
                    "habilidade" in header for header in headers
                )
                is_matrix_table = len(headers) >= 5 and any("grupo" in header for header in headers)
                sparse_scope_layout = None
                if not is_scope_table:
                    sparse_scope_layout = detect_sparse_scope_layout(table, headers, header_rows)
                    is_scope_table = sparse_scope_layout is not None

                if is_matrix_table:
                    header_skill = extract_matrix_header_skill(table)
                    if header_skill:
                        code, description = header_skill
                        if description:
                            skill_descriptions[code] = description

                        if len(table) > 1:
                            matrix_row = table[1]
                            group_headers = [headers[index].title() for index in range(4, len(headers)) if headers[index].startswith("grupo")]
                            non_empty_groups = []
                            for offset, group_name in enumerate(group_headers, start=4):
                                if offset < len(matrix_row) and clean_text(matrix_row[offset]):
                                    non_empty_groups.append(group_name)
                            descriptor_match = DESCRIPTOR_PATTERN.search(" ".join(clean_text(cell) for cell in matrix_row if cell))
                            matrix_by_skill[code] = {
                                "matriz_descritor": descriptor_match.group(1).upper() if descriptor_match else None,
                                "matriz_nivel": ", ".join(non_empty_groups) or None,
                            }

                    for row in table[header_rows - 1 :]:
                        if not row or len(row) < 4:
                            continue
                        skill_cell = clean_text(row[1] if len(row) > 1 else "")
                        codes = extract_codes(skill_cell)
                        if not codes:
                            continue
                        code = codes[0]
                        description = clean_text(SKILL_CODE_PATTERN.sub("", skill_cell))
                        if description:
                            description = description.lstrip("-–: ")
                            skill_descriptions[code] = description

                        group_headers = [headers[index].title() for index in range(4, len(headers)) if headers[index].startswith("grupo")]
                        non_empty_groups = []
                        for offset, group_name in enumerate(group_headers, start=4):
                            if offset < len(row) and clean_text(row[offset]):
                                non_empty_groups.append(group_name)

                        descriptor_match = DESCRIPTOR_PATTERN.search(" ".join(clean_text(cell) for cell in row if cell))
                        matrix_by_skill[code] = {
                            "matriz_descritor": descriptor_match.group(1).upper() if descriptor_match else None,
                            "matriz_nivel": ", ".join(non_empty_groups) or None,
                        }
                    continue

                if not is_scope_table:
                    continue

                unit_index = next((i for i, header in enumerate(headers) if "unidade" in header), None)
                content_index = next((i for i, header in enumerate(headers) if "conteúdo" in header or "conteudo" in header), None)
                objectives_index = next((i for i, header in enumerate(headers) if "objetivo" in header), None)
                skill_index = next((i for i, header in enumerate(headers) if "habilidade" in header), None)
                title_index = 1 if len(headers) > 1 else 0
                data_start = header_rows

                if sparse_scope_layout is not None:
                    unit_index = sparse_scope_layout["unit_index"]
                    content_index = sparse_scope_layout["content_index"]
                    objectives_index = sparse_scope_layout["objectives_index"]
                    skill_index = sparse_scope_layout["skill_index"]
                    title_index = sparse_scope_layout["title_index"]
                    data_start = sparse_scope_layout["data_start"]

                if content_index is None or skill_index is None:
                    continue

                for row in table[data_start:]:
                    if not row:
                        continue
                    unit_value = clean_text(row[unit_index]) if unit_index is not None and unit_index < len(row) else ""
                    content_value = clean_content_text(row[content_index]) if content_index < len(row) else ""
                    title_value = clean_text(row[title_index]) if title_index < len(row) else ""
                    objectives_value = clean_text(row[objectives_index]) if objectives_index is not None and objectives_index < len(row) else ""
                    skill_value = clean_text(row[skill_index]) if skill_index < len(row) else ""

                    if not current_year or not current_bimester or not skill_value:
                        continue

                    resolved_content = content_value or clean_content_text(title_value)
                    if not resolved_content:
                        continue

                    for code in extract_codes(skill_value):
                        matrix_data = matrix_by_skill.get(code, {})
                        prioritized_rows.append(
                            {
                                "nivel_ensino": infer_level(current_year),
                                "disciplina": discipline,
                                "ano_serie": current_year,
                                "bimestre": current_bimester,
                                "unidade_tematica": unit_value or None,
                                "objetos_conhecimento": resolved_content,
                                "habilidade_codigo": code,
                                "habilidade_descricao": skill_descriptions.get(code, objectives_value or "Descrição curricular a complementar."),
                                "skill_category": PRIORITIZED_CATEGORY,
                                "objetivos": objectives_value or None,
                                "matriz_nivel": matrix_data.get("matriz_nivel"),
                                "matriz_descritor": matrix_data.get("matriz_descritor"),
                                "source_file": source_file,
                            }
                        )

    for row in prioritized_rows:
        row["ae_codigo"] = None
        row["ae_descricao"] = None
        matrix_data = matrix_by_skill.get(row["habilidade_codigo"], {})
        if not row["matriz_nivel"] and matrix_data.get("matriz_nivel"):
            row["matriz_nivel"] = matrix_data["matriz_nivel"]
        if not row["matriz_descritor"] and matrix_data.get("matriz_descritor"):
            row["matriz_descritor"] = matrix_data["matriz_descritor"]
        preferred_description = skill_descriptions.get(row["habilidade_codigo"])
        if preferred_description and (not row["habilidade_descricao"] or "Descrição curricular a complementar" in row["habilidade_descricao"]):
            row["habilidade_descricao"] = preferred_description

    parsed_rows = list(prioritized_rows)
    prioritized_lookup = {(row["ano_serie"], row["bimestre"], row["habilidade_codigo"]): row for row in prioritized_rows}
    for ae_page in ae_pages:
        year = ae_page["ano_serie"]
        ae_codigo = ae_page.get("ae_codigo")
        ae_descricao = ae_page.get("ae_descricao")
        prioritized_code = ae_page["prioritized_code"]

        for row in parsed_rows:
            if row["habilidade_codigo"] == prioritized_code and row["ano_serie"] == year:
                row["ae_codigo"] = ae_codigo
                row["ae_descricao"] = ae_descricao

        for content in ae_page["contents"]:
            scope_matches = resolve_related_scope_rows(prioritized_rows, year, content["bimestre"], content["content"])
            prioritized_row = prioritized_lookup.get((year, content["bimestre"], ae_page["prioritized_code"])) if year else None
            if prioritized_row is None:
                prioritized_row = next(
                    (row for row in scope_matches if row["habilidade_codigo"] == ae_page["prioritized_code"]),
                    scope_matches[0] if scope_matches else None,
                )

            target_rows = scope_matches or [
                {
                    "ano_serie": year,
                    "bimestre": content["bimestre"],
                    "unidade_tematica": prioritized_row["unidade_tematica"] if prioritized_row else None,
                    "objetos_conhecimento": clean_content_text(content["content"]),
                }
            ]

            for code, description in ae_page["related_entries"]:
                for target_row in target_rows:
                    resolved_year = target_row["ano_serie"] or year or "9º Ano"
                    parsed_rows.append(
                        {
                            "nivel_ensino": infer_level(resolved_year),
                            "disciplina": discipline,
                            "ano_serie": target_row["ano_serie"],
                            "bimestre": target_row["bimestre"],
                            "unidade_tematica": target_row.get("unidade_tematica"),
                            "objetos_conhecimento": target_row["objetos_conhecimento"],
                            "habilidade_codigo": code,
                            "habilidade_descricao": description,
                            "skill_category": RELATED_CATEGORY,
                            "ae_codigo": ae_codigo,
                            "ae_descricao": ae_descricao,
                            "objetivos": None,
                            "matriz_nivel": None,
                            "matriz_descritor": None,
                            "source_file": source_file,
                        }
                    )

            for code, description in ae_page["prior_knowledge_entries"]:
                for target_row in target_rows:
                    resolved_year = target_row["ano_serie"] or year or "9º Ano"
                    parsed_rows.append(
                        {
                            "nivel_ensino": infer_level(resolved_year),
                            "disciplina": discipline,
                            "ano_serie": target_row["ano_serie"],
                            "bimestre": target_row["bimestre"],
                            "unidade_tematica": target_row.get("unidade_tematica"),
                            "objetos_conhecimento": target_row["objetos_conhecimento"],
                            "habilidade_codigo": code,
                            "habilidade_descricao": description,
                            "skill_category": PRIOR_KNOWLEDGE_CATEGORY,
                            "ae_codigo": ae_codigo,
                            "ae_descricao": ae_descricao,
                            "objetivos": None,
                            "matriz_nivel": None,
                            "matriz_descritor": None,
                            "source_file": source_file,
                        }
                    )

    unique_rows = {}
    for row in parsed_rows:
        key = (
            row["disciplina"],
            row["ano_serie"],
            row["bimestre"],
            row["objetos_conhecimento"],
            row["habilidade_codigo"],
            row["skill_category"],
        )
        unique_rows[key] = row
    return list(unique_rows.values())
