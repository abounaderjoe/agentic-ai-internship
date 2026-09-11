"""
Project 1 (Capstone) front-end: a Streamlit chat UI for the multi-agent
Supervisor system.

Run with:
    streamlit run capstone_app.py

Two UX details worth knowing:
  - Multiple chats: each chat in the sidebar has its own thread_id, so
    LangGraph's Postgres checkpointer keeps each one's memory independent --
    switching back to an older chat continues exactly where it left off, and
    the whole chat list + message history survives an app restart (backed by
    Supabase, see capstone/chat_store.py and capstone/supervisor.py).
  - Streaming: the user's own message renders immediately (before the agent
    is even called), and the assistant's final answer types out token by
    token via supervisor.stream(..., stream_mode="messages"), filtered to
    langgraph_node == "model" -- the SQL-generation and chart-spec LLM calls
    happen as separate nested calls tagged "tools", so filtering on "model"
    keeps the internal machinery out of the live typing effect.

Chart.js is bundled locally (capstone/static/chart.umd.min.js) and inlined
directly into the component's HTML rather than loaded via <script src=CDN>.
Streamlit's components.html() renders inside a sandboxed iframe with a null/
opaque origin, and Chromium's Opaque Response Blocking (ORB) rejects
cross-origin <script src> fetches from that context (net::ERR_BLOCKED_BY_ORB,
leaving `Chart` undefined) -- inlining sidesteps it entirely, no network
dependency at render time either.
"""
import json
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import AIMessageChunk, ToolMessage

from capstone.chat_store import create_chat, list_chats, update_chat_title
from capstone.supervisor import TOOLS, load_history, supervisor
from capstone.visualization import CHART_SPEC_PREFIX

st.set_page_config(page_title="Capstone Multi-Agent Assistant", page_icon="🤖")

CHART_JS_SOURCE = (Path(__file__).parent / "capstone" / "static" / "chart.umd.min.js").read_text(encoding="utf-8")
CHART_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#eab308", "#f43f5e"]
NEW_CHAT_TITLE = "New chat"


def new_chat() -> str:
    chat_id = str(uuid.uuid4())
    create_chat(chat_id, NEW_CHAT_TITLE)
    st.session_state.chats[chat_id] = {"title": NEW_CHAT_TITLE, "history": []}
    return chat_id


if "chats" not in st.session_state:
    # history=None means "not loaded yet" -- fetched lazily from the
    # Postgres checkpoint the first time a chat is actually viewed, so
    # opening the app with many saved chats doesn't pull all of them at once.
    st.session_state.chats = {row["id"]: {"title": row["title"], "history": None} for row in list_chats()}
    if st.session_state.chats:
        st.session_state.active_chat_id = list(st.session_state.chats.keys())[-1]  # most recently created
    else:
        st.session_state.active_chat_id = new_chat()


def render_chart(spec: dict, key: str) -> None:
    canvas_id = f"chart_{key}"
    title = spec.get("title", "")
    chart_html = f"""
    <script>{CHART_JS_SOURCE}</script>
    <canvas id="{canvas_id}" height="120"></canvas>
    <script>
      new Chart(document.getElementById('{canvas_id}'), {{
        type: {json.dumps(spec['type'])},
        data: {{
          labels: {json.dumps(spec['labels'])},
          datasets: [{{
            label: {json.dumps(title)},
            data: {json.dumps(spec['data'])},
            backgroundColor: {json.dumps(CHART_COLORS)},
          }}]
        }},
        options: {{
          responsive: true,
          plugins: {{ title: {{ display: true, text: {json.dumps(title)} }} }}
        }}
      }});
    </script>
    """
    components.html(chart_html, height=340)


with st.sidebar:
    if st.button("+ New chat", use_container_width=True):
        st.session_state.active_chat_id = new_chat()
        st.rerun()

    st.divider()
    st.caption("Chats")
    for chat_id in reversed(list(st.session_state.chats.keys())):
        title = st.session_state.chats[chat_id]["title"]
        prefix = "● " if chat_id == st.session_state.active_chat_id else ""
        if st.button(prefix + title, key=f"chatbtn_{chat_id}", use_container_width=True):
            st.session_state.active_chat_id = chat_id
            st.rerun()

    st.divider()
    st.subheader("Specialist agents")
    for t in TOOLS:
        st.markdown(f"**{t.name}**  \n{t.description}")

active_chat = st.session_state.chats[st.session_state.active_chat_id]
if active_chat["history"] is None:
    active_chat["history"] = load_history(st.session_state.active_chat_id)

st.title("Multi-Agent Assistant")
st.caption("A Supervisor routes each message to the right specialist agent. Each chat in the sidebar keeps its own memory.")

for i, item in enumerate(active_chat["history"]):
    if item["role"] == "chart":
        with st.chat_message("assistant"):
            render_chart(item["spec"], key=f"{st.session_state.active_chat_id}_{i}")
    else:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

question = st.chat_input("Ask about sales data, request a chart, research something, or just chat...")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    active_chat["history"].append({"role": "user", "content": question})
    if active_chat["title"] == NEW_CHAT_TITLE:
        active_chat["title"] = question[:40] + ("…" if len(question) > 40 else "")
        update_chat_title(st.session_state.active_chat_id, active_chat["title"])

    config = {
        "configurable": {"thread_id": st.session_state.active_chat_id},
        "tags": ["capstone", "supervisor"],
    }
    chart_specs = []
    full_text = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("▌")
        for msg, metadata in supervisor.stream(
            {"messages": [("human", question)]}, config=config, stream_mode="messages"
        ):
            if isinstance(msg, ToolMessage):
                if isinstance(msg.content, str) and msg.content.startswith(CHART_SPEC_PREFIX):
                    spec = json.loads(msg.content[len(CHART_SPEC_PREFIX):])
                    chart_specs.append(spec)
                    render_chart(spec, key=f"{st.session_state.active_chat_id}_live_{len(chart_specs)}")
                continue
            if metadata.get("langgraph_node") == "model" and isinstance(msg, AIMessageChunk) and msg.content:
                full_text += msg.content
                placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)

    for spec in chart_specs:
        active_chat["history"].append({"role": "chart", "spec": spec})
    active_chat["history"].append({"role": "assistant", "content": full_text})
    st.rerun()
