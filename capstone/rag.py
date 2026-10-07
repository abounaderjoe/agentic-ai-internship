"""RAG Node: answers questions from the internal ./docs knowledge base."""
from pathlib import Path
from typing import Literal

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.types import Command

from .config import DOCS_DIR, make_llm
from .state import SupervisorState, current_task

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


def rag_agent(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """Answer questions using the internal knowledge base (docs about Groq
    models, LangChain/LCEL, and LangSmith tracing)."""
    query = current_task(state)
    docs = _retriever.invoke(query)
    if not docs:
        reply = "No relevant internal documents found."
    else:
        context = "\n\n".join(
            f"[{Path(d.metadata.get('source', '?')).name}]\n{d.page_content}" for d in docs
        )
        reply = _answer_chain.invoke({"context": context, "query": query}, config={"tags": ["final_answer"]})
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="rag_agent")],
            "visited": ["rag_agent"],
        },
    )
