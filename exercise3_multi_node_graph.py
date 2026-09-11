"""
Exercise 3: Multi-Node LangGraph
Step 6 of the Agentic AI Onboarding Roadmap.

Covers all five goals of the exercise:
  1. A graph with 3+ specialized nodes (classify, technical, chitchat, complaint).
  2. Conditional branching: the classifier routes to exactly one responder node.
  3. Memory: a MemorySaver checkpointer keeps per-thread conversation history,
     so a second message on the same thread_id sees the first one.
  4. Tested with different inputs across all three branches, plus a two-turn
     conversation on one thread to exercise memory.
  5. LangSmith tracing: each node shows up as a nested span inside the graph
     run (tagged 'exercise3'), so the branching is visible in the trace tree.
"""
import sys
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"
CLASSIFIER_MODEL_NAME = "openai/gpt-oss-20b"  # smaller/faster, classification is a cheap task


# --- State ----------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str


# --- Node 1: classifier -----------------------------------------------------
classify_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classify the user's latest message into exactly one category:\n"
            "- technical: a question about Groq, LangChain, or LangSmith\n"
            "- chitchat: small talk, greetings, casual conversation\n"
            "- complaint: frustration, a problem report, or a negative experience\n"
            "Reply with only the single category word, nothing else.",
        ),
        ("human", "{message}"),
    ]
)
classifier_llm = ChatGroq(model=CLASSIFIER_MODEL_NAME, temperature=0)
classify_chain = classify_prompt | classifier_llm | StrOutputParser()

VALID_INTENTS = {"technical", "chitchat", "complaint"}


def classify(state: State) -> dict:
    if not state["messages"]:
        # Reachable from Studio/API callers that invoke with no messages yet;
        # the script's own ask() always populates one, so this never fires there.
        return {"intent": "chitchat"}
    last_message = state["messages"][-1].content
    raw = classify_chain.invoke(
        {"message": last_message},
        config={"run_name": "classify-intent", "tags": ["exercise3", "classify"]},
    )
    intent = raw.strip().lower()
    if intent not in VALID_INTENTS:
        intent = "chitchat"  # safe fallback if the model replies with something unexpected
    return {"intent": intent}


def route_after_classify(state: State) -> Literal["technical", "chitchat", "complaint"]:
    return state["intent"]


# --- Node 2: technical responder --------------------------------------------
technical_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a technical support assistant for engineers using Groq, "
            "LangChain, and LangSmith. Answer precisely and concisely, in 2-3 "
            "sentences.",
        ),
        MessagesPlaceholder("messages"),
    ]
)
llm = ChatGroq(model=MODEL_NAME)
technical_chain = technical_prompt | llm


def technical_node(state: State) -> dict:
    response = technical_chain.invoke(
        {"messages": state["messages"]},
        config={"run_name": "technical-response", "tags": ["exercise3", "technical"]},
    )
    return {"messages": [response]}


# --- Node 3: chitchat responder ---------------------------------------------
chitchat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a friendly, casual assistant making small talk. Keep "
            "replies short and warm.",
        ),
        MessagesPlaceholder("messages"),
    ]
)
chitchat_chain = chitchat_prompt | llm


def chitchat_node(state: State) -> dict:
    response = chitchat_chain.invoke(
        {"messages": state["messages"]},
        config={"run_name": "chitchat-response", "tags": ["exercise3", "chitchat"]},
    )
    return {"messages": [response]}


# --- Node 4: complaint responder --------------------------------------------
complaint_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a support agent handling an unhappy user. Acknowledge "
            "their frustration empathetically, and tell them you're escalating "
            "this to a human specialist who will follow up. Keep it brief.",
        ),
        MessagesPlaceholder("messages"),
    ]
)
complaint_chain = complaint_prompt | llm


def complaint_node(state: State) -> dict:
    response = complaint_chain.invoke(
        {"messages": state["messages"]},
        config={"run_name": "complaint-response", "tags": ["exercise3", "complaint"]},
    )
    return {"messages": [response]}


# --- Graph assembly ----------------------------------------------------------
graph_builder = StateGraph(State)
graph_builder.add_node("classify", classify)
graph_builder.add_node("technical", technical_node)
graph_builder.add_node("chitchat", chitchat_node)
graph_builder.add_node("complaint", complaint_node)

graph_builder.add_edge(START, "classify")
graph_builder.add_conditional_edges("classify", route_after_classify)
graph_builder.add_edge("technical", END)
graph_builder.add_edge("chitchat", END)
graph_builder.add_edge("complaint", END)

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)


def ask(thread_id: str, text: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}, "tags": ["exercise3"]}
    result = graph.invoke({"messages": [("human", text)]}, config=config)
    return {
        "thread_id": thread_id,
        "question": text,
        "intent": result["intent"],
        "answer": result["messages"][-1].content,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, which
    # can't print characters like non-breaking hyphens that Groq models sometimes output.

    print("Graph structure (Mermaid):")
    print(graph.get_graph().draw_mermaid())

    graph_png_path = Path(__file__).parent / "graph_structure.png"
    graph_png_path.write_bytes(graph.get_graph().draw_mermaid_png())
    print(f"Saved a rendered image of the graph structure to {graph_png_path.name}\n")

    # One branch per intent, each on its own thread (no shared memory needed).
    single_turn_tests = [
        ("thread-technical", "What does the pipe operator do in LCEL?"),
        ("thread-chitchat", "Hey, how's it going?"),
        ("thread-complaint", "This is the third time my request has failed, I'm fed up."),
    ]
    for thread_id, question in single_turn_tests:
        result = ask(thread_id, question)
        print(f"[{result['thread_id']}] intent={result['intent']}")
        print(f"Q: {result['question']}")
        print(f"A: {result['answer']}\n")

    # Two-turn conversation on ONE thread, to demonstrate memory: the second
    # message relies on context from the first.
    memory_thread = "thread-memory-demo"
    first = ask(memory_thread, "Which Groq model is the largest and best quality?")
    print(f"[{memory_thread}] turn 1 intent={first['intent']}")
    print(f"Q: {first['question']}")
    print(f"A: {first['answer']}\n")

    second = ask(memory_thread, "And which one did I just ask you about?")
    print(f"[{memory_thread}] turn 2 intent={second['intent']}")
    print(f"Q: {second['question']}")
    print(f"A: {second['answer']}\n")

    print(
        "Open https://smith.langchain.com and check the "
        "'agentic-ai-internship' project (tag 'exercise3') — each run's "
        "trace tree shows 'classify' branching into exactly one of "
        "'technical' / 'chitchat' / 'complaint', and the memory-demo thread's "
        "second run includes the first turn's messages in its input."
    )
