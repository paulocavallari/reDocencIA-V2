import os
import sys
import glob
import httpx
from pathlib import Path

# Supabase project credentials
PROJECT_REF = "zilkfhkwxyroobastsqj"
SUPABASE_URL = "https://zilkfhkwxyroobastsqj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppbGtmaGt3eHlyb29iYXN0c3FqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxMjI5NjIsImV4cCI6MjA5MTY5ODk2Mn0.7T5ft0N-HaH8jbTmN3GSs8oCCcLmRgGdHB-2d0kgH3M"

def main():
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

    print(f"Applying {len(files)} SQL files to Supabase via PostgREST...")
    
    # We use the anon key since we're hitting the REST endpoint. 
    # Usually you'd need the service_role key for schema changes, 
    # but let's try with what we have.
    
    for fpath in files:
        fname = Path(fpath).name
        sql = Path(fpath).read_text(encoding="utf-8")
        print(f"  Applying {fname} ({len(sql)} chars)...", end=" ", flush=True)

        # Note: This requires a custom function 'execute_sql' to be present in Supabase.
        # Since I don't know if it exists, this might fail.
        # Alternative: Use mcp_supabase_execute_sql directly in a loop.
        
        print("SKIPPED (Use MCP tool instead)")

if __name__ == "__main__":
    main()
