"""Visualization Node: turns structured data into a Chart.js chart spec.

Returns a "CHART_SPEC::<json>"-prefixed message rather than plain text, so
the front ends can detect it among the streamed messages and render it with
Chart.js instead of printing it as text. A second, short natural-language
message follows describing the chart -- the "final answer" the user sees
typed out live.
"""
import json
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from .config import make_llm
from .state import SupervisorState, current_task

CHART_SPEC_PREFIX = "CHART_SPEC::"

_chart_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Convert the data below into a Chart.js chart configuration as "
            "JSON with exactly these top-level keys: \"type\" (one of "
            "\"bar\", \"pie\", \"line\"), \"title\" (a short string), "
            "\"labels\" (array of strings), and \"data\" (array of numbers, "
            "same length as labels). Pick whichever chart type best fits "
            "the data and the request. Reply with ONLY the JSON object -- "
            "no markdown fences, no explanation.",
        ),
        ("human", "Request: {request}\n\nData:\n{data}"),
    ]
)
_chart_chain = _chart_prompt | make_llm() | JsonOutputParser()

_describe_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "In one short, friendly sentence, tell the user their chart is "
            "ready and briefly describe what it shows. The chart is "
            "already rendered separately by the UI -- do NOT add a "
            "markdown image link or any fake URL for it.",
        ),
        ("human", "Chart request: {request}\n\nChart spec: {spec}"),
    ]
)
_describe_chain = _describe_prompt | make_llm() | StrOutputParser()

_REQUIRED_KEYS = {"type", "labels", "data"}
_VALID_TYPES = {"bar", "pie", "line"}


def _extract_data(state: SupervisorState) -> str:
    """The most recent AIMessage (e.g. sql_query_agent's results) if there
    is one, else the raw request text itself."""
    messages = state["messages"]
    if messages and isinstance(messages[-1], AIMessage):
        return messages[-1].content
    return current_task(state)


def _done(*messages: AIMessage) -> Command[Literal["supervisor"]]:
    return Command(
        goto="supervisor",
        update={"messages": list(messages), "visited": ["visualization_agent"]},
    )


def visualization_agent(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """Create an interactive bar, pie, or line chart from structured data
    (e.g. rows returned by sql_query_agent, or any labeled numeric data)."""
    request = current_task(state)
    data = _extract_data(state)
    try:
        spec = _chart_chain.invoke({"request": request, "data": data})
    except Exception as exc:  # noqa: BLE001 - report back to the supervisor, don't crash the run
        return _done(AIMessage(content=f"Could not build a chart: {exc}", name="visualization_agent"))
    if not isinstance(spec, dict) or not _REQUIRED_KEYS.issubset(spec) or spec["type"] not in _VALID_TYPES:
        return _done(
            AIMessage(
                content=f"Chart generation returned an unexpected format: {spec!r}",
                name="visualization_agent",
            )
        )
    if len(spec["labels"]) != len(spec["data"]):
        return _done(
            AIMessage(
                content="Chart generation returned mismatched labels/data lengths.",
                name="visualization_agent",
            )
        )

    description = _describe_chain.invoke(
        {"request": request, "spec": json.dumps(spec)}, config={"tags": ["final_answer"]}
    )
    return _done(
        AIMessage(content=CHART_SPEC_PREFIX + json.dumps(spec), name="visualization_agent"),
        AIMessage(content=description, name="visualization_agent"),
    )
