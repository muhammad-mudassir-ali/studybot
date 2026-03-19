"""
modules/youtube_recommender.py
==============================
Subtopic-based YouTube recommendation engine for StudyBot.

Pipeline:
  1. LLM expands the topic into 3 key subtopics with targeted search queries.
  2. YouTube Data API searches for the best 5 videos per subtopic.
  3. LLM picks the single best video per subtopic from those 5.
  4. Returns a list of up to 3 results, one per subtopic, with a subtopic label.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional

from modules.llm import get_llm


# ── Internal helper ────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """Invoke the shared Groq LLM and return the stripped text response."""
    return get_llm().invoke(prompt).content.strip()


def _safe_thumbnail(snippet: Dict) -> str:
    """Extract the best available thumbnail URL from a YouTube snippet."""
    thumbs = snippet.get("thumbnails", {})
    for size in ("high", "medium", "default"):
        url = thumbs.get(size, {}).get("url", "")
        if url:
            return url
    return ""


# ── Step 1 — Subtopic expansion ────────────────────────────────────────────────

def _expand_into_subtopics(
    topic: str,
    grade_level: str,
    pdf_chunks: str,
) -> List[Dict[str, str]]:
    """
    Ask Groq to break the topic into 3 subtopics, each with a targeted
    YouTube search query.  Returns a list of dicts: {title, search_query}.
    """
    context_snippet = pdf_chunks[:1500] if pdf_chunks else "(no PDF context)"

    prompt = f"""Topic: {topic}
Grade Level: {grade_level}
PDF Context: {context_snippet}

Break this topic into exactly 3 key subtopics a {grade_level} student must learn.
For each subtopic write the single most effective YouTube search query.

Return ONLY valid JSON — no markdown, no extra text:
{{
  "main_topic": "{topic}",
  "subtopics": [
    {{"title": "Subtopic 1 Name", "search_query": "youtube search query 1"}},
    {{"title": "Subtopic 2 Name", "search_query": "youtube search query 2"}},
    {{"title": "Subtopic 3 Name", "search_query": "youtube search query 3"}}
  ]
}}"""

    raw = _call_llm(prompt)

    # Strip any accidental markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(raw)
        subtopics = data.get("subtopics", [])
        # Enforce max-3 and required keys
        result = [
            s for s in subtopics
            if isinstance(s, dict) and "title" in s and "search_query" in s
        ][:3]
        if result:
            return result
    except Exception as e:
        print(f"[YouTube] ⚠️  Subtopic JSON parse error: {e}")

    # Fallback: simple split into 3 generic subtopics
    return [
        {"title": f"Introduction to {topic}",    "search_query": f"{topic} introduction for beginners"},
        {"title": f"Key Concepts of {topic}",    "search_query": f"{topic} key concepts explained"},
        {"title": f"Applications of {topic}",    "search_query": f"{topic} real world examples tutorial"},
    ]


# ── Step 2 — YouTube search per subtopic ───────────────────────────────────────

def _search_youtube(
    youtube_client,
    query: str,
    max_results: int = 5,
) -> List[Dict]:
    """Run one YouTube search and return the raw items list."""
    try:
        response = youtube_client.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results,
            relevanceLanguage="en",
            videoDuration="medium",    # 4–20 minutes
            videoEmbeddable="true",
            safeSearch="strict",
            order="relevance",
        ).execute()
        return response.get("items", [])
    except Exception as e:
        print(f"[YouTube] ❌ API error for query '{query}': {e}")
        return []


# ── Step 3 — LLM picks best video from 5 ─────────────────────────────────────

def _pick_best_video(
    subtopic_title: str,
    grade_level: str,
    items: List[Dict],
) -> int:
    """
    Send up to 5 video titles/descriptions to Groq and ask it to pick
    the single best index (0-based).  Returns that integer index.
    """
    if not items:
        return 0

    video_text = ""
    for i, item in enumerate(items):
        snip = item["snippet"]
        video_text += (
            f"{i}. Title: {snip['title']}\n"
            f"   Channel: {snip.get('channelTitle', '')}\n"
            f"   Description: {snip.get('description', '')[:120]}\n\n"
        )

    prompt = f"""Subtopic: {subtopic_title}
Grade Level: {grade_level}

Choose the single most accurate and educational YouTube video for this subtopic.
Return ONLY the integer index (0-based), e.g.: 2

Videos:
{video_text}"""

    raw = _call_llm(prompt).strip()

    # Extract first integer found
    match = re.search(r"\d+", raw)
    if match:
        idx = int(match.group())
        return idx if 0 <= idx < len(items) else 0
    return 0


# ── Main public function ───────────────────────────────────────────────────────

def get_youtube_recommendations(
    topic: str,
    grade_level: str,
    pdf_chunks: str = "",
) -> List[Dict[str, Any]]:
    """
    Returns up to 3 YouTube video recommendations, one per subtopic.

    Args:
        topic:       Main topic from the user query.
        grade_level: Target grade (e.g. '7th Grade').
        pdf_chunks:  PDF text for grounding the subtopic expansion.

    Returns:
        List of dicts: {subtopic, title, url, thumbnail, channel, description}
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("[YouTube] ⚠️  YOUTUBE_API_KEY not set — returning empty list.")
        return []

    # ── STEP 1: Expand topic → 3 subtopics ───────────────────────────────────
    print(f"[YouTube] 📚 Expanding '{topic}' into subtopics...")
    subtopics = _expand_into_subtopics(topic, grade_level, pdf_chunks)
    print(f"[YouTube] Subtopics: {[s['title'] for s in subtopics]}")

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        print(f"[YouTube] ❌ Failed to initialise YouTube client: {e}")
        return []

    results: List[Dict[str, Any]] = []

    for subtopic in subtopics:
        title = subtopic["title"]
        query = subtopic["search_query"]
        print(f"[YouTube] 🔍 Searching for subtopic '{title}': '{query}'")

        # ── STEP 2: Search YouTube for this subtopic ──────────────────────────
        items = _search_youtube(youtube, query, max_results=5)
        if not items:
            print(f"[YouTube] ⚠️  No results for subtopic '{title}' — skipping.")
            continue

        # ── STEP 3: LLM picks the best single video ───────────────────────────
        best_idx = _pick_best_video(title, grade_level, items)
        print(f"[YouTube] 🏆 Best video index for '{title}': {best_idx}")

        # ── STEP 4: Build result dict ─────────────────────────────────────────
        item = items[best_idx]
        snip = item["snippet"]
        video_id = item["id"]["videoId"]

        results.append({
            "subtopic":    title,
            "title":       snip["title"],
            "url":         f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail":   _safe_thumbnail(snip),
            "channel":     snip.get("channelTitle", ""),
            "description": snip.get("description", "")[:200],
        })

    print(f"[YouTube] ✅ Done — {len(results)} video(s) curated.")
    return results


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    results = get_youtube_recommendations(
        topic="ETL Pipelines",
        grade_level="10th Grade",
        pdf_chunks="ETL stands for Extract, Transform, Load. It is a data integration process used in data warehousing.",
    )

    for i, v in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"  Subtopic: {v['subtopic']}")
        print(f"  {i}. {v['title']}")
        print(f"     {v['url']}")
        print(f"     Channel: {v['channel']}")
