"""Apply one or more SQL files to a Supabase project via Management API.

Usage examples:
  c:/Users/Administrator/Desktop/redocêncIA/.venv/Scripts/python.exe backend/apply_sql_files_supabase.py \
      --project-ref zilkfhkwxyroobastsqj \
      --files backend/migration_chunks/01_cleanup_aes.sql backend/migration_chunks/02_contents.sql

  c:/Users/Administrator/Desktop/redocêncIA/.venv/Scripts/python.exe backend/apply_sql_files_supabase.py \
      --project-ref zilkfhkwxyroobastsqj \
      --glob "backend/migration_chunks/03_skills_*.sql"

Requires SUPABASE_ACCESS_TOKEN in environment.
"""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply SQL files to Supabase Management API")
    parser.add_argument("--project-ref", required=True, help="Supabase project ref (ex: zilkfhkwxyroobastsqj)")
    parser.add_argument("--files", nargs="*", default=[], help="Explicit SQL files to execute in order")
    parser.add_argument("--glob", dest="globs", nargs="*", default=[], help="Glob patterns expanded and appended in sorted order")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per SQL file in seconds")
    return parser.parse_args()


def resolve_files(files: list[str], globs: list[str]) -> list[Path]:
    resolved: list[Path] = []

    for raw in files:
        p = Path(raw)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {raw}")
        resolved.append(p)

    for pattern in globs:
        matches = sorted(glob.glob(pattern))
        for match in matches:
            p = Path(match)
            if p.is_file():
                resolved.append(p)

    if not resolved:
        raise ValueError("No SQL files resolved. Use --files and/or --glob.")

    return resolved


def run() -> int:
    args = parse_args()

    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        print("ERROR: SUPABASE_ACCESS_TOKEN is not set.")
        return 1

    sql_files = resolve_files(args.files, args.globs)
    api_url = f"https://api.supabase.com/v1/projects/{args.project_ref}/database/query"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Applying {len(sql_files)} SQL file(s) to project {args.project_ref}...")

    with httpx.Client(timeout=args.timeout) as client:
        for file_path in sql_files:
            sql = file_path.read_text(encoding="utf-8")
            print(f"  -> {file_path} ({len(sql)} chars)", end=" ... ", flush=True)
            response = client.post(api_url, json={"query": sql}, headers=headers)
            if response.status_code not in (200, 201):
                print(f"FAIL [{response.status_code}]")
                print(response.text[:1000])
                return 1
            print("OK")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
