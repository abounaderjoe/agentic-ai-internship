"""One-off script: seeds Postgres (Supabase or local Docker) with the sample
sales schema/data and the read-only capstone_reader role from seed.sql.

Run with:
    .venv\\Scripts\\python.exe -m capstone.seed_db

Needs SUPABASE_ADMIN_URL (the admin/superuser connection string -- NOT the
capstone_reader one the app uses) set in .env.
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

ADMIN_URL = os.environ.get("SUPABASE_ADMIN_URL") or os.environ.get("DATABASE_ADMIN_URL")
SEED_SQL_PATH = Path(__file__).parent / "seed.sql"


def main() -> None:
    if not ADMIN_URL:
        print("Set SUPABASE_ADMIN_URL (the admin connection string) in .env first.")
        sys.exit(1)

    sql = SEED_SQL_PATH.read_text(encoding="utf-8")
    conn = psycopg2.connect(ADMIN_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)  # one multi-statement script; psycopg2 sends it as-is
        print("Seed complete: schema, sample data, and capstone_reader role are ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
