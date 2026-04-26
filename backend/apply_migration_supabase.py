"""Apply all curriculum migration SQL to Supabase via REST API.

Usage: python apply_migration_supabase.py
"""
import os
import sys
import glob
import httpx
from pathlib import Path

# Supabase project credentials
PROJECT_REF = "zilkfhkwxyroobastsqj"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"

# Get the service role key from environment or .env
def get_service_key():
    # Try env var first
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if key:
        return key
    # Try .env file
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    # Try backend .env
    env_path = Path(__file__).resolve().parent / "app" / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent / ".env"
    return None


def execute_sql(sql: str, key: str) -> dict:
    """Execute SQL via Supabase Management API."""
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(url, json={"query": sql}, headers=headers, timeout=60)
    if resp.status_code != 200 and resp.status_code != 201:
        print(f"  ERROR {resp.status_code}: {resp.text[:500]}")
        return {"error": resp.text}
    return resp.json()


def main():
    # We'll use Supabase access token from env
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        print("ERROR: Set SUPABASE_ACCESS_TOKEN environment variable")
        print("Get it from: https://supabase.com/dashboard/account/tokens")
        sys.exit(1)

    chunks_dir = Path(__file__).resolve().parent / "migration_chunks"

    # Order of execution
    files = []
    # 1. AE batches
    files.extend(sorted(glob.glob(str(chunks_dir / "ae_batches" / "ae_batch_*.sql"))))
    # 2. Contents
    files.append(str(chunks_dir / "02_contents.sql"))
    # 3. Skills
    files.extend(sorted(glob.glob(str(chunks_dir / "03_skills_*.sql"))))
    # 4. Links
    files.extend(sorted(glob.glob(str(chunks_dir / "04_links_*.sql"))))
    # 5. Sequences
    files.append(str(chunks_dir / "05_sequences.sql"))

    print(f"Applying {len(files)} SQL files to Supabase...")
    for fpath in files:
        fname = Path(fpath).name
        sql = Path(fpath).read_text(encoding="utf-8")
        print(f"  Applying {fname} ({len(sql)} chars)...", end=" ", flush=True)

        url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(url, json={"query": sql}, headers=headers, timeout=120)
        if resp.status_code in (200, 201):
            print("OK")
        else:
            print(f"FAILED ({resp.status_code})")
            print(f"    {resp.text[:300]}")
            sys.exit(1)

    print("\nAll migrations applied successfully!")


if __name__ == "__main__":
    main()
