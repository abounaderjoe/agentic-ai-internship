"""One-off script: creates the capstone_app DB role + capstone_state schema
used for persistent chat state (LangGraph checkpoints + the UI's chat list).

Deliberately separate from capstone_reader (read-only, business tables in
public) and from the admin role used only for seeding -- capstone_app owns
its own schema and has zero grants on public, so even a bug in the app code
structurally cannot touch customers/products/orders/order_items.

Run with:
    .venv\\Scripts\\python.exe -m capstone.seed_state
Needs SUPABASE_ADMIN_URL in .env. Prints the DATABASE_STATE_URL to add to
.env (idempotent: re-running reuses the existing password instead of
generating a new one, unless the role doesn't exist yet).
"""
import os
import secrets
import string
import sys
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv

load_dotenv()

ADMIN_URL = os.environ.get("SUPABASE_ADMIN_URL") or os.environ.get("DATABASE_ADMIN_URL")
ROLE = "capstone_app"
SCHEMA = "capstone_state"


def _make_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(28))


def main() -> None:
    if not ADMIN_URL:
        print("Set SUPABASE_ADMIN_URL in .env first.")
        sys.exit(1)

    conn = psycopg2.connect(ADMIN_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = %s", (ROLE,))
            role_exists = cur.fetchone() is not None
            password = _make_password()
            if not role_exists:
                cur.execute(f"CREATE ROLE {ROLE} WITH LOGIN PASSWORD %s", (password,))
                print(f"Created role {ROLE!r} with a new password.")
            else:
                cur.execute(f"ALTER ROLE {ROLE} WITH LOGIN PASSWORD %s", (password,))
                print(f"Role {ROLE!r} already existed -- reset its password.")
            cur.execute("GRANT CONNECT ON DATABASE postgres TO " + ROLE)
            # Schema stays owned by the admin role (Supabase's "postgres" role
            # can't SET ROLE to authorize a schema for capstone_app directly)
            # -- USAGE + CREATE is enough; anything capstone_app creates in it
            # is owned by capstone_app, so it has full control either way.
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            cur.execute(f"GRANT USAGE, CREATE ON SCHEMA {SCHEMA} TO {ROLE}")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA}.chats (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {SCHEMA} TO {ROLE}")
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT ALL ON TABLES TO {ROLE}")
    finally:
        conn.close()

    parsed = urlparse(ADMIN_URL)
    host_port = parsed.netloc.split("@")[-1]
    dbname = parsed.path.lstrip("/")
    # Supabase's pooler (Supavisor) routes by username, requiring
    # "<role>.<project-ref>" for any role, not just "postgres" -- reuse
    # whatever suffix the admin URL's own username has (empty if this is a
    # direct, non-pooled connection).
    admin_user = parsed.username or ""
    suffix = admin_user.split(".", 1)[1] if "." in admin_user else ""
    pooled_user = f"{ROLE}.{suffix}" if suffix else ROLE
    # No ?options=-c search_path=... here: Supabase's pooler (Supavisor)
    # doesn't forward that startup parameter. capstone/state_db.py sets the
    # search_path with a plain SQL command after connecting instead.
    state_url = f"postgresql://{pooled_user}:{password}@{host_port}/{dbname}"
    print("\nAdd this to .env as DATABASE_STATE_URL:")
    print(state_url)


if __name__ == "__main__":
    main()
