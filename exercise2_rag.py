"""
Exercise 2: RAG Implementation
Step 5 of the Agentic AI Onboarding Roadmap.

Covers all five goals of the exercise:
  1. Build a Retrieval-Augmented Generation system.
  2. Index a set of documents (the markdown files in ./docs).
  3. Create relevant queries and retrieve information for them.
  4. Generate coherent responses using a Groq LLM based on retrieved context.
  5. Trace and evaluate RAG performance in LangSmith.

Groq does not serve an embeddings model, so retrieval uses a local,
free embedding model (FastEmbed) while generation still uses ChatGroq.
"""
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
MODEL_NAME = "openai/gpt-oss-120b"

# --- 2. Index a set of documents ---------------------------------------
loader = DirectoryLoader(str(DOCS_DIR), glob="*.md", loader_cls=TextLoader)
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
chunks = splitter.split_documents(documents)

embeddings = FastEmbedEmbeddings()  # local model, downloaded once and cached
vectorstore = InMemoryVectorStore.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# --- 3/4. Retrieval + generation chain (LCEL) ---------------------------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an assistant answering questions using only the "
            "provided context. If the context does not contain the answer, "
            "say you don't know instead of guessing.\n\nContext:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


def format_docs(docs) -> str:
    return "\n\n".join(f"[{doc.metadata.get('source', '?')}]\n{doc.page_content}" for doc in docs)


llm = ChatGroq(model=MODEL_NAME)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# A few test queries that exercise different documents in ./docs
QUERIES = [
    "Which Groq models are currently available, and which two were deprecated?",
    "What does the pipe operator do in LCEL?",
    "How do I label an individual run so I can find it in the LangSmith UI?",
    "Does Groq offer an embeddings API?",
]


def ask(question: str) -> dict:
    start = time.perf_counter()
    retrieved = retriever.invoke(question)
    answer = rag_chain.invoke(
        question,
        config={
            "run_name": f"exercise2-rag-query",
            "tags": ["exercise2", "rag"],
        },
    )
    elapsed = time.perf_counter() - start
    return {
        "question": question,
        "answer": answer,
        "sources": [doc.metadata.get("source", "?") for doc in retrieved],
        "seconds": elapsed,
    }


if __name__ == "__main__":
    print(f"Indexed {len(chunks)} chunks from {len(documents)} documents in ./docs\n")

    for query in QUERIES:
        result = ask(query)
        print(f"Q: {result['question']}")
        print(f"A: {result['answer']}")
        print(f"   (retrieved from: {', '.join(Path(s).name for s in result['sources'])}, "
              f"{result['seconds']:.2f}s)")
        print()

    print(
        "Open https://smith.langchain.com and check the "
        "'agentic-ai-internship' project — each query's trace shows the "
        "retriever step (which chunks were fetched) nested inside the "
        "ChatGroq generation step (tagged 'exercise2')."
    )
