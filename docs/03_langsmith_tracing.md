# LangSmith Tracing

LangSmith is LangChain's observability platform. When `LANGSMITH_TRACING=true`
and `LANGSMITH_API_KEY` are set in the environment, every `Runnable.invoke()`
call is automatically traced — no code changes required beyond loading the
environment variables.

## Projects

Traces are grouped into a "project," set via the `LANGCHAIN_PROJECT`
environment variable. All runs from this internship's exercises land in the
`agentic-ai-internship` project at https://smith.langchain.com.

## Run names and tags

Passing a `config` dict to `.invoke()` lets you label individual runs:

```python
chain.invoke(input, config={"run_name": "my-run", "tags": ["exercise2"]})
```

This makes it possible to filter and compare specific runs in the LangSmith
UI instead of scrolling through an undifferentiated list.

## Nested traces for RAG

For a chain built from multiple steps (retriever, prompt, model, parser),
LangSmith records each step as a nested span inside the overall trace. This
means you can inspect exactly which document chunks a retriever returned for
a given question, separately from how the LLM used those chunks to generate
its answer — essential for debugging when a RAG system gives a wrong or
ungrounded answer.
