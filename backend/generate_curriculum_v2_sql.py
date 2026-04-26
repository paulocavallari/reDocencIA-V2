"""Generate SQL seed for the Curriculum V2 normalized model.

Run from workspace root:
  c:/Users/Administrator/Desktop/redocêncIA/.venv/Scripts/python.exe backend/generate_curriculum_v2_sql.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.md_parser import parse_curriculum_markdown

MD_FILE = Path(__file__).resolve().parent.parent / "curriculos-priorizados-completo.md"
OUT_FILE = Path(__file__).resolve().parent / "curriculum_v2_seed.sql"


def escape_sql(value: str) -> str:
    return value.replace("'", "''")


def grade_sort_order(ano_serie: str) -> int:
    match = re.search(r"(\d+)", ano_serie)
    if not match:
        return 999
    number = int(match.group(1))
    if "série" in ano_serie.lower() or "serie" in ano_serie.lower():
        return 100 + number
    return number


def ae_sort_order(ae_codigo: str) -> int:
    match = re.search(r"(\d+)", ae_codigo)
    return int(match.group(1)) if match else 999


def main() -> None:
    rows = parse_curriculum_markdown(MD_FILE)

    # Disciplines
    discipline_names = sorted({row["disciplina"] for row in rows})
    disciplines = {name: idx for idx, name in enumerate(discipline_names, start=1)}

    # Grade levels
    grade_keys = sorted(
        {(row["nivel_ensino"], row["ano_serie"]) for row in rows},
        key=lambda it: (grade_sort_order(it[1]), it[0], it[1]),
    )
    grade_levels = {
        key: {"id": idx, "sort_order": grade_sort_order(key[1])}
        for idx, key in enumerate(grade_keys, start=1)
    }

    # Learning objectives
    learning_map: dict[tuple[str, str, str], dict[str, object]] = {}
    learning_seq: dict[tuple[str, str], list[tuple[int, tuple[str, str, str]]]] = {}
    learning_id = 0

    for row in rows:
        key = (row["disciplina"], row["ano_serie"], row["ae_codigo"])
        if key not in learning_map:
            learning_id += 1
            sort = ae_sort_order(row["ae_codigo"])
            learning_map[key] = {
                "id": learning_id,
                "discipline_id": disciplines[row["disciplina"]],
                "grade_level_id": grade_levels[(row["nivel_ensino"], row["ano_serie"])]["id"],
                "ae_codigo": row["ae_codigo"],
                "descricao": row["ae_descricao"],
                "sort_order": sort,
            }
            learning_seq.setdefault((row["disciplina"], row["ano_serie"]), []).append((sort, key))

    # Skill codes and links
    skill_codes: dict[str, dict[str, object]] = {}
    learning_skills: dict[tuple[int, int, str], dict[str, object]] = {}
    skill_id = 0
    skill_sort_map: dict[tuple[int, str], int] = {}

    # Content items and links
    content_items: dict[str, int] = {}
    learning_contents: dict[tuple[int, int], dict[str, object]] = {}
    content_id = 0
    content_sort_map: dict[int, int] = {}

    for row in rows:
        learning_key = (row["disciplina"], row["ano_serie"], row["ae_codigo"])
        learning_objective_id = int(learning_map[learning_key]["id"])

        code = row["habilidade_codigo"].strip().upper()
        if code not in skill_codes:
            skill_id += 1
            skill_codes[code] = {
                "id": skill_id,
                "descricao_referencia": row.get("habilidade_descricao") or "",
            }
        skill_code_id = int(skill_codes[code]["id"])

        skill_sort_key = (learning_objective_id, row["skill_category"])
        skill_sort_map[skill_sort_key] = skill_sort_map.get(skill_sort_key, 0) + 1
        link_key = (learning_objective_id, skill_code_id, row["skill_category"])
        if link_key not in learning_skills:
            learning_skills[link_key] = {
                "sort_order": skill_sort_map[skill_sort_key],
            }

        content_desc = row["objetos_conhecimento"].strip()
        if content_desc not in content_items:
            content_id += 1
            content_items[content_desc] = content_id
        content_item_id = content_items[content_desc]

        content_sort_map[learning_objective_id] = content_sort_map.get(learning_objective_id, 0) + 1
        lc_key = (learning_objective_id, content_item_id)
        if lc_key not in learning_contents:
            learning_contents[lc_key] = {
                "sort_order": content_sort_map[learning_objective_id],
            }

    # Sequential dependencies by discipline+year using AE numeric order
    dependencies: list[tuple[int, int, str]] = []
    for _, seq_list in learning_seq.items():
        ordered = sorted(seq_list, key=lambda it: it[0])
        prev_id: int | None = None
        for _, l_key in ordered:
            current_id = int(learning_map[l_key]["id"])
            if prev_id is not None:
                dependencies.append((current_id, prev_id, "sequencial"))
            prev_id = current_id

    with OUT_FILE.open("w", encoding="utf-8") as f:
        f.write("-- Auto-generated seed for Curriculum V2 model\n")
        f.write("-- Source: curriculos-priorizados-completo.md\n\n")
        f.write("BEGIN;\n\n")

        f.write("DELETE FROM curriculum_learning_dependencies;\n")
        f.write("DELETE FROM curriculum_learning_contents;\n")
        f.write("DELETE FROM curriculum_learning_skills;\n")
        f.write("DELETE FROM curriculum_content_items;\n")
        f.write("DELETE FROM curriculum_skill_codes;\n")
        f.write("DELETE FROM curriculum_learning_objectives;\n")
        f.write("DELETE FROM curriculum_grade_levels;\n")
        f.write("DELETE FROM curriculum_disciplines;\n\n")

        f.write("-- Disciplines\n")
        for name, did in disciplines.items():
            f.write(
                "INSERT INTO curriculum_disciplines (id, nome, created_at) "
                f"VALUES ({did}, '{escape_sql(name)}', NOW());\n"
            )

        f.write("\n-- Grade levels\n")
        for (nivel, ano), data in grade_levels.items():
            f.write(
                "INSERT INTO curriculum_grade_levels (id, nivel_ensino, ano_serie, sort_order, created_at) "
                f"VALUES ({data['id']}, '{escape_sql(nivel)}', '{escape_sql(ano)}', {data['sort_order']}, NOW());\n"
            )

        f.write("\n-- Learning objectives\n")
        for _, obj in sorted(learning_map.items(), key=lambda it: int(it[1]["id"])):
            f.write(
                "INSERT INTO curriculum_learning_objectives "
                "(id, discipline_id, grade_level_id, ae_codigo, descricao, sort_order, created_at) "
                f"VALUES ({obj['id']}, {obj['discipline_id']}, {obj['grade_level_id']}, "
                f"'{escape_sql(str(obj['ae_codigo']))}', '{escape_sql(str(obj['descricao']))}', "
                f"{obj['sort_order']}, NOW());\n"
            )

        f.write("\n-- Skill codes\n")
        for code, data in sorted(skill_codes.items(), key=lambda it: int(it[1]["id"])):
            description = str(data["descricao_referencia"] or "")
            description_sql = f"'{escape_sql(description)}'" if description else "NULL"
            f.write(
                "INSERT INTO curriculum_skill_codes (id, codigo, descricao_referencia, created_at) "
                f"VALUES ({data['id']}, '{escape_sql(code)}', {description_sql}, NOW());\n"
            )

        f.write("\n-- Learning x skills\n")
        for (learning_objective_id, skill_code_id, categoria), data in sorted(
            learning_skills.items(), key=lambda it: (it[0][0], it[0][2], it[1]["sort_order"])
        ):
            f.write(
                "INSERT INTO curriculum_learning_skills "
                "(learning_objective_id, skill_code_id, categoria, sort_order, created_at) "
                f"VALUES ({learning_objective_id}, {skill_code_id}, '{escape_sql(categoria)}', "
                f"{data['sort_order']}, NOW());\n"
            )

        f.write("\n-- Content items\n")
        for description, cid in sorted(content_items.items(), key=lambda it: it[1]):
            f.write(
                "INSERT INTO curriculum_content_items (id, descricao, created_at) "
                f"VALUES ({cid}, '{escape_sql(description)}', NOW());\n"
            )

        f.write("\n-- Learning x contents\n")
        for (learning_objective_id, content_item_id), data in sorted(
            learning_contents.items(), key=lambda it: (it[0][0], it[1]["sort_order"])
        ):
            f.write(
                "INSERT INTO curriculum_learning_contents "
                "(learning_objective_id, content_item_id, sort_order, created_at) "
                f"VALUES ({learning_objective_id}, {content_item_id}, {data['sort_order']}, NOW());\n"
            )

        f.write("\n-- Sequential dependencies\n")
        for learning_objective_id, prerequisite_learning_objective_id, dependency_type in dependencies:
            f.write(
                "INSERT INTO curriculum_learning_dependencies "
                "(learning_objective_id, prerequisite_learning_objective_id, dependency_type, created_at) "
                f"VALUES ({learning_objective_id}, {prerequisite_learning_objective_id}, "
                f"'{dependency_type}', NOW());\n"
            )

        f.write("\n")
        f.write("SELECT setval('curriculum_disciplines_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_disciplines), 1));\n")
        f.write("SELECT setval('curriculum_grade_levels_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_grade_levels), 1));\n")
        f.write("SELECT setval('curriculum_learning_objectives_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_learning_objectives), 1));\n")
        f.write("SELECT setval('curriculum_skill_codes_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_skill_codes), 1));\n")
        f.write("SELECT setval('curriculum_content_items_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_content_items), 1));\n")
        f.write("SELECT setval('curriculum_learning_skills_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_learning_skills), 1));\n")
        f.write("SELECT setval('curriculum_learning_contents_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_learning_contents), 1));\n")
        f.write("SELECT setval('curriculum_learning_dependencies_id_seq', COALESCE((SELECT MAX(id) FROM curriculum_learning_dependencies), 1));\n")

        f.write("\nCOMMIT;\n")

    print(f"Generated: {OUT_FILE}")
    print(f"Disciplines: {len(disciplines)}")
    print(f"Grade levels: {len(grade_levels)}")
    print(f"Learning objectives: {len(learning_map)}")
    print(f"Skill codes: {len(skill_codes)}")
    print(f"Learning x skills: {len(learning_skills)}")
    print(f"Content items: {len(content_items)}")
    print(f"Learning x contents: {len(learning_contents)}")
    print(f"Dependencies: {len(dependencies)}")


if __name__ == "__main__":
    main()
