"""RAG Agent: answers questions from the internal ./docs knowledge base."""
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import DOCS_DIR, make_llm

_loader = DirectoryLoader(str(DOCS_DIR), glob="*.md", loader_cls=TextLoader)
_documents = _loader.load()
_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
_chunks = _splitter.split_documents(_documents)
_retriever = InMemoryVectorStore.from_documents(_chunks, FastEmbedEmbeddings()).as_retriever(
    search_kwargs={"k": 4}
)

_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer using only the provided context. If the context does "
            "not contain the answer, say you don't know instead of "
            "guessing.\n\nContext:\n{context}",
        ),
        ("human", "{query}"),
    ]
)
_answer_chain = _answer_prompt | make_llm() | StrOutputParser()


@tool
def rag_agent(query: str) -> str:
    """Answer questions using the internal knowledge base (docs about Groq
    models, LangChain/LCEL, and LangSmith tracing). Use this for any
    question specifically about Groq, LangChain, or LangSmith."""
    docs = _retriever.invoke(query)
    if not docs:
        return "No relevant internal documents found."
    context = "\n\n".join(
        f"[{Path(d.metadata.get('source', '?')).name}]\n{d.page_content}" for d in docs
    )
    return _answer_chain.invoke({"context": context, "query": query})
