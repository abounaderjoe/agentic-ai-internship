"""
Exercise 4: Agent with Tools
Step 7 of the Agentic AI Onboarding Roadmap.

Covers all four goals of the exercise:
  1. An agent (LangGraph's prebuilt ReAct agent) that can use multiple tools.
  2. Three distinct tools: a calculator, a semantic search over the ./docs
     knowledge base, and a SQLite employee-directory lookup.
  3. Reasoning to pick the right tool: the ReAct loop lets the model read
     each question, decide which tool (if any) applies, call it, and use
     the result to answer -- visible per-question via `tools_used` below
     and as nested tool-call spans in LangSmith.
  4. A LangSmith evaluation dataset ('exercise4-agent-eval') with expected
     answers and expected tool choices, scored by two evaluators.
"""
import ast
import operator
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.agents import create_agent
from langsmith import Client
from langsmith.evaluation import evaluate

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
MODEL_NAME = "openai/gpt-oss-120b"


# --- Tool 1: calculator -----------------------------------------------------
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression (+, -, *, /, %, **, parentheses).
    Use this for any math question. Example input: "482 * 37 - 100"."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree.body))
    except Exception as exc:  # noqa: BLE001 - report back to the agent, don't crash the run
        return f"Could not evaluate '{expression}': {exc}"


# --- Tool 2: semantic search over the ./docs knowledge base ----------------
_loader = DirectoryLoader(str(DOCS_DIR), glob="*.md", loader_cls=TextLoader)
_documents = _loader.load()
_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
_chunks = _splitter.split_documents(_documents)
_vectorstore = InMemoryVectorStore.from_documents(_chunks, FastEmbedEmbeddings())
_retriever = _vectorstore.as_retriever(search_kwargs={"k": 3})


@tool
def search_docs(query: str) -> str:
    """Search the internship knowledge base (docs about Groq models, LCEL,
    and LangSmith tracing) for information relevant to the query. Use this
    for any question about Groq, LangChain/LCEL, or LangSmith."""
    docs = _retriever.invoke(query)
    if not docs:
        return "No relevant documents found."
    return "\n\n".join(
        f"[{Path(d.metadata.get('source', '?')).name}]\n{d.page_content}" for d in docs
    )


# --- Tool 3: employee database lookup (SQLite) ------------------------------
_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.execute("CREATE TABLE employees (name TEXT, role TEXT, department TEXT)")
_db.executemany(
    "INSERT INTO employees VALUES (?, ?, ?)",
    [
        ("Priya Nair", "Senior Engineer", "Engineering"),
        ("Marcus Webb", "Product Manager", "Product"),
        ("Sofia Alvarez", "Engineering Manager", "Engineering"),
        ("Daniel Kim", "Data Analyst", "Analytics"),
        ("Grace Osei", "Recruiter", "People Ops"),
    ],
)
_db.commit()


@tool
def lookup_employee(query: str) -> str:
    """Look up employees by name, role, or department in the company
    directory database. Use this for any question about who works at the
    company, their role, or their team. Example input: "Engineering" or
    "Priya Nair"."""
    like = f"%{query}%"
    rows = _db.execute(
        "SELECT name, role, department FROM employees "
        "WHERE name LIKE ? OR role LIKE ? OR department LIKE ?",
        (like, like, like),
    ).fetchall()
    if not rows:
        return f"No employees found matching '{query}'."
    return "\n".join(f"{name} - {role}, {department}" for name, role, department in rows)


# --- Agent: reasoning + tool selection via LangGraph's ReAct loop ----------
TOOLS = [calculator, search_docs, lookup_employee]
llm = ChatGroq(model=MODEL_NAME, temperature=0)
agent = create_agent(
    llm,
    TOOLS,
    system_prompt=(
        "You are a helpful assistant with access to a calculator, a search "
        "tool over internal docs, and an employee directory lookup. Read "
        "each question, decide which tool (if any) is relevant, call it, "
        "and use the result to answer concisely. If no tool applies, answer "
        "directly from your own knowledge."
    ),
)


def ask(question: str) -> dict:
    result = agent.invoke(
        {"messages": [("human", question)]},
        config={"run_name": "exercise4-agent-query", "tags": ["exercise4"]},
    )
    tools_used = [m.name for m in result["messages"] if isinstance(m, ToolMessage)]
    return {"question": question, "answer": result["messages"][-1].content, "tools_used": tools_used}


TEST_QUERIES = [
    "What is 482 * 37, minus 100?",
    "According to the internship docs, what does the LCEL pipe operator do?",
    "Which employees are in the Engineering department?",
    "What is Priya Nair's role at the company?",
    "What's the capital of France?",
]


# --- LangSmith evaluation dataset -------------------------------------------
DATASET_NAME = "exercise4-agent-eval"

EVAL_EXAMPLES = [
    {
        "inputs": {"question": "What is 156 * 23?"},
        "outputs": {"expected_tool": "calculator", "expected_answer_contains": "3588"},
    },
    {
        "inputs": {"question": "Does Groq offer an embeddings API?"},
        "outputs": {"expected_tool": "search_docs", "expected_answer_contains": "embed"},
    },
    {
        "inputs": {"question": "Who is the Engineering Manager?"},
        "outputs": {"expected_tool": "lookup_employee", "expected_answer_contains": "Sofia Alvarez"},
    },
    {
        "inputs": {"question": "What department is Daniel Kim in?"},
        "outputs": {"expected_tool": "lookup_employee", "expected_answer_contains": "Analytics"},
    },
    {
        "inputs": {"question": "What is the capital of Japan?"},
        "outputs": {"expected_tool": None, "expected_answer_contains": "Tokyo"},
    },
]


def build_dataset(client: Client) -> str:
    if not client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Exercise 4: does the tool-using agent pick the right "
            "tool and land on the right answer?",
        )
        client.create_examples(
            dataset_id=dataset.id,
            examples=[{"inputs": e["inputs"], "outputs": e["outputs"]} for e in EVAL_EXAMPLES],
        )
    return DATASET_NAME


def target(inputs: dict) -> dict:
    result = ask(inputs["question"])
    return {"answer": result["answer"], "tools_used": result["tools_used"]}


def contains_expected(run, example) -> dict:
    expected = (example.outputs or {}).get("expected_answer_contains", "")
    actual = (run.outputs or {}).get("answer", "")
    score = (expected.lower() in actual.lower()) if expected else True
    return {"key": "contains_expected", "score": float(score)}


def correct_tool_used(run, example) -> dict:
    expected_tool = (example.outputs or {}).get("expected_tool")
    tools_used = (run.outputs or {}).get("tools_used", [])
    score = (len(tools_used) == 0) if expected_tool is None else (expected_tool in tools_used)
    return {"key": "correct_tool_used", "score": float(score)}


def print_answer(result: dict) -> None:
    print(f"   tools used: {result['tools_used'] or 'none'}")
    print(f"A: {result['answer']}\n")


def run_chat() -> None:
    print("Chat mode - type a question, or 'quit' to exit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in {"quit", "exit"}:
            break
        print_answer(ask(question))


def run_demo() -> None:
    print(f"Tools available: {[t.name for t in TOOLS]}\n")

    for query in TEST_QUERIES:
        result = ask(query)
        print(f"Q: {result['question']}")
        print_answer(result)

    print("Building/using LangSmith dataset and running evaluation...\n")
    client = Client()
    dataset_name = build_dataset(client)
    evaluate(
        target,
        data=dataset_name,
        evaluators=[contains_expected, correct_tool_used],
        experiment_prefix="exercise4-agent",
        client=client,
    )

    print(
        f"\nOpen https://smith.langchain.com -> Datasets & Testing -> "
        f"'{dataset_name}' to see the evaluation experiment, per-example "
        "scores, and which tool the agent chose for each question. "
        "Individual query traces are also under the 'agentic-ai-internship' "
        "project, tagged 'exercise4'."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1] == "--chat":
        run_chat()
    elif len(sys.argv) > 1:
        print_answer(ask(" ".join(sys.argv[1:])))
    else:
        run_demo()
