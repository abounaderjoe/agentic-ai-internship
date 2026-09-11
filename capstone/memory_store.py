"""Cross-chat memory: facts that persist across ALL conversations, not just
one thread. Separate from chat_store.py (which only tracks chat titles) and
from LangGraph's checkpoints (which are per-thread). No user auth exists
yet, so this is global -- shared across every chat, not per-person.
"""
from .state_db import get_state_pool

with get_state_pool().connection() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def list_memories() -> list[str]:
    with get_state_pool().connection() as conn:
        rows = conn.execute("SELECT content FROM memories ORDER BY created_at").fetchall()
    return [r[0] for r in rows]


def add_memory(content: str) -> None:
    with get_state_pool().connection() as conn:
        conn.execute("INSERT INTO memories (content) VALUES (%s)", (content,))
