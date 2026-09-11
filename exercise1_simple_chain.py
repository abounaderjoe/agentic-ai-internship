"""
Exercise 1: Simple Chain with ChatGroq
Step 4 of the Agentic AI Onboarding Roadmap.

Covers all four goals of the exercise:
  1. A basic chain that calls ChatGroq.
  2. A reusable prompt TEMPLATE (variables, not hardcoded text).
  3. A latency/quality comparison across a few different Groq models.
  4. LangSmith tracing of every call (each run gets a name/tag so the
     three models are easy to tell apart in the LangSmith UI).

Fill this in once your .env has a real GROQ_API_KEY (see .env.example).
"""
import time

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()

# --- 2. Template system -----------------------------------------------
# Variables ({input_language}, {output_language}, {text}) instead of a
# hardcoded sentence, so the same prompt can be reused for any request.
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that translates {input_language} "
            "to {output_language}. Reply with only the translation.",
        ),
        ("human", "{text}"),
    ]
)

# Models confirmed live on the Groq account via https://api.groq.com/openai/v1/models
# (llama-3.1-8b-instant and llama-3.3-70b-versatile were deprecated June 2026 —
# skip any tutorial that still lists them).
MODELS_TO_COMPARE = [
    "openai/gpt-oss-120b",   # large, best quality
    "openai/gpt-oss-20b",    # smaller/faster sibling
    "qwen/qwen3.8-27b",      # different model family, for contrast
]

INPUT_LANGUAGE = "English"
OUTPUT_LANGUAGE = "French"
TEXT = "I love programming."


def build_chain(model_name: str):
    """Assemble a prompt -> model -> parser chain (LCEL) for one model."""
    llm = ChatGroq(model=model_name)
    return prompt | llm | StrOutputParser()


def run_and_time(model_name: str) -> dict:
    """Invoke the chain once, tagging the run for LangSmith, and time it."""
    chain = build_chain(model_name)
    start = time.perf_counter()
    try:
        result = chain.invoke(
            {
                "input_language": INPUT_LANGUAGE,
                "output_language": OUTPUT_LANGUAGE,
                "text": TEXT,
            },
            config={
                # Shows up as the run name in the LangSmith trace view,
                # so you can find/compare each model's run at a glance.
                "run_name": f"exercise1-{model_name}",
                "tags": ["exercise1", model_name],
            },
        )
        elapsed = time.perf_counter() - start
        return {"model": model_name, "output": result, "seconds": elapsed, "error": None}
    except Exception as exc:  # noqa: BLE001 - want to keep comparing other models
        elapsed = time.perf_counter() - start
        return {"model": model_name, "output": None, "seconds": elapsed, "error": str(exc)}


if __name__ == "__main__":
    print(f"Translating: {TEXT!r} ({INPUT_LANGUAGE} -> {OUTPUT_LANGUAGE})\n")

    runs = [run_and_time(model) for model in MODELS_TO_COMPARE]

    print(f"{'model':<22} {'seconds':>8}  output")
    print("-" * 60)
    for run in sorted(runs, key=lambda r: r["seconds"]):
        if run["error"]:
            print(f"{run['model']:<22} {run['seconds']:>8.2f}  ERROR: {run['error']}")
        else:
            print(f"{run['model']:<22} {run['seconds']:>8.2f}  {run['output']}")

    print(
        "\nOpen https://smith.langchain.com and check the "
        "'agentic-ai-internship' project to see the traced runs "
        "(one per model, tagged 'exercise1')."
    )
