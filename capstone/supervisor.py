"""Main Supervisor: a LangGraph StateGraph that routes each request to the
right specialist node, using Command-based routing -- the supervisor node's
LLM decides the next specialist and returns Command(goto=...), each
specialist does its work and returns Command(goto="supervisor") to hand
control back, until the supervisor decides FINISH.

Two compiled graphs are exposed for two different callers:
  - `supervisor`: checkpointed to Postgres (capstone_state schema, see
    state_db.py), used by the standalone script/Streamlit app so a
    conversation survives both across turns AND across app restarts.
  - `supervisor_for_studio`: no custom checkpointer, used by langgraph.json/
    LangGraph Studio, which manages persistence itself (a custom
    checkpointer there raises, same issue as exercise3 -- see graph_builder
    there for the same pattern).
"""
from typing import Literal, NamedTuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import TypedDict

from .config import make_llm
from .conversation import conversation_agent
from .db import sql_query_agent
from .memory_store import add_memory, list_memories
from .rag import rag_agent
from .state import SupervisorState, current_task, specialists_tried_this_turn
from .state_db import get_state_pool
from .visualization import CHART_SPEC_PREFIX, visualization_agent
from .web_research import web_research_team


class SpecialistInfo(NamedTuple):
    name: str
    description: str


SPECIALISTS = [
    SpecialistInfo(
        "sql_query_agent",
        "questions about customers, products, orders, sales, or revenue in the sample database",
    ),
    SpecialistInfo(
        "web_research_team",
        "questions needing live/external web research (news, general knowledge, comparisons, "
        "anything outside the internal docs or database)",
    ),
    SpecialistInfo(
        "visualization_agent",
        "a request for a chart (bar/pie/line). It only draws whatever numbers it's given -- it "
        "cannot fetch data itself. If the numbers aren't already in the conversation, get them "
        "first (sql_query_agent for database data, web_research_team for external numbers), "
        "then route to visualization_agent.",
    ),
    SpecialistInfo(
        "rag_agent",
        "questions specifically about Groq, LangChain/LCEL, or LangSmith, answered from the internal docs",
    ),
    SpecialistInfo("conversation_agent", "general chit-chat with no specific data need"),
    SpecialistInfo(
        "remember_fact",
        "the user asks you to remember something, or states a lasting fact/preference about "
        "themselves -- it carries over into every future conversation, not just this one",
    ),
]

SYSTEM_PROMPT = (
    "You are the Main Supervisor of a multi-agent assistant. Given the "
    "conversation so far, decide which specialist should act next:\n"
    + "\n".join(f"- {s.name}: {s.description}" for s in SPECIALISTS)
    + "\nRules:\n"
    "1. If the most recent specialist message already answers the user's "
    "latest request, reply next=FINISH immediately -- never call a "
    "specialist again just to double-check, rephrase, or confirm an "
    "answer that's already there. That message IS the reply shown to "
    "the user, verbatim.\n"
    "2. Never call the SAME specialist twice in a row for the same "
    "request. If a specialist's message reports a failure, an error, a "
    "refusal, or that it doesn't know or found nothing relevant, do NOT "
    "retry it -- route to a different, better-suited specialist instead "
    "(e.g. web_research_team for general or current knowledge that "
    "turned out not to be in the internal docs), or FINISH and let that "
    "message explain the limitation to the user if no other specialist "
    "fits.\n"
    "3. A chart request needs real numbers to plot, and visualization_agent "
    "cannot fetch any itself -- if the needed numbers aren't already in "
    "the conversation, get them first: route to sql_query_agent for "
    "anything about customers/products/orders/sales, or to "
    "web_research_team for external numbers (e.g. prices, statistics, "
    "counts) that a web search could plausibly find as a handful of "
    "concrete figures. Only once that data is in the conversation, route "
    "to visualization_agent next. If the request needs a long, precise "
    "time series (e.g. a full month of daily prices) that a web search "
    "is very unlikely to return as clean data, still try web_research_team "
    "once -- but if its result doesn't contain real usable numbers, FINISH "
    "and let it explain the limitation rather than sending clearly "
    "insufficient data to visualization_agent.\n"
    "4. Always fill `instructions` with the precise question, request, "
    "or fact to hand to the chosen specialist, rephrased from the "
    "conversation if needed (ignored when next is FINISH).\n"
    "5. You must always answer by choosing a `next` value -- never write "
    "a plain-text reply yourself, even if you already know the answer "
    "(e.g. from a fact mentioned earlier in the conversation). If the "
    "request is trivially answerable from context already present, "
    "route to conversation_agent with `instructions` containing that "
    "answer for it to relay."
)

MAX_HOPS = 4  # loop guard: force FINISH after this many specialist hops in one turn


class Route(TypedDict):
    next: Literal[
        "sql_query_agent",
        "web_research_team",
        "visualization_agent",
        "rag_agent",
        "conversation_agent",
        "remember_fact",
        "FINISH",
    ]
    instructions: str


_router_llm = make_llm().with_structured_output(Route)


def supervisor_node(
    state: SupervisorState,
) -> Command[
    Literal[
        "sql_query_agent",
        "web_research_team",
        "visualization_agent",
        "rag_agent",
        "conversation_agent",
        "remember_fact",
        "__end__",
    ]
]:
    if state.get("hops", 0) >= MAX_HOPS:
        return Command(goto=END)
    tried = specialists_tried_this_turn(state)
    context = SYSTEM_PROMPT
    if tried:
        context += (
            "\n\nAlready tried for the user's current request, in order: "
            f"{tried}. Do not pick any of these again -- FINISH, or route "
            "to one that hasn't been tried yet."
        )
    try:
        route: Route = _router_llm.invoke([SystemMessage(content=context), *state["messages"]])
    except Exception:  # noqa: BLE001 - e.g. the model answered in plain text instead of
        # calling the routing schema (seen with trivially-answerable requests); fall back
        # to conversation_agent rather than crashing the whole turn.
        if "conversation_agent" in tried:
            return Command(goto=END)
        return Command(
            goto="conversation_agent",
            update={"task": current_task(state), "hops": state.get("hops", 0) + 1},
        )
    if route["next"] == "FINISH":
        if not tried:
            # The router tried to end the turn before any specialist ever
            # responded to the user's current message -- observed in
            # testing to happen occasionally, and it would otherwise leave
            # the user's own message as the last one in state, displayed
            # as if it were the reply. Force a real response instead.
            return Command(
                goto="conversation_agent",
                update={"task": current_task(state), "hops": state.get("hops", 0) + 1},
            )
        return Command(goto=END)
    if route["next"] in tried:
        # Hard stop on a repeat rather than trusting the model to always
        # obey the "don't repeat" instruction above -- observed in testing
        # to sometimes retry the same specialist until MAX_HOPS anyway.
        return Command(goto=END)
    return Command(
        goto=route["next"],
        update={"task": route.get("instructions", ""), "hops": state.get("hops", 0) + 1},
    )


def remember_fact_node(state: SupervisorState) -> Command[Literal["supervisor"]]:
    fact = current_task(state)
    add_memory(fact)
    reply = f"Got it, I'll remember that: {fact}"
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="remember_fact")],
            "visited": ["remember_fact"],
        },
    )


_builder = StateGraph(SupervisorState)
_builder.add_node("supervisor", supervisor_node)
_builder.add_node("sql_query_agent", sql_query_agent)
_builder.add_node("web_research_team", web_research_team)
_builder.add_node("visualization_agent", visualization_agent)
_builder.add_node("rag_agent", rag_agent)
_builder.add_node("conversation_agent", conversation_agent)
_builder.add_node("remember_fact", remember_fact_node)
_builder.add_edge(START, "supervisor")

_checkpointer = PostgresSaver(get_state_pool())
_checkpointer.setup()  # idempotent: creates the checkpoint tables if missing

supervisor = _builder.compile(checkpointer=_checkpointer)
supervisor_for_studio = _builder.compile()


def delete_memory(thread_id: str) -> None:
    """Deletes a thread's checkpoint data (its agent memory). Called
    alongside chat_store.delete_chat() so removing a chat also clears what
    the agent remembers about it, not just the sidebar entry."""
    _checkpointer.delete_thread(thread_id)


def build_input_messages(thread_id: str, message: str) -> list:
    """The human message, prefixed with known cross-chat memories -- but
    only on a thread's first turn, so they don't get re-injected (and
    re-checkpointed) on every single message in a long conversation."""
    state = supervisor.get_state({"configurable": {"thread_id": thread_id}})
    is_new_thread = not (state.values and state.values.get("messages"))
    messages = [("human", message)]
    if is_new_thread:
        memories = list_memories()
        if memories:
            memory_text = "\n".join(f"- {m}" for m in memories)
            messages.insert(0, ("system", f"Known facts about the user from past conversations:\n{memory_text}"))
    return messages


def ask(thread_id: str, message: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}, "tags": ["capstone", "supervisor"]}
    result = supervisor.invoke(
        {"messages": build_input_messages(thread_id, message), "hops": 0, "task": ""},
        config=config,
    )
    return {
        "thread_id": thread_id,
        "question": message,
        "messages": result["messages"],
        "visited": result.get("visited", []),
    }


def load_history(thread_id: str) -> list[dict]:
    """Rebuilds a chat-UI-shaped history (list of {"role", ...} dicts) from
    a thread's Postgres checkpoint -- used to restore a chat after a
    restart, since only the chat list (chat_store.py) is otherwise cached."""
    import json

    state = supervisor.get_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state.values else []

    history: list[dict] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.startswith(CHART_SPEC_PREFIX):
            spec = json.loads(msg.content[len(CHART_SPEC_PREFIX):])
            history.append({"role": "chart", "spec": spec})
        elif isinstance(msg, HumanMessage) and msg.content:
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            history.append({"role": "assistant", "content": msg.content})
    return history
