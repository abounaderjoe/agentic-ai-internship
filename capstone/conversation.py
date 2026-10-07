"""Conversation Node: general chit-chat with no specific data need.

Unlike the other specialists, this one is given the FULL conversation
history (state["messages"]) rather than just current_task()'s single
derived string -- chit-chat is exactly the case where naturally recalling
anything already said earlier in the thread (including the cross-chat
memories build_input_messages() injects as a system message on a new
thread's first turn) matters, and a single isolated string can't carry
that.
"""
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from .config import make_llm
from .state import SupervisorState

_chat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a friendly, helpful conversational assistant. Keep "
            "replies natural, warm, and concise. Use any facts already "
            "established earlier in the conversation below.",
        ),
        MessagesPlaceholder("history"),
    ]
)
_chat_chain = _chat_prompt | make_llm(temperature=0.7)


def conversation_agent(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """Handle general chit-chat, greetings, or open-ended conversation that
    isn't a specific request for data, research, or a chart."""
    reply = _chat_chain.invoke({"history": state["messages"]}, config={"tags": ["final_answer"]}).content
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="conversation_agent")],
            "visited": ["conversation_agent"],
        },
    )
