import os
import sys
import glob
import httpx
from pathlib import Path

# Supabase project credentials
PROJECT_REF = "zilkfhkwxyroobastsqj"

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
    # 1. Cleanup and Core AEs
    files.append(str(chunks_dir / "01_cleanup_aes.sql"))
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
        # Increased timeout for large batches
        try:
            resp = httpx.post(url, json={"query": sql}, headers=headers, timeout=300)
            if resp.status_code in (200, 201):
                print("OK")
            else:
                print(f"FAILED ({resp.status_code})")
                print(f"    {resp.text[:500]}")
                sys.exit(1)
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
            sys.exit(1)

    print("\nAll migrations applied successfully!")

if __name__ == "__main__":
    main()
