"""Persists the chat list (id, title) shown in the sidebar. The actual
message history for each chat isn't duplicated here -- it lives in
LangGraph's Postgres checkpoints (see supervisor.py), keyed by the same id
used as thread_id. This table only remembers which chats exist and what to
label them.
"""
from .state_db import get_state_pool


def list_chats() -> list[dict]:
    with get_state_pool().connection() as conn:
        rows = conn.execute("SELECT id, title FROM chats ORDER BY created_at").fetchall()
    return [{"id": str(row[0]), "title": row[1]} for row in rows]


def create_chat(chat_id: str, title: str) -> None:
    with get_state_pool().connection() as conn:
        conn.execute("INSERT INTO chats (id, title) VALUES (%s, %s)", (chat_id, title))


def update_chat_title(chat_id: str, title: str) -> None:
    with get_state_pool().connection() as conn:
        conn.execute("UPDATE chats SET title = %s WHERE id = %s", (title, chat_id))
