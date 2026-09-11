"""Conversation Agent: general chit-chat with no specific data need.

Conversation memory across turns is handled at the Main Supervisor level
(see supervisor.py's MemorySaver + thread_id), not here -- this tool only
needs the single message it's given plus whatever context the Supervisor's
own message history already carries into that context.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from .config import make_llm

_chat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a friendly, helpful conversational assistant. Keep "
            "replies natural, warm, and concise.",
        ),
        ("human", "{message}"),
    ]
)
_chat_chain = _chat_prompt | make_llm(temperature=0.7)


@tool
def conversation_agent(message: str) -> str:
    """Handle general chit-chat, greetings, or open-ended conversation that
    isn't a specific request for data, research, or a chart. Use this as
    the default for casual questions with no clear specialist fit."""
    return _chat_chain.invoke({"message": message}).content
