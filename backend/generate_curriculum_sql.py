"""Generate SQL migration from the markdown curriculum file.

Run from workspace root:
  python backend/generate_curriculum_sql.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.md_parser import parse_curriculum_markdown

MD_FILE = Path(__file__).resolve().parent.parent / "curriculos-priorizados-completo.md"


def escape_sql(val: str) -> str:
    return val.replace("'", "''")


def main():
    rows = parse_curriculum_markdown(MD_FILE)

    # ── Deduplicate entities ──
    # AEs: unique by (nivel_ensino, disciplina, ano_serie, ae_codigo)
    ae_map: dict[tuple, dict] = {}
    # Contents: unique by descricao
    content_map: dict[str, int] = {}
    # Skills: unique by (ae_key, habilidade_codigo, skill_category)
    skill_map: dict[tuple, dict] = {}
    # Links: (skill_key, content_desc)
    links: set[tuple] = set()

    ae_id = 0
    skill_id = 0
    content_id = 0

    for row in rows:
        ae_key = (row["nivel_ensino"], row["disciplina"], row["ano_serie"], row["ae_codigo"])
        if ae_key not in ae_map:
            ae_id += 1
            ae_map[ae_key] = {
                "id": ae_id,
                "nivel_ensino": row["nivel_ensino"],
                "disciplina": row["disciplina"],
                "ano_serie": row["ano_serie"],
                "codigo": row["ae_codigo"],
                "descricao": row["ae_descricao"],
            }

        content_desc = row["objetos_conhecimento"]
        if content_desc not in content_map:
            content_id += 1
            content_map[content_desc] = content_id

        sk_key = (ae_key, row["habilidade_codigo"], row["skill_category"])
        if sk_key not in skill_map:
            skill_id += 1
            skill_map[sk_key] = {
                "id": skill_id,
                "ae_id": ae_map[ae_key]["id"],
                "codigo": row["habilidade_codigo"],
                "descricao": row["habilidade_descricao"],
                "tipo": row["skill_category"],
            }

        link = (skill_map[sk_key]["id"], content_map[content_desc])
        links.add(link)

    # ── Print stats ──
    print(f"-- Parsed {len(rows)} raw rows", file=sys.stderr)
    print(f"-- {len(ae_map)} AEs", file=sys.stderr)
    print(f"-- {len(skill_map)} skills", file=sys.stderr)
    print(f"-- {len(content_map)} contents", file=sys.stderr)
    print(f"-- {len(links)} skill_content links", file=sys.stderr)

    # Count by discipline
    disciplines = {}
    for key, ae in ae_map.items():
        disciplines.setdefault(ae["disciplina"], 0)
        disciplines[ae["disciplina"]] += 1
    for d, c in sorted(disciplines.items()):
        print(f"--   {d}: {c} AEs", file=sys.stderr)

    # ── Generate SQL ──
    out = Path(__file__).resolve().parent / "curriculum_migration.sql"
    with open(out, "w", encoding="utf-8") as f:
        f.write("-- Auto-generated curriculum data migration\n")
        f.write("-- Source: curriculos-priorizados-completo.md\n\n")

        # Clear existing relational data
        f.write("DELETE FROM skill_content;\n")
        f.write("DELETE FROM curriculum_skills;\n")
        f.write("DELETE FROM curriculum_contents;\n")
        f.write("DELETE FROM aprendizagens_essenciais;\n\n")

        # AEs (bimestre = NULL)
        f.write("-- Aprendizagens Essenciais\n")
        for ae in ae_map.values():
            f.write(
                f"INSERT INTO aprendizagens_essenciais (id, nivel_ensino, disciplina, ano_serie, bimestre, codigo, descricao, created_at) "
                f"VALUES ({ae['id']}, '{escape_sql(ae['nivel_ensino'])}', '{escape_sql(ae['disciplina'])}', "
                f"'{escape_sql(ae['ano_serie'])}', NULL, '{escape_sql(ae['codigo'])}', "
                f"'{escape_sql(ae['descricao'])}', NOW());\n"
            )

        f.write("\n-- Curriculum Contents\n")
        for desc, cid in content_map.items():
            f.write(
                f"INSERT INTO curriculum_contents (id, descricao, unidade_tematica) "
                f"VALUES ({cid}, '{escape_sql(desc)}', NULL);\n"
            )

        f.write("\n-- Curriculum Skills\n")
        for sk in skill_map.values():
            f.write(
                f"INSERT INTO curriculum_skills (id, aprendizagem_essencial_id, codigo, descricao, tipo) "
                f"VALUES ({sk['id']}, {sk['ae_id']}, '{escape_sql(sk['codigo'])}', "
                f"'{escape_sql(sk['descricao'])}', '{escape_sql(sk['tipo'])}');\n"
            )

        f.write("\n-- Skill-Content links\n")
        for sid, cid in sorted(links):
            f.write(f"INSERT INTO skill_content (skill_id, content_id) VALUES ({sid}, {cid});\n")

        # Reset sequences
        f.write("\n-- Reset sequences\n")
        f.write("SELECT setval('aprendizagens_essenciais_id_seq', (SELECT COALESCE(MAX(id), 1) FROM aprendizagens_essenciais));\n")
        f.write("SELECT setval('curriculum_skills_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_skills));\n")
        f.write("SELECT setval('curriculum_contents_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_contents));\n")

    print(f"\nSQL written to: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
