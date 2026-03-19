"""
modules/manim_generator.py
==========================
Professional Manim-based educational video generator.
No Playwright, no avatar, no CSS slides. No LaTeX/MathTex.

Pipeline:
  1. Query ChromaDB for PDF context -> LLM generates lesson JSON.
  2. LLM generates a complete Manim Python script from JSON.
  3. Validate and fix generated Manim code (MathTex -> Text, etc.).
  4. Render with Manim via subprocess (low quality for speed).
  5. Generate narration via gTTS and merge with ffmpeg.
  6. Return raw video bytes and cleanup.
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from modules.llm import get_llm
from modules.embeddings import query_embeddings

# Try importing gTTS for narration
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[ManimGen] WARNING: gTTS not installed. Videos will be silent.")

# Paths
_HERE = Path(__file__).resolve().parent.parent
_PROMPT_DIR = _HERE / "prompts"

def _load_prompt(filename: str) -> str:
    """Loads a prompt template from the prompts/ directory."""
    path = _PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _extract_json(text: str) -> str:
    """Strips markdown fences and extracts the first JSON object."""
    text = re.sub(r"```(?:json)?", "", text)
    text = re.sub(r"```", "", text).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text

# ═════════════════════════════════════════════════════════════════════════
# STEP 1 — Extract content from PDF
# ═════════════════════════════════════════════════════════════════════════

def extract_lesson_content(
    topic: str,
    grade_level: str,
    collection_name: str,
) -> Optional[Dict]:
    """
    STEP 1: Retrieves PDF chunks from ChromaDB and uses Groq LLM to produce
    structured JSON content.
    """
    print(f"[ManimGen] STEP 1: Extracting content for topic: {topic}")
    
    # Query ChromaDB
    chunks = query_embeddings(topic, collection_name=collection_name, top_k=10)
    context = "\n\n".join([c.page_content for c in chunks])
    
    if not context:
        print("[ManimGen] ERROR: No context found in ChromaDB.")
        return None

    # Load and fill prompt
    prompt_template = _load_prompt("manim_prompt.txt")
    prompt_text = prompt_template.format(
        topic=topic,
        grade_level=grade_level,
        context=context[:5000] # Limit context size
    )

    # Call LLM
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt_text)])
    raw_content = response.content

    # Parse JSON
    try:
        json_str = _extract_json(raw_content)
        data = json.loads(json_str)
        print(f"[ManimGen]   Step 1 Success: Extracted {len(data.get('sections', []))} sections.")
        return data
    except Exception as e:
        print(f"[ManimGen] ERROR: JSON parsing failed: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════
# STEP 2 — Generate Manim Python script dynamically
# ═════════════════════════════════════════════════════════════════════════

def generate_manim_script(content: Dict) -> str:
    """
    STEP 2: Sends JSON content to Groq LLM to write a complete Manim Python script.
    """
    print("[ManimGen] STEP 2: Generating Manim script...")
    
    system_prompt = _load_prompt("manim_code_prompt.txt")
    user_prompt = f"Lesson Content JSON:\n{json.dumps(content, indent=2)}"

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    code = response.content.strip()
    
    # Strip markdown fences
    code = re.sub(r"```(?:python)?", "", code)
    code = re.sub(r"```", "", code).strip()
    
    return code

# ═════════════════════════════════════════════════════════════════════════
# STEP 3 — Validate and fix generated Manim code
# ═════════════════════════════════════════════════════════════════════════

def _validate_and_fix_code(code: str) -> str:
    """
    STEP 3: Check and fix common errors in the generated Manim code.
    """
    print("[ManimGen] STEP 3: Validating and fixing Manim code...")
    
    # 1. Replace MathTex/Tex with Text
    code = code.replace("MathTex", "Text").replace("Tex(", "Text(")
    
    # 2. Remove LaTeX backslashes in Text()
    # Replace common LaTeX macros with plain text
    code = re.sub(r"\\(?:frac|sqrt|alpha|beta|gamma|delta|sum|int|infty)", " ", code)
    code = code.replace("{", "").replace("}", "").replace("\\", "")
    
    # 3. Clean up imports - only 'from manim import *'
    lines = code.splitlines()
    final_lines = ["from manim import *"]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import ") or (stripped.startswith("from ") and "manim" not in stripped):
            continue
        if stripped.startswith("from manim import *"):
            continue
        final_lines.append(line)
    
    code = "\n".join(final_lines)
    
    # 4. Ensure class name is TopicLesson
    class_match = re.search(r"class\s+(\w+)\s*\(Scene\):", code)
    if class_match:
        current_name = class_match.group(1)
        if current_name != "TopicLesson":
            code = code.replace(f"class {current_name}(Scene):", "class TopicLesson(Scene):")
    elif "class TopicLesson(Scene):" not in code:
        # If no class found, wrap it? risky, better hope LLM follows rules
        pass

    return code

def _build_fallback_script(content: Dict) -> str:
    """Guaranteed simple fallback script if complex render fails."""
    title = content.get("topic_title", "Summary")
    summary = content.get("summary", "Lesson complete.")
    
    return f"""
from manim import *

class TopicLesson(Scene):
    def construct(self):
        self.camera.background_color = "#0a0a0f"
        t = Text("{title}", font_size=48, color="#6366f1")
        s = Text("{summary}", font_size=32, color=WHITE)
        s.next_to(t, DOWN)
        self.play(Write(t))
        self.play(FadeIn(s))
        self.wait(2)
        self.play(FadeOut(t), FadeOut(s))
"""

# ═════════════════════════════════════════════════════════════════════════
# STEP 4 — Render with Manim
# ═════════════════════════════════════════════════════════════════════════

def _render_manim(script_path, temp_dir):
    """
    Renders the Manim script using subprocess.
    Works around Windows path issues by finding the full manim.exe path.
    """
    import sys
    import os
    
    # ── FIND MANIM EXECUTABLE (Windows Fix) ──
    python_dir = os.path.dirname(sys.executable)
    manim_exe = os.path.join(python_dir, "manim.exe")
    
    if not os.path.exists(manim_exe):
        manim_exe = os.path.join(python_dir, "Scripts", "manim.exe")
    if not os.path.exists(manim_exe):
        manim_exe = "manim" # fallback to PATH
        
    print(f"[ManimGen] Using Manim at: {manim_exe}")

    cmd = [
        manim_exe,
        "-ql",
        "--format=mp4",
        "--media_dir", temp_dir,
        "-o", "output",
        script_path,
        "TopicLesson"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=temp_dir
        )
        
        if result.returncode == 0:
            print("[ManimGen]   Render Success.")
            return True
        else:
            print(f"[ManimGen] ERROR: Render Failed (Code {result.returncode})")
            print(f"[ManimGen] STDOUT: {result.stdout[-500:]}")
            print(f"[ManimGen] STDERR: {result.stderr[-500:]}")
            return False
    except Exception as e:
        print(f"[ManimGen] ERROR: Render Exception: {e}")
        return False

# ═════════════════════════════════════════════════════════════════════════
# STEP 5 — Add narration audio
# ═════════════════════════════════════════════════════════════════════════

def _add_narration(video_path: str, narration_text: str, temp_dir: str) -> str:
    """
    STEP 5: Convert narration to MP3 and merge with video using ffmpeg.
    """
    print("[ManimGen] STEP 5: Adding narration...")
    
    if not TTS_AVAILABLE:
        print("[ManimGen]   Skipping narration (gTTS not available).")
        return video_path
        
    audio_path = os.path.join(temp_dir, "narration.mp3")
    final_path = os.path.join(temp_dir, "final_lesson.mp4")
    
    try:
        # Generate MP3
        tts = gTTS(text=narration_text, lang="en")
        tts.save(audio_path)
        
        # Merge with ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            final_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return final_path
    except Exception as e:
        print(f"[ManimGen] WARNING: Narration merge failed: {e}. Returning silent video.")
        return video_path

def _find_rendered_video(temp_dir: str) -> str:
    """Search recursively for the final rendered MP4 file."""
    import glob

    # Search all mp4 files recursively
    all_mp4s = glob.glob(
        os.path.join(temp_dir, "**", "*.mp4"),
        recursive=True
    )

    # Filter out partial movie files
    final_videos = [
        f for f in all_mp4s
        if "partial_movie_files" not in f
    ]

    if not final_videos:
        return None

    # Return the largest file (most likely the final assembled video)
    best = max(final_videos, key=os.path.getsize)
    print(f"[ManimGen] Found final video: {best}")
    print(f"[ManimGen] File size: {os.path.getsize(best)} bytes")
    return best

# ═════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════

def generate_manim_video(
    topic: str,
    grade_level: str = "Grade 10",
    collection_name: str = "studybot_docs",
) -> Union[bytes, str]:
    """
    Complete pipeline to generate a professional Manim video.
    Returns raw bytes on success, or an error message on failure.
    """
    temp_dir = tempfile.mkdtemp(prefix="manim_gen_")
    
    try:
        # Step 1: Extract content
        content = extract_lesson_content(topic, grade_level, collection_name)
        if not content:
            return "Failed to extract lesson content from PDF."

        # Step 2: Generate script
        script_code = generate_manim_script(content)
        if not script_code:
            return "Failed to generate Manim script."

        # Step 3: Validate and fix code
        validated_code = _validate_and_fix_code(script_code)
        script_path = os.path.join(temp_dir, "topic_lesson.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(validated_code)

        # Step 4: Render
        success = _render_manim(script_path, temp_dir)
        
        # Retry with fallback if failed
        if not success:
            print("[ManimGen] WARNING: Retrying with simplified fallback script...")
            fallback_code = _build_fallback_script(content)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(fallback_code)
            success = _render_manim(script_path, temp_dir)

        if not success:
            return "Manim rendering failed after multiple attempts."

        # STEP 5 — Find video BEFORE any cleanup
        print("[ManimGen] STEP 5: Searching for rendered video...")
        video_file = _find_rendered_video(temp_dir)
        
        if not video_file:
            print("[ManimGen] ERROR: Video not found. Listing all files above.")
            return "Could not find rendered video file."

        print(f"[ManimGen] Found video: {video_file}")

        # STEP 6 — Add narration BEFORE reading bytes
        narration_text = content.get("narration", "")
        final_video_path = _add_narration(video_file, narration_text, temp_dir)
        print(f"[ManimGen] Final video: {final_video_path}")
        
        # STEP 7 — Read as bytes BEFORE cleanup
        if os.path.exists(final_video_path):
            with open(final_video_path, "rb") as f:
                video_bytes = f.read()
            print(f"[ManimGen] SUCCESS: Video generated ({len(video_bytes)} bytes)")
            return video_bytes
        else:
            return "Final video file not found."

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ManimGen] ERROR: {e}")
        return f"Video generation failed: {str(e)}"

    finally:
        # Step 8: Strict Cleanup ONLY after bytes are safely in memory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("[ManimGen] Cleaned up temp dir")

# Compatibility Alias
def generate_animation(topic: str) -> Union[bytes, str]:
    return generate_manim_video(topic)

if __name__ == "__main__":
    # Test block
    print("Testing Manim Generator...")
    # result = generate_manim_video("Binary Search", "Grade 10", "your_collection")
    # print(f"Result type: {type(result)}")
