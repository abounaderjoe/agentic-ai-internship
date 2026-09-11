"""Main Supervisor Agent: routes each request to the right specialist tool.

Two compiled agents are exposed for two different callers:
  - `supervisor`: checkpointed to Postgres (capstone_state schema, see
    state_db.py), used by the standalone script/Streamlit app so a
    conversation survives both across turns AND across app restarts.
  - `supervisor_for_studio`: no custom checkpointer, used by langgraph.json/
    LangGraph Studio, which manages persistence itself (a custom
    checkpointer there raises, same issue as exercise3 -- see graph_builder
    there for the same pattern).
"""
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.postgres import PostgresSaver

from .config import make_llm
from .conversation import conversation_agent
from .db import sql_query_agent
from .rag import rag_agent
from .state_db import get_state_pool
from .visualization import visualization_agent
from .web_research import web_research_team

TOOLS = [sql_query_agent, web_research_team, visualization_agent, rag_agent, conversation_agent]

SYSTEM_PROMPT = (
    "You are the Main Supervisor of a multi-agent assistant. Route each "
    "request to exactly the right specialist tool:\n"
    "- sql_query_agent: questions about customers, products, orders, sales, "
    "or revenue in the sample database\n"
    "- web_research_team: questions needing live/external web research "
    "(news, general knowledge, comparisons, anything outside the internal "
    "docs or database)\n"
    "- visualization_agent: a request for a chart (bar/pie/line). If the "
    "chart needs database data you don't already have, call "
    "sql_query_agent FIRST to get it, then pass that data to "
    "visualization_agent.\n"
    "- rag_agent: questions specifically about Groq, LangChain/LCEL, or "
    "LangSmith, answered from the internal docs\n"
    "- conversation_agent: general chit-chat with no specific data need\n"
    "If a tool call fails or returns an error, explain the failure to the "
    "user plainly rather than guessing an answer, and consider retrying "
    "once with a rephrased query if that seems likely to help.\n"
    "After calling visualization_agent, the chart is already rendered "
    "separately by the UI -- do NOT add a markdown image link or any fake "
    "URL for it in your reply; just briefly describe what it shows."
)

_checkpointer = PostgresSaver(get_state_pool())
_checkpointer.setup()  # idempotent: creates the checkpoint tables if missing

supervisor = create_agent(
    make_llm(),
    TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)

supervisor_for_studio = create_agent(make_llm(), TOOLS, system_prompt=SYSTEM_PROMPT)


def ask(thread_id: str, message: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}, "tags": ["capstone", "supervisor"]}
    result = supervisor.invoke({"messages": [("human", message)]}, config=config)
    return {"thread_id": thread_id, "question": message, "messages": result["messages"]}


def load_history(thread_id: str) -> list[dict]:
    """Rebuilds a chat-UI-shaped history (list of {"role", ...} dicts) from
    a thread's Postgres checkpoint -- used to restore a chat after a
    restart, since only the chat list (chat_store.py) is otherwise cached."""
    from .visualization import CHART_SPEC_PREFIX  # local import: avoid a cycle at module load

    import json

    state = supervisor.get_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state.values else []

    history: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            if isinstance(msg.content, str) and msg.content.startswith(CHART_SPEC_PREFIX):
                spec = json.loads(msg.content[len(CHART_SPEC_PREFIX):])
                history.append({"role": "chart", "spec": spec})
        elif isinstance(msg, HumanMessage) and msg.content:
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            history.append({"role": "assistant", "content": msg.content})
    return history
