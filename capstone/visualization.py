"""Visualization Agent: turns structured data into a Chart.js chart spec.

Returns a "CHART_SPEC::<json>"-prefixed string rather than plain text, so
the Streamlit front-end can detect this tool's output among the agent's
messages and render it with Chart.js instead of printing it as text.
"""
import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from .config import make_llm

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

_REQUIRED_KEYS = {"type", "labels", "data"}
_VALID_TYPES = {"bar", "pie", "line"}


@tool
def visualization_agent(request: str, data: str) -> str:
    """Create an interactive bar, pie, or line chart from structured data
    (e.g. rows returned by sql_query_agent, or any labeled numeric data).
    Pass the charting request and the raw data as text. Returns a chart
    spec the UI renders with Chart.js."""
    try:
        spec = _chart_chain.invoke({"request": request, "data": data})
    except Exception as exc:  # noqa: BLE001 - report back to the agent, don't crash the run
        return f"Could not build a chart: {exc}"
    if not isinstance(spec, dict) or not _REQUIRED_KEYS.issubset(spec) or spec["type"] not in _VALID_TYPES:
        return f"Chart generation returned an unexpected format: {spec!r}"
    if len(spec["labels"]) != len(spec["data"]):
        return "Chart generation returned mismatched labels/data lengths."
    return CHART_SPEC_PREFIX + json.dumps(spec)
