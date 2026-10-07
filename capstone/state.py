"""Shared graph state for the Main Supervisor and every specialist node.

Lives outside supervisor.py so specialist modules (db.py, rag.py, ...) can
import it without a circular import with supervisor.py.
"""
import operator
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import MessagesState


class SupervisorState(MessagesState):
    task: str  # instructions the supervisor routed to the active specialist
    hops: int  # loop guard within a single turn, reset to 0 each new call
    visited: Annotated[list[str], operator.add]  # specialist names run, for observability


def current_task(state: SupervisorState) -> str:
    """The instructions the supervisor gave the active specialist, or (if
    none were set) the content of the most recent human message."""
    if state.get("task"):
        return state["task"]
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def specialists_tried_this_turn(state: SupervisorState) -> list[str]:
    """Names of specialists that already responded to the CURRENT (most
    recent) human request -- i.e. every named AIMessage since the last
    HumanMessage. Derived from messages rather than the cumulative
    `visited` list, which persists across turns in the checkpoint and so
    can't tell "already tried this turn" from "tried three turns ago"."""
    tried: list[str] = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage) and msg.name and msg.name not in tried:
            tried.append(msg.name)
    return tried
