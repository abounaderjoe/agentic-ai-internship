"""Web Research Team: a LangGraph subgraph exposed to the Main Supervisor
as a single node. Internally, a sub-supervisor coordinates a Researcher
(live web search via DuckDuckGo) and a Report Writer (synthesizes findings
into a readable report).
"""
from typing import Literal

from ddgs import DDGS
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import TypedDict

from .config import make_llm
from .state import SupervisorState, current_task


class ResearchState(TypedDict):
    topic: str
    findings: str
    report: str
    next: str


def _web_search(query: str, max_results: int = 5) -> str:
    try:
        results = list(DDGS().text(query, max_results=max_results))
    except Exception as exc:  # noqa: BLE001 - surfaced to the writer, not fatal
        return f"SEARCH_ERROR: {exc}"
    if not results:
        return "SEARCH_ERROR: no results found."
    return "\n\n".join(f"{r['title']}\n{r['href']}\n{r['body']}" for r in results)


# --- Sub-supervisor: routes between researcher and writer -------------------
_route_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You coordinate a two-person research team: 'researcher' "
            "gathers raw web findings, 'writer' turns findings into a "
            "report. Reply with exactly one word: 'researcher' if there "
            "are no findings yet, 'writer' if there are findings but no "
            "report yet, or 'done' if the report is already complete.",
        ),
        ("human", "Findings present: {has_findings}\nReport present: {has_report}"),
    ]
)
_route_chain = _route_prompt | make_llm() | StrOutputParser()


def sub_supervisor(state: ResearchState) -> dict:
    has_findings = bool(state.get("findings"))
    has_report = bool(state.get("report"))
    if has_findings and not has_report and state["findings"].startswith("SEARCH_ERROR"):
        # Edge case: search failed -- skip straight to a report that says so,
        # instead of looping on a dead end. The `not has_report` check
        # matters: without it, every pass after the writer finished routed
        # back to the writer again, an infinite loop.
        return {"next": "writer"}
    decision = _route_chain.invoke(
        {"has_findings": has_findings, "has_report": has_report}
    ).strip().lower()
    if decision not in {"researcher", "writer", "done"}:
        decision = "writer" if has_findings else "researcher"  # safe fallback
    return {"next": decision}


def route(state: ResearchState) -> Literal["researcher", "writer", "__end__"]:
    return END if state["next"] == "done" else state["next"]


# --- Researcher ---------------------------------------------------------
def researcher_node(state: ResearchState) -> dict:
    return {"findings": _web_search(state["topic"])}


# --- Report writer -------------------------------------------------------
_writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Write a concise, well-organized report (3-5 short paragraphs) "
            "synthesizing the research findings below.\n"
            "Formatting rules -- follow these exactly:\n"
            "- Separate every paragraph with a blank line.\n"
            "- Do not use headings, and do not use bullet/numbered lists "
            "unless the content is genuinely a list of items.\n"
            "- Don't bold random phrases for emphasis -- plain prose only.\n"
            "- Cite sources as inline Markdown links, e.g. "
            "[Kitco](https://kitco.com/...) -- never bare brackets, "
            "raw URLs, or citation markers like 【...】.\n"
            "If the findings say SEARCH_ERROR, say plainly that the web "
            "search failed and why, instead of inventing information.",
        ),
        ("human", "Topic: {topic}\n\nFindings:\n{findings}"),
    ]
)
_writer_chain = _writer_prompt | make_llm() | StrOutputParser()


def writer_node(state: ResearchState) -> dict:
    report = _writer_chain.invoke(
        {"topic": state["topic"], "findings": state["findings"]}, config={"tags": ["final_answer"]}
    )
    return {"report": report}


_builder = StateGraph(ResearchState)
_builder.add_node("sub_supervisor", sub_supervisor)
_builder.add_node("researcher", researcher_node)
_builder.add_node("writer", writer_node)
_builder.add_edge(START, "sub_supervisor")
_builder.add_conditional_edges("sub_supervisor", route)
_builder.add_edge("researcher", "sub_supervisor")
_builder.add_edge("writer", "sub_supervisor")
web_research_graph = _builder.compile()


def web_research_team(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """Research a topic on the live web and produce a synthesized report.
    Use this for questions needing current or external information that
    isn't in the internal docs or the database (news, general knowledge,
    comparisons, etc.)."""
    topic = current_task(state)
    result = web_research_graph.invoke(
        {"topic": topic, "findings": "", "report": "", "next": ""},
        # A normal run takes 5 steps (sub_supervisor, researcher,
        # sub_supervisor, writer, sub_supervisor); the cap stops any future
        # routing loop before it can burn through the Groq token quota.
        config={"tags": ["capstone", "web-research-team"], "recursion_limit": 10},
    )
    reply = result.get("report") or result.get("findings") or "No report produced."
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="web_research_team")],
            "visited": ["web_research_team"],
        },
    )
