"""SQL Query Agent: writes and runs a read-only SQL query against the
PostgreSQL sample database, then explains the results in plain language.

Defense in depth against a malformed/malicious LLM-generated query:
  1. The query must parse as a single SELECT with no forbidden keywords.
  2. Even if that check were bypassed, DATABASE_URL connects as
     'capstone_reader', a DB role with SELECT-only grants (see seed.sql) --
     so a write is rejected by Postgres itself, not just by app code.
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .config import DATABASE_URL, make_llm

_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SCHEMA_DESCRIPTION = """
customers(id, name, email, country)
products(id, name, category, price)
orders(id, customer_id, order_date, status)
order_items(id, order_id, product_id, quantity, unit_price)
"""

_sql_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You write a single PostgreSQL SELECT query to answer the "
            "question, using this schema:\n{schema}\n"
            "Rules: SELECT only, no semicolons, no comments, no markdown "
            "fences. Reply with ONLY the raw SQL query.",
        ),
        ("human", "{question}"),
    ]
)
_sql_chain = _sql_prompt | make_llm() | StrOutputParser()

_explain_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Explain SQL query results in plain, concise natural language "
            "for a non-technical reader. Don't mention SQL syntax.",
        ),
        ("human", "Question: {question}\nResults: {results}"),
    ]
)
_explain_chain = _explain_prompt | make_llm() | StrOutputParser()

_FORBIDDEN = ("insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", ";")


def _extract_sql(raw: str) -> str:
    sql = raw.strip().strip("`")
    if sql.lower().startswith("sql\n"):
        sql = sql[4:]
    return sql.strip()


def _is_safe_select(sql: str) -> bool:
    normalized = sql.strip().rstrip(";").lower()
    return normalized.startswith("select") and not any(word in normalized for word in _FORBIDDEN)


@tool
def sql_query_agent(question: str) -> str:
    """Answer questions about customers, products, orders, and order items
    in the sample sales database by writing and running a SQL query, then
    explaining the results in plain language. Use this for any question
    about sales, revenue, orders, customers, or products."""
    sql = _extract_sql(_sql_chain.invoke({"schema": SCHEMA_DESCRIPTION, "question": question}))
    if not _is_safe_select(sql):
        return f"Refused to run a non-SELECT or unsafe query: {sql}"
    try:
        with _engine.connect() as conn:
            rows = conn.execute(text(sql)).mappings().all()
    except SQLAlchemyError as exc:
        return f"Query failed ({exc}). Generated SQL was: {sql}"
    results_str = "\n".join(str(dict(r)) for r in rows[:50]) or "(no rows returned)"
    explanation = _explain_chain.invoke({"question": question, "results": results_str})
    return f"{explanation}\n\n[SQL used: {sql}]\n[Raw rows: {results_str}]"
