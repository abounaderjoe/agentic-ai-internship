"""
Project 1 (Capstone): Multi-Agent System with a Supervisor.

A hierarchical assistant: a Main Supervisor routes each request to one of
five specialists -- sql_query_agent (Postgres), web_research_team (a
Researcher + Report Writer subgraph coordinated by its own sub-supervisor,
searching live via DuckDuckGo), visualization_agent (Chart.js chart specs),
rag_agent (the internship docs), and conversation_agent (chit-chat).

Usage:
    python capstone_demo.py            # fixed test suite + metrics summary
    python capstone_demo.py "question" # ask one question, once
    python capstone_demo.py --chat     # interactive back-and-forth (memory
                                        # persists across turns in this mode)

sql_query_agent needs Postgres running: `docker compose up -d` (see
docker-compose.yml) before those queries will succeed.
"""
import sys
import time

from capstone.supervisor import SPECIALISTS, ask

FAILURE_MARKERS = ("failed", "could not", "refused", "no relevant", "search_error", "no results")

TEST_QUERIES = [
    "Hi there, how's it going?",  # conversation_agent
    "What does the LCEL pipe operator do?",  # rag_agent
    "How many orders were completed, and what's the total revenue from them?",  # sql_query_agent
    "Show me a bar chart of how many orders each status (completed/cancelled/refunded) has",  # sql -> viz
    "What is the Groq LPU chip and how is it different from a GPU?",  # web_research_team
]


def print_result(result: dict, elapsed: float) -> bool:
    """Prints the result; returns True if the answer looks like a failure/fallback."""
    answer = result["messages"][-1].content
    tools_used = result.get("visited", [])
    print(f"   tools used: {tools_used or 'none'}  ({elapsed:.2f}s)")
    print(f"A: {answer}\n")
    return any(marker in answer.lower() for marker in FAILURE_MARKERS)


def run_chat() -> None:
    print("Chat mode - type a question, or 'quit' to exit. Memory persists this session.\n")
    thread_id = "capstone-chat"
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in {"quit", "exit"}:
            break
        start = time.perf_counter()
        result = ask(thread_id, question)
        print_result(result, time.perf_counter() - start)


def run_demo() -> None:
    print(f"Specialists available: {[t.name for t in SPECIALISTS]}\n")

    fallback_count = 0
    total_time = 0.0
    for i, query in enumerate(TEST_QUERIES):
        print(f"Q: {query}")
        start = time.perf_counter()
        result = ask(f"capstone-demo-{i}", query)
        elapsed = time.perf_counter() - start
        total_time += elapsed
        if print_result(result, elapsed):
            fallback_count += 1

    completed = len(TEST_QUERIES) - fallback_count
    print("--- Metrics ---")
    print(f"Completion rate: {completed}/{len(TEST_QUERIES)} ({completed / len(TEST_QUERIES):.0%})")
    print(f"Fallback/error responses: {fallback_count}/{len(TEST_QUERIES)}")
    print(f"Avg response time: {total_time / len(TEST_QUERIES):.2f}s")
    print(
        "\nOpen https://smith.langchain.com and check the "
        "'agentic-ai-internship' project (tag 'capstone') to see each "
        "request's full trace: which specialist tool was chosen, the "
        "Web Research Team's internal sub-supervisor/researcher/writer "
        "spans, and the SQL/chart-spec tool outputs."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1] == "--chat":
        run_chat()
    elif len(sys.argv) > 1:
        print_result(ask("capstone-cli", " ".join(sys.argv[1:])), 0.0)
    else:
        run_demo()
