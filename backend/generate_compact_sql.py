"""Generate a compact SQL migration using batch INSERT statements."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.md_parser import parse_curriculum_markdown

MD_FILE = Path(__file__).resolve().parent.parent / "curriculos-priorizados-completo.md"


def e(val: str) -> str:
    return val.replace("'", "''")


def main():
    rows = parse_curriculum_markdown(MD_FILE)

    ae_map: dict[tuple, dict] = {}
    content_map: dict[str, int] = {}
    skill_map: dict[tuple, dict] = {}
    links: set[tuple] = set()

    ae_id = skill_id = content_id = 0

    for row in rows:
        ae_key = (row["nivel_ensino"], row["disciplina"], row["ano_serie"], row["ae_codigo"])
        if ae_key not in ae_map:
            ae_id += 1
            ae_map[ae_key] = {"id": ae_id, **{k: row[k] for k in ("nivel_ensino", "disciplina", "ano_serie", "ae_codigo", "ae_descricao")}}

        cd = row["objetos_conhecimento"]
        if cd not in content_map:
            content_id += 1
            content_map[cd] = content_id

        sk_key = (ae_key, row["habilidade_codigo"], row["skill_category"])
        if sk_key not in skill_map:
            skill_id += 1
            skill_map[sk_key] = {"id": skill_id, "ae_id": ae_map[ae_key]["id"], "codigo": row["habilidade_codigo"], "descricao": row["habilidade_descricao"], "tipo": row["skill_category"]}

        links.add((skill_map[sk_key]["id"], content_map[cd]))

    # Generate compact batch SQL files (one per section)
    out_dir = Path(__file__).resolve().parent / "migration_chunks"
    out_dir.mkdir(exist_ok=True)

    # Chunk 1: Cleanup + AEs
    with open(out_dir / "01_cleanup_aes.sql", "w", encoding="utf-8") as f:
        f.write("DELETE FROM skill_content;\nDELETE FROM curriculum_skills;\nDELETE FROM curriculum_contents;\nDELETE FROM aprendizagens_essenciais;\n\n")
        vals = []
        for a in ae_map.values():
            vals.append(f"({a['id']}, '{e(a['nivel_ensino'])}', '{e(a['disciplina'])}', '{e(a['ano_serie'])}', NULL, '{e(a['ae_codigo'])}', '{e(a['ae_descricao'])}', NOW())")
        f.write("INSERT INTO aprendizagens_essenciais (id, nivel_ensino, disciplina, ano_serie, bimestre, codigo, descricao, created_at) VALUES\n")
        f.write(",\n".join(vals))
        f.write(";\n")

    # Chunk 2: Contents
    with open(out_dir / "02_contents.sql", "w", encoding="utf-8") as f:
        vals = [f"({cid}, '{e(desc)}', NULL)" for desc, cid in content_map.items()]
        f.write("INSERT INTO curriculum_contents (id, descricao, unidade_tematica) VALUES\n")
        f.write(",\n".join(vals))
        f.write(";\n")

    # Chunk 3: Skills (split into sub-chunks of ~400)
    skill_list = list(skill_map.values())
    chunk_size = 400
    for i in range(0, len(skill_list), chunk_size):
        batch = skill_list[i:i+chunk_size]
        idx = i // chunk_size
        with open(out_dir / f"03_skills_{idx}.sql", "w", encoding="utf-8") as f:
            vals = [f"({s['id']}, {s['ae_id']}, '{e(s['codigo'])}', '{e(s['descricao'])}', '{e(s['tipo'])}')" for s in batch]
            f.write("INSERT INTO curriculum_skills (id, aprendizagem_essencial_id, codigo, descricao, tipo) VALUES\n")
            f.write(",\n".join(vals))
            f.write(";\n")

    # Chunk 4: Links (split into sub-chunks of ~2000)
    link_list = sorted(links)
    chunk_size = 2000
    for i in range(0, len(link_list), chunk_size):
        batch = link_list[i:i+chunk_size]
        idx = i // chunk_size
        with open(out_dir / f"04_links_{idx}.sql", "w", encoding="utf-8") as f:
            vals = [f"({sid}, {cid})" for sid, cid in batch]
            f.write("INSERT INTO skill_content (skill_id, content_id) VALUES\n")
            f.write(",\n".join(vals))
            f.write(";\n")

    # Chunk 5: Reset sequences
    with open(out_dir / "05_sequences.sql", "w", encoding="utf-8") as f:
        f.write("SELECT setval('aprendizagens_essenciais_id_seq', (SELECT COALESCE(MAX(id), 1) FROM aprendizagens_essenciais));\n")
        f.write("SELECT setval('curriculum_skills_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_skills));\n")
        f.write("SELECT setval('curriculum_contents_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_contents));\n")

    # Print file list
    for f in sorted(out_dir.iterdir()):
        print(f"{f.name}: {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
