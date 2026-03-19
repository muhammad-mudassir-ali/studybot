"""
modules/embeddings.py
======================
Vector storage and retrieval module for StudyBot.

Uses HuggingFace (local) embeddings and ChromaDB to store and query
text chunks extracted from books.
"""

import chromadb
from typing import List, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from config.settings import (
    EMBEDDING_MODEL_NAME,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME
)

# ── Global Embedding Instance ───────────────────────────────────────────
# Initializes the model once for use across all embedding functions
_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def get_vector_store(collection_name: str = CHROMA_COLLECTION_NAME) -> Chroma:
    """
    Returns a LangChain Chroma vector store instance.
    """
    return Chroma(
        collection_name=collection_name,
        embedding_function=_embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )


def collection_exists(collection_name: str) -> bool:
    """
    Checks if a collection already has data stored in ChromaDB.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        # Attempt to get the collection; returns it if exists, raises error if not
        collection = client.get_collection(name=collection_name)
        return collection.count() > 0
    except Exception:
        return False


def store_embeddings(chunks: List[Any], collection_name: str = CHROMA_COLLECTION_NAME) -> bool:
    """
    Takes text chunks, creates embeddings, and saves them to ChromaDB.
    """
    try:
        if not chunks:
            return False
            
        # Create vector store and add documents
        Chroma.from_documents(
            documents=chunks,
            embedding=_embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=collection_name
        )
        return True
    except Exception as e:
        print(f"❌ Error storing embeddings: {str(e)}")
        return False


def query_embeddings(query: str, collection_name: str = CHROMA_COLLECTION_NAME, top_k: int = 5) -> List[Any]:
    """
    Retrieves the most relevant text chunks for a given query string.
    """
    try:
        vector_store = get_vector_store(collection_name)
        # Similarity search returns the top K most relevant chunks
        results = vector_store.similarity_search(query, k=top_k)
        return results
    except Exception as e:
        print(f"❌ Error querying embeddings: {str(e)}")
        return []
