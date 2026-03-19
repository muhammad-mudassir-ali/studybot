"""
graph/nodes.py
==============
Contains the node functions for our LangGraph workflow.
Each node takes the state and returns a partial state update.
"""

from typing import Dict, Any, List
from graph.state import StudyBotState
from modules.llm import get_llm
from modules.embeddings import query_embeddings
from modules.rag import get_rag_answer
from modules.topic_explainer import explain_topic
from modules.youtube_recommender import get_youtube_recommendations
from modules.manim_generator import generate_manim_video
from langchain_core.messages import HumanMessage, SystemMessage

def extract_topic(user_input: str) -> str:
    """
    Strips common conversational prefixes to extract the core topic.
    """
    prefixes = [
        "create a lesson about:",
        "create lesson about:",
        "animate:",
        "animate",
        "create explanation video on",
        "create explaination video on",
        "teach me about",
        "teach me",
        "explain",
        "show me",
        "make a video about",
        "video about",
        "lesson about",
    ]
    topic = user_input.lower().strip()
    for prefix in prefixes:
        if topic.startswith(prefix):
            topic = topic[len(prefix):].strip()
            # If after stripping it starts with another prefix or punctuation, strip it
            if topic.startswith(":") or topic.startswith("-"):
                topic = topic[1:].strip()
            break
    
    final_topic = topic.strip() or user_input.strip()
    print(f"DEBUG: Extracted topic -> '{final_topic}'")
    return final_topic

def classify_intent(state: StudyBotState) -> Dict[str, Any]:
    """
    Uses the LLM to classify user input into one of four categories:
    'qa', 'explain', 'youtube', 'animate', or 'lesson'.
    """
    print("\n--- [NODE] CLASSIFY INTENT ---")
    question = state["question"]
    llm = get_llm()

    system_prompt = (
        "You are an intent classifier. Categorize the user's message into exactly one of these categories: "
        "'qa', 'explain', 'youtube', 'animate', 'lesson'.\n"
        "- 'qa': General questions about content, definitions, or facts from the book.\n"
        "- 'explain': When the user wants a simple explanation or summary for a specific grade level.\n"
        "- 'youtube': When the user asks for videos, recommendations, or visual resources from YouTube.\n"
        "- 'animate': When the user specifically wants an animation or move-based visualization.\n"
        "- 'lesson': When the user wants a full topic lesson, video lesson, or asks to 'teach me' about something.\n"
        "Output ONLY the category name."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    response = llm.invoke(messages)
    intent = response.content.lower().strip()

    allowed = ["qa", "explain", "youtube", "animate", "lesson"]
    if intent not in allowed:
        intent = "qa"  # default

    print(f"DEBUG: Classified Intent -> '{intent}'")
    return {"intent": intent}


def retrieve_chunks(state: StudyBotState) -> Dict[str, Any]:
    """
    Retrieves relevant text chunks from ChromaDB using the specific collection name.
    """
    print("\n--- [NODE] RETRIEVE CONTEXT ---")
    question = state["question"]
    collection = state.get("collection_name")

    print(f"DEBUG: Retrieval Query -> '{question}'")
    print(f"DEBUG: Using Collection -> '{collection}'")

    chunks = query_embeddings(question, collection_name=collection, top_k=5)

    print(f"DEBUG: Chunks Retrieved -> {len(chunks)}")
    if chunks:
        print(f"DEBUG: Sample from first chunk -> {chunks[0].page_content[:200]}...")
    else:
        print("DEBUG: ⚠️ NO CHUNKS RETRIEVED! Check if PDF was successfully processed.")

    return {"context": chunks}


def qa_answer(state: StudyBotState) -> Dict[str, Any]:
    """
    Answers the user's question using the RAG chain.
    """
    print("\n--- [NODE] GENERATE QA ANSWER ---")
    question = state["question"]
    context = state["context"]

    answer = get_rag_answer(question, context)
    return {"answer": answer}


def explain_node(state: StudyBotState) -> Dict[str, Any]:
    """
    Generates a simplified topic explanation based on selected grade level.
    """
    print("\n--- [NODE] EXPLAIN TOPIC ---")
    topic = extract_topic(state["question"])
    grade = state.get("grade_level", "5th Grade")

    print(f"DEBUG: Topic -> '{topic}' | Level -> '{grade}'")

    answer = explain_topic(topic, grade)
    return {"answer": answer}


def recommend_youtube_node(state: StudyBotState) -> Dict[str, Any]:
    """
    Fetches YouTube video recommendations.
    Passes PDF chunks to the recommender so the LLM can build a precise query.
    """
    print("\n--- [NODE] RECOMMEND YOUTUBE ---")
    topic = extract_topic(state["question"])
    grade = state.get("grade_level", "5th Grade")

    # Build a text snippet from already-retrieved PDF chunks (if any)
    context_chunks = state.get("context", [])
    pdf_chunks = "\n\n".join([c.page_content for c in context_chunks]) if context_chunks else ""

    print(f"DEBUG: Topic -> '{topic}' | Level -> '{grade}' | Chunks -> {len(context_chunks)}")

    vids = get_youtube_recommendations(topic, grade, pdf_chunks)
    return {"youtube_results": vids, "answer": None}


def animate_node(state: StudyBotState) -> Dict[str, Any]:
    """
    Generates a professional Manim animation video and returns raw bytes in state.
    Falls back to text if video generation fails.
    """
    print("\n--- [NODE] GENERATE ANIMATION ---")
    topic = extract_topic(state["question"])
    collection = state.get("collection_name", "studybot_docs")
    grade = state.get("grade_level", "Grade 10")

    print(f"DEBUG: Animate Topic -> '{topic}'")

    result = generate_manim_video(topic, grade, collection)
    if isinstance(result, bytes):
        return {
            "video_bytes": result,
            "intent": "animate",
            "answer": "🎥 Here is your professional Manim visualization!",
        }
    # Text fallback
    return {"answer": result, "intent": "qa", "video_bytes": None}


def generate_lesson_node(state: StudyBotState) -> Dict[str, Any]:
    """
    Generates a full educational Manim video lesson.
    Returns raw video bytes in state.
    """
    print("\n--- [NODE] GENERATE LESSON VIDEO ---")
    topic = extract_topic(state["question"])
    collection = state.get("collection_name", "studybot_docs")
    grade = state.get("grade_level", "Grade 10")

    print(f"DEBUG: Lesson Topic -> '{topic}'")

    result = generate_manim_video(topic, grade, collection)
    if isinstance(result, bytes):
        return {
            "video_bytes": result,
            "intent": "lesson",
            "answer": "🎓 I've prepared a professional Manim lesson for you!",
        }
    # Text fallback
    return {"answer": result, "intent": "qa", "video_bytes": None}
