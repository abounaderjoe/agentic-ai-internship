"""
Project 1 (Capstone) backend API -- wraps the same capstone.supervisor
agent used by capstone_app.py (Streamlit) and capstone_demo.py (CLI) behind
an HTTP API, so a separately-hosted frontend (e.g. a Next.js app on Vercel)
can talk to it. Meant to run on a host that supports long-lived Python
processes (Render, Railway, Fly.io, ...) -- NOT Vercel itself, which only
runs short-lived serverless functions and can't host this.

Run locally with:
    .venv\\Scripts\\python.exe -m uvicorn capstone_api:app --reload --port 8000

Endpoints:
    GET  /chats                    -> [{id, title}]
    POST /chats                    -> {id, title} (new empty chat)
    GET  /chats/{chat_id}/messages -> [{role, content} | {role: "chart", spec}]
    POST /chats/{chat_id}/messages -> Server-Sent Events stream of the
                                       assistant's reply to {"message": "..."}
                                       (see StreamEvent below for event shapes)
"""
import json
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessageChunk, ToolMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from capstone.chat_store import create_chat, delete_chat, list_chats, update_chat_title
from capstone.supervisor import build_input_messages, delete_memory, load_history, supervisor
from capstone.visualization import CHART_SPEC_PREFIX

load_dotenv()

app = FastAPI(title="Capstone Multi-Agent API")

# ALLOWED_ORIGINS: comma-separated list, e.g. "https://your-app.vercel.app".
# Defaults to "*" for local development only -- set this explicitly once
# deployed, so only your actual frontend can call the API.
_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

NEW_CHAT_TITLE = "New chat"


class SendMessageBody(BaseModel):
    message: str


@app.get("/chats")
def get_chats() -> list[dict]:
    return list_chats()


@app.post("/chats")
def post_chat() -> dict:
    chat_id = str(uuid.uuid4())
    create_chat(chat_id, NEW_CHAT_TITLE)
    return {"id": chat_id, "title": NEW_CHAT_TITLE}


@app.delete("/chats/{chat_id}")
def delete_chat_endpoint(chat_id: str) -> dict:
    delete_chat(chat_id)
    delete_memory(chat_id)
    return {"deleted": chat_id}


@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str) -> list[dict]:
    return load_history(chat_id)


@app.post("/chats/{chat_id}/messages")
def post_message(chat_id: str, body: SendMessageBody):
    async def event_stream():
        config = {
            "configurable": {"thread_id": chat_id},
            "tags": ["capstone", "supervisor", "api"],
        }

        # Mirror capstone_app.py: title the chat from its first message.
        chats = {c["id"]: c["title"] for c in list_chats()}
        if chats.get(chat_id) == NEW_CHAT_TITLE:
            title = body.message[:40] + ("…" if len(body.message) > 40 else "")
            update_chat_title(chat_id, title)
            yield {"event": "title", "data": json.dumps({"title": title})}

        for msg, metadata in supervisor.stream(
            {"messages": build_input_messages(chat_id, body.message)}, config=config, stream_mode="messages"
        ):
            if isinstance(msg, ToolMessage):
                if isinstance(msg.content, str) and msg.content.startswith(CHART_SPEC_PREFIX):
                    spec = json.loads(msg.content[len(CHART_SPEC_PREFIX):])
                    yield {"event": "chart", "data": json.dumps(spec)}
                continue
            if metadata.get("langgraph_node") == "model" and isinstance(msg, AIMessageChunk) and msg.content:
                yield {"event": "token", "data": json.dumps({"text": msg.content})}

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_stream())
