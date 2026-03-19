"""
modules/classroom_video.py
==========================
Advanced Professor Avatar Teaching System.
Orchestrates: ChromaDB -> Groq (JSON Sections) -> Playwright Rendering -> gTTS -> ffmpeg.
"""

import os
import json
import re
import subprocess
import tempfile
import asyncio
import sys
import time
from typing import List, Dict, Any
from langchain_core.prompts import PromptTemplate
from modules.llm import get_llm
from modules.embeddings import query_embeddings

# ── Environment Setup ────────────────────────────────────────────────────
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[Classroom] ⚠️ gTTS not installed. Videos will be silent.")

# ── Global Constants ──────────────────────────────────────────────────────
FPS = 24
MIN_SECTION_DURATION = 8.0  # Seconds per teaching section
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

def _load_classroom_prompt() -> PromptTemplate:
    """Loads the system prompt for section-based lesson extraction."""
    with open("prompts/classroom_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()
    return PromptTemplate(
        input_variables=["topic", "grade_level", "context"],
        template=template
    )

def _get_html_template(content: Dict[str, Any], active_section_idx: int) -> str:
    """
    Generates the HTML/CSS for the classroom scene.
    State is driven by active_section_idx.
    """
    sections = content.get("sections", [])
    if not sections:
        return "<h1>No lesson content found.</h1>"

    current = sections[active_section_idx]
    topic_title = content.get("topic_title", "Lesson")
    total_sections = len(sections)
    progress = ((active_section_idx + 1) / total_sections) * 100

    # Keyword bubbles HTML
    keywords_html = "".join([
        f'<div class="keyword-bubble" style="left: {20 + (i*15)}%; top: {15 + (i*8)}%; animation-delay: {i*0.5}s;">{kw}</div>'
        for i, kw in enumerate(current.get("keywords", []))
    ])

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        :root {{
            --primary: #2c3e50;
            --accent: #e67e22;
            --board: #112d1b;
            --chalk: #f0f0f0;
            --wall: #34495e;
            --floor: #7f8c8d;
        }}
        body {{
            margin: 0; padding: 0; overflow: hidden;
            width: 1280px; height: 720px;
            font-family: 'Comic Sans MS', 'Segoe UI', sans-serif;
            background: var(--wall);
        }}
        .classroom {{
            position: relative; width: 100%; height: 100%;
        }}
        .blackboard {{
            position: absolute; right: 40px; top: 40px;
            width: 750px; height: 450px;
            background: var(--board);
            border: 15px solid #5d4037; border-radius: 10px;
            box-shadow: 10px 10px 40px rgba(0,0,0,0.5);
            padding: 40px; color: var(--chalk);
            font-size: 28px;
        }}
        .blackboard h2 {{ color: #ffd54f; margin-top: 0; border-bottom: 2px dashed #ffd54f; padding-bottom: 10px; }}
        .board-content {{ margin-top: 20px; line-height: 1.6; white-space: pre-wrap; }}
        .professor-container {{
            position: absolute; left: 100px; bottom: 80px;
            width: 300px; height: 500px;
        }}
        .professor {{
            position: relative; width: 100%; height: 100%;
        }}
        .body {{
            position: absolute; bottom: 0; width: 220px; height: 350px;
            background: #2980b9; border-radius: 60px 60px 0 0;
            left: 40px;
            animation: body-idle 3s infinite ease-in-out;
        }}
        .head {{
            position: absolute; top: 60px; left: 90px;
            width: 120px; height: 130px; background: #ffcc80;
            border-radius: 50%; z-index: 2;
        }}
        .mouth {{
            position: absolute; bottom: 30px; left: 35px;
            width: 50px; height: 10px; background: #8d6e63;
            border-radius: 10px;
            animation: speaking 0.4s infinite;
        }}
        .arm-right {{
            position: absolute; right: -20px; top: 120px;
            width: 40px; height: 200px; background: #2980b9;
            border-radius: 20px; transform-origin: top center;
            transform: rotate(-30deg);
            animation: pointing 4s infinite alternate;
        }}
        .speech-bubble {{
            position: absolute; left: 320px; top: 100px;
            background: white; border-radius: 20px; padding: 25px;
            width: 280px; font-size: 20px; line-height: 1.4;
            box-shadow: 5px 5px 20px rgba(0,0,0,0.2);
            z-index: 5;
        }}
        .speech-bubble::after {{
            content: ''; position: absolute; left: -20px; top: 40px;
            border-width: 10px 20px 10px 0;
            border-style: solid; border-color: transparent white transparent transparent;
        }}
        .keyword-bubble {{
            position: absolute; background: rgba(230, 126, 34, 0.9);
            color: white; padding: 10px 20px; border-radius: 30px;
            font-weight: bold; font-size: 18px;
            animation: float 3s infinite ease-in-out;
        }}
        .lesson-header {{
            position: absolute; left: 40px; top: 30px; color: white;
            font-size: 24px; font-weight: bold; background: rgba(0,0,0,0.3);
            padding: 10px 20px; border-radius: 10px;
        }}
        .progress-bar-container {{
            position: absolute; bottom: 20px; left: 50px;
            width: calc(100% - 100px); height: 15px;
            background: rgba(0,0,0,0.2); border-radius: 10px;
        }}
        .progress-bar {{
            height: 100%; background: var(--accent);
            width: {progress}%; border-radius: 10px;
            transition: width 0.5s ease;
        }}
        .student-desk {{
            position: absolute; bottom: 0; left: 400px;
            width: 500px; height: 60px; background: #4e342e;
            border-radius: 10px 10px 0 0;
        }}
        @keyframes speaking {{
            0%, 100% {{ height: 10px; }}
            50% {{ height: 25px; }}
        }}
        @keyframes body-idle {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-5px); }}
        }}
        @keyframes pointing {{
            0% {{ transform: rotate(-30deg); }}
            100% {{ transform: rotate(-100deg); }}
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-15px); }}
        }}
    </style>
</head>
<body>
    <div class="classroom">
        <div class="lesson-header">{topic_title} - Section {active_section_idx + 1}/{total_sections}</div>
        <div class="blackboard">
            <h2>{current.get("heading", "Topic")}</h2>
            <div class="board-content">{current.get("board_content", "")}</div>
        </div>
        <div class="professor-container">
            <div class="professor">
                <div class="body"></div>
                <div class="head">
                    <div class="mouth"></div>
                </div>
                <div class="arm-right"></div>
            </div>
        </div>
        <div class="speech-bubble">
            {current.get("explanation", "")}
        </div>
        <div class="student-desk"></div>
        <div class="progress-bar-container">
            <div class="progress-bar"></div>
        </div>
        {keywords_html}
    </div>
</body>
</html>
    """


def generate_classroom_video(topic: str, grade_level: str = "5th Grade", collection_name: str = "default") -> bytes | str:
    """
    Orchestrates the full pipeline to create a multi-section professor lesson.

    Returns:
        bytes: Raw MP4 video bytes on success.
        str:   Formatted text explanation if video generation fails (fallback).
    """
    print(f"\n[Classroom] 🎓 Starting Lesson Creation: '{topic}' for {grade_level}")

    # Temp dir holds only intermediate frames and audio — NOT the final video
    temp_dir = tempfile.mkdtemp(prefix="professor_lesson_")
    content: Dict[str, Any] = {}

    try:
        # ── STEP 1: Content Extraction ──────────────────────────────────────
        print("[Classroom] Step 1: Querying ChromaDB and extracting JSON content...")
        chunks = query_embeddings(topic, collection_name=collection_name, top_k=10)
        context = "\n\n".join([c.page_content for c in chunks])

        llm = get_llm()
        prompt_tmpl = _load_classroom_prompt()
        chain = prompt_tmpl | llm

        raw_response = chain.invoke({"topic": topic, "grade_level": grade_level, "context": context}).content

        # Robust JSON Parsing
        try:
            content_str = re.sub(r'```json\s*', '', raw_response)
            content_str = re.sub(r'```\s*', '', content_str).strip()
            content = json.loads(content_str)
        except Exception as e:
            print(f"[Classroom] ❌ JSON Error: {e}. Retrying once...")
            raw_response = llm.invoke(
                f"Extract educational sections for '{topic}' as JSON. Chunks: {context[:2000]}"
            ).content
            content_str = re.sub(r'```json\s*', '', raw_response)
            content_str = re.sub(r'```\s*', '', content_str).strip()
            content = json.loads(content_str)

        sections = content.get("sections", [])
        if not sections:
            return "Failed to extract logical lesson sections."

        # ── STEP 2: Rendering with Playwright ──────────────────────────────
        print(f"[Classroom] Step 2: Rendering {len(sections)} sections with Playwright...")

        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": FRAME_WIDTH, "height": FRAME_HEIGHT})

            total_rendered_frames = 0

            for idx, sec in enumerate(sections):
                words = len(sec.get("explanation", "").split())
                duration = max(MIN_SECTION_DURATION, words / 2.5 + 2.0)
                sec_frames = int(duration * FPS)

                print(f"  [Renderer] Section {idx+1}/{len(sections)}: {duration:.1f}s ({sec_frames} frames)")

                html = _get_html_template(content, idx)
                html_path = os.path.join(temp_dir, f"section_{idx}.html")
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(html)

                page.goto(f"file://{os.path.abspath(html_path)}")
                page.wait_for_load_state("networkidle")

                for f in range(sec_frames):
                    frame_path = os.path.join(temp_dir, f"frame_{total_rendered_frames:05d}.png")
                    page.screenshot(path=frame_path)
                    total_rendered_frames += 1

                    if total_rendered_frames % 50 == 0:
                        print(f"    Captured frame {total_rendered_frames}...")

            browser.close()

        # ── STEP 3: Audio Generation (gTTS) ────────────────────────────────
        audio_path = os.path.join(temp_dir, "lesson_narration.mp3")
        if TTS_AVAILABLE:
            print("[Classroom] Step 3: Generating audio narration...")
            narration = content.get("narration_script", "Today we will learn something new.")
            gTTS(text=narration, lang='en', slow=False).save(audio_path)
        else:
            audio_path = None

        # ── STEP 4: Video Assembly — pipe output to memory ──────────────────
        print("[Classroom] Step 4: Assembling final MP4 into memory (no disk write)...")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(temp_dir, "frame_%05d.png"),
        ]

        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])

        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            # frag_keyframe+empty_moov make the MP4 container valid when piped
            "-movflags", "frag_keyframe+empty_moov",
            "-shortest",
            "-f", "mp4",
            "pipe:1",   # write encoded output to stdout
        ])

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(f"[Classroom] ❌ ffmpeg Error:\n{proc.stderr.decode(errors='replace')}")
            raise Exception("ffmpeg assembly failed.")

        video_bytes: bytes = proc.stdout
        print(f"[Classroom] ✅ Lesson Complete — {len(video_bytes):,} bytes held in memory")
        return video_bytes

    except Exception as e:
        print(f"[Classroom] ❌ Error: {e}")
        # FALLBACK: return formatted text so the UI can still show something
        try:
            fb_text = f"### {content.get('topic_title', topic)}\n\n"
            for sec in content.get("sections", []):
                fb_text += f"**{sec['heading']}**\n{sec['explanation']}\n\n*On the board:* {sec['board_content']}\n\n"
            fb_text += f"\n**Summary:** {content.get('summary', '')}"
            return fb_text
        except Exception:
            return "I'm sorry, I couldn't generate the video lesson. Please check my logs."

    finally:
        # Clean up ALL temp files (frames, section HTML, audio)
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"[Classroom] 🧹 Cleaned up temp dir: {temp_dir}")
        except Exception as ce:
            print(f"[Classroom] ⚠️ Failed to clean up temp dir: {ce}")


if __name__ == "__main__":
    # Smoke Test
    from dotenv import load_dotenv
    load_dotenv()
    res = generate_classroom_video("The Process of Evaporation")
    if isinstance(res, bytes):
        print(f"Test Result: {len(res):,} video bytes returned in memory ✅")
    else:
        print(f"Test Result (text fallback):\n{res}")
