"""Connection pool for persistent app state (chat list + LangGraph
checkpoints), stored in the capstone_state schema under the capstone_app
role -- see seed_state.py. Isolated from both the admin role and the
read-only capstone_reader role used by sql_query_agent.

A pool, not a single shared connection: Streamlit runs each browser session
in its own thread, and a single psycopg.Connection is not safe for
concurrent use across threads. Sharing one raw connection here caused a real
bug during testing -- two overlapping script reruns racing on it corrupted a
thread's LangGraph checkpoint chain (the earlier turn's messages silently
vanished from the state). A pool hands each caller its own connection.
"""
import os

import psycopg
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_STATE_URL = os.environ.get("DATABASE_STATE_URL")

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    # Supabase's pooler doesn't forward a ?options=-c search_path=...
    # startup parameter, so it's set explicitly on every new connection.
    conn.execute("SET search_path TO capstone_state, public")


def get_state_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_STATE_URL:
            raise RuntimeError("Set DATABASE_STATE_URL in .env (see capstone/seed_state.py).")
        _pool = ConnectionPool(
            DATABASE_STATE_URL,
            kwargs={"autocommit": True},
            configure=_configure,
            min_size=1,
            max_size=5,
        )
    return _pool
