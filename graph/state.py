"""
graph/state.py
==============
Defines the state structure for our LangGraph workflow.
"""

from typing import TypedDict, List, Optional
from langchain_core.documents import Document

class StudyBotState(TypedDict):
    """
    Represents the state of our StudyBot graph.

    Attributes:
        question:        The user's input/query.
        intent:          Classified intent ('qa', 'explain', 'animate', 'youtube', 'lesson').
        context:         List of chunks retrieved from ChromaDB (for RAG).
        answer:          The final generated answer string (text).
        video_bytes:     Raw MP4 bytes when a video lesson is generated in memory.
        collection_name: ChromaDB collection name for the uploaded PDF.
        grade_level:     Selected grade level (e.g. '5th Grade').
        youtube_results: List of YouTube video result dicts.
    """
    question: str
    intent: Optional[str]
    context: List[Document]
    answer: Optional[str]
    video_bytes: Optional[bytes]
    collection_name: Optional[str]
    grade_level: str
    youtube_results: Optional[List]
