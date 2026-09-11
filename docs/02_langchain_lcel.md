# LangChain Expression Language (LCEL)

LCEL is LangChain's syntax for composing "runnables" — prompts, models,
parsers, and retrievers — into a pipeline using the `|` (pipe) operator.

A basic chain looks like:

```python
chain = prompt | llm | output_parser
```

Each stage is a `Runnable`. The pipe operator wires the output of one stage
into the input of the next, so `chain.invoke(input)` runs the whole pipeline
in one call.

## Prompt templates

`ChatPromptTemplate.from_messages([...])` builds a reusable prompt with
placeholders like `{text}` or `{question}`. Passing a dict to `.invoke()`
fills those placeholders in, so the same template can be reused across many
different inputs instead of hardcoding a new prompt string each time.

## Parallel steps

LCEL chains can run multiple sub-steps in parallel using a dict literal.
This is the standard pattern for RAG: the retriever and the raw question
need to reach the prompt at the same time.

```python
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

Here, `retriever` fetches relevant documents for the question,
`RunnablePassthrough()` forwards the original question unchanged, and both
results land in the prompt template together.
