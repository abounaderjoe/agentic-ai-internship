"""Shared configuration for the capstone multi-agent system."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"

MODEL_NAME = "openai/gpt-oss-120b"

# A separate, read-only DB role (see seed.sql) so a malformed or malicious
# LLM-generated query physically cannot write, regardless of app-level checks.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://capstone_reader:capstone_reader@localhost:5432/capstone"
)


def make_llm(temperature: float = 0) -> ChatGroq:
    return ChatGroq(model=MODEL_NAME, temperature=temperature)
