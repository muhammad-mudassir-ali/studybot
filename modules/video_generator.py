"""
modules/video_generator.py
==========================
Full pipeline orchestrator:
  PDF chunks → LLM lesson plan → HTML slides → Playwright PNGs → gTTS audio → ffmpeg MP4

Public API:
    from modules.video_generator import generate_video
    path = generate_video(topic, collection_name, grade_level)
    # Returns: MP4 path string, or plain-text explanation on failure
"""

import os
import json
import re
import subprocess
import tempfile
from langchain_core.prompts import PromptTemplate

from modules.embeddings import query_embeddings
from modules.llm import get_llm
from modules.grade_themes import get_theme, get_grade_band
from modules.slide_html_renderer import render_slide_to_png

# ── TTS availability check ────────────────────────────────────────────────
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[VideoGen] ⚠️  gTTS not installed — videos will be silent. pip install gtts")

FPS = 24


# ── Helpers ───────────────────────────────────────────────────────────────

def _load_lesson_prompt() -> PromptTemplate:
    with open("prompts/lesson_plan_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()
    return PromptTemplate(
        input_variables=["topic", "context", "grade_level"],
        template=template
    )


def _build_context(chunks: list, max_chunks: int = 8) -> str:
    if not chunks:
        return "No relevant textbook content found for this topic."
    parts = []
    for i, chunk in enumerate(chunks[:max_chunks], 1):
        text   = chunk.page_content.strip()
        source = chunk.metadata.get("source", f"excerpt {i}")
        parts.append(f"[Excerpt {i} — {source}]\n{text}")
    context = "\n\n".join(parts)
    print(f"[VideoGen] Context: {len(chunks[:max_chunks])} chunks, {len(context)} chars")
    return context


def _parse_lesson_plan(raw: str) -> dict | None:
    """Robustly extracts and parses the JSON lesson plan from LLM output."""
    clean = re.sub(r'```json\s*', '', raw)
    clean = re.sub(r'```\s*', '', clean).strip()
    start = clean.find("{")
    end   = clean.rfind("}") + 1
    if start == -1 or end == 0:
        print("[VideoGen] ❌ No JSON object found in LLM response")
        return None
    try:
        plan = json.loads(clean[start:end])
        print(f"[VideoGen] Lesson plan: {len(plan.get('slides', []))} slides, "
              f"subject={plan.get('subject')}, band={plan.get('grade_band')}")
        return plan
    except json.JSONDecodeError as e:
        print(f"[VideoGen] ❌ JSON parse error: {e}")
        return None


def _text_fallback(topic: str, context: str, grade_level: str) -> str:
    """Plain-text explanation when the full video pipeline fails."""
    print("[VideoGen] Generating plain-text fallback …")
    try:
        llm    = get_llm()
        prompt = (
            f"You are a helpful tutor for a {grade_level} student.\n"
            f"Using only the textbook content below, explain '{topic}' clearly "
            f"in 5–7 sentences appropriate for {grade_level}.\n\n"
            f"TEXTBOOK CONTENT:\n{context}"
        )
        return llm.invoke(prompt).content.strip()
    except Exception as e:
        print(f"[VideoGen] Fallback LLM also failed: {e}")
        return (
            f"I wasn't able to generate a video for '{topic}'. "
            f"Please try rephrasing your question or check that your PDF "
            f"contains relevant content on this topic."
        )


# ── TTS audio generator ───────────────────────────────────────────────────

def _generate_audio_for_slide(narration: str, path: str) -> float:
    """
    Generates an MP3 narration file for one slide.
    Returns the audio duration in seconds (0.0 if TTS unavailable or failed).
    """
    if not TTS_AVAILABLE or not narration.strip():
        return 0.0
    try:
        gTTS(text=narration, lang="en", slow=False).save(path)
        if not os.path.exists(path) or os.path.getsize(path) < 500:
            return 0.0
        # Probe duration with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        print(f"[VideoGen]   TTS audio: {duration:.1f}s")
        return duration
    except Exception as e:
        print(f"[VideoGen]   TTS failed: {e}")
        return 0.0


# ── ffmpeg video assembler ────────────────────────────────────────────────

def _check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _assemble_video(
    frame_lists:   list[list[str]],
    audio_paths:   list[str],
    slide_durations: list[float],
    output_path:   str,
    temp_dir:      str
) -> bool:
    """
    Assembles all slide frame sequences and audio tracks into a final MP4.

    Strategy:
      1. Build a per-slide video clip from PNG frames (using ffmpeg image2 input)
      2. Attach the per-slide audio clip (or silence) to each clip
      3. Concatenate all clips with a fast concat demuxer
      4. Produce final MP4 with H.264 + AAC

    Returns True on success.
    """
    if not _check_ffmpeg():
        print("[VideoGen] ❌ ffmpeg not found. Install from https://ffmpeg.org/")
        return False

    clip_paths = []

    # ── Build per-slide video+audio clip ─────────────────────────────────
    for i, (frames, audio, duration) in enumerate(
        zip(frame_lists, audio_paths, slide_durations)
    ):
        if not frames:
            continue

        clip_path = os.path.join(temp_dir, f"clip_{i:03d}.mp4")

        # Write a concat list file pointing to the PNG frames
        # (faster than -framerate with glob for variable counts)
        list_file = os.path.join(temp_dir, f"frames_{i:03d}.txt")
        with open(list_file, "w") as f:
            for frame in frames:
                f.write(f"file '{os.path.abspath(frame)}'\n")
                f.write(f"duration {1/FPS:.6f}\n")

        has_audio = audio and os.path.exists(audio) and os.path.getsize(audio) > 500

        if has_audio:
            # Pad video to match audio duration + 0.5s tail
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", list_file,
                "-i", audio,
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                "-t", str(duration + 0.5),
                clip_path
            ]
        else:
            # Silent clip: generate silent audio track
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", list_file,
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                clip_path
            ]

        print(f"[VideoGen]   Building clip {i+1}/{len(frame_lists)}: {duration:.1f}s …")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[VideoGen]   ⚠️  Clip {i} failed:\n{result.stderr[-800:]}")
            continue
        clip_paths.append(clip_path)

    if not clip_paths:
        print("[VideoGen] ❌ No clips produced — cannot assemble video")
        return False

    # ── Concatenate all clips ─────────────────────────────────────────────
    concat_list = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    print(f"[VideoGen] Concatenating {len(clip_paths)} clips → {output_path}")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",   # web-optimised: moov atom at front
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[VideoGen] ❌ Final concat failed:\n{result.stderr[-1200:]}")
        return False

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[VideoGen] ✅ Video ready: {output_path} ({size_mb:.1f} MB)")
    return True


# ── Slide duration calculator ─────────────────────────────────────────────

def _calculate_slide_duration(slide: dict, audio_duration: float) -> float:
    """
    Returns how long (in seconds) a slide should appear.
    Rules:
      - If audio exists: audio_duration + 1.2s padding
      - Else estimate from narration word count at ~2.8 words/sec
      - Title / summary slides get a minimum of 5s
      - Concept slides get a minimum of 6s
      - Maximum 15s per slide
    """
    slide_type = slide.get("type", "concept")
    min_dur    = 5.0 if slide_type == "title" else 6.0

    if audio_duration > 0:
        duration = audio_duration + 1.2
    else:
        narration  = slide.get("narration", "")
        word_count = len(narration.split())
        duration   = max(word_count / 2.8 + 1.5, min_dur)

    return min(duration, 15.0)


# ── Main entry point ──────────────────────────────────────────────────────

def generate_video(
    topic: str,
    collection_name: str,
    grade_level: str = "5th Grade"
) -> str:
    """
    Full pipeline: PDF → lesson plan → HTML slides → PNGs → audio → MP4.

    Args:
        topic           : The concept to teach (e.g. "photosynthesis").
        collection_name : ChromaDB collection name for the uploaded PDF.
        grade_level     : e.g. "7th Grade" — controls theme + language.

    Returns:
        str: Absolute path to the MP4, or a plain-text explanation on failure.
    """
    print(f"\n[VideoGen] ══════════════════════════════════════════")
    print(f"[VideoGen] Generating video: '{topic}' | {grade_level}")
    print(f"[VideoGen] ══════════════════════════════════════════")

    # ── Step 1: Retrieve PDF context ─────────────────────────────────────
    print("[VideoGen] Step 1 — Querying ChromaDB …")
    chunks  = query_embeddings(topic, collection_name=collection_name, top_k=10)
    context = _build_context(chunks)

    # ── Step 2: Generate lesson plan ─────────────────────────────────────
    print("[VideoGen] Step 2 — Generating lesson plan …")
    try:
        raw  = (
            _load_lesson_prompt()
            | get_llm()
        ).invoke({
            "topic":       topic,
            "context":     context,
            "grade_level": grade_level,
        }).content
    except Exception as e:
        print(f"[VideoGen] LLM lesson plan call failed: {e}")
        return _text_fallback(topic, context, grade_level)

    plan = _parse_lesson_plan(raw)
    if not plan or not plan.get("slides"):
        print("[VideoGen] ❌ Invalid lesson plan")
        return _text_fallback(topic, context, grade_level)

    subject    = plan.get("subject", "general")
    slides     = plan["slides"]
    grade_band = get_grade_band(grade_level)
    print(f"[VideoGen] Plan ready — {len(slides)} slides | subject={subject} | band={grade_band}")

    # ── Step 3: Render slides + generate audio ────────────────────────────
    print("[VideoGen] Step 3 — Rendering slides and generating audio …")
    temp_dir = tempfile.mkdtemp(prefix="studybot_")
    print(f"[VideoGen] Working directory: {temp_dir}")

    frame_lists      = []
    audio_paths      = []
    slide_durations  = []

    for idx, slide in enumerate(slides):
        print(f"\n[VideoGen] ── Slide {idx + 1}/{len(slides)} "
              f"({slide.get('type')}: {slide.get('heading', '')[:36]}) ──")

        # Generate TTS audio first to know the duration
        narration   = slide.get("narration", "")
        audio_path  = os.path.join(temp_dir, f"audio_{idx:03d}.mp3")
        audio_dur   = _generate_audio_for_slide(narration, audio_path)
        duration    = _calculate_slide_duration(slide, audio_dur)

        # Render slide PNG and duplicate to fill duration
        try:
            frames = render_slide_to_png(
                slide       = slide,
                subject     = subject,
                grade_level = grade_level,
                output_dir  = temp_dir,
                slide_idx   = idx,
                hold_seconds= duration,
                fps         = FPS
            )
        except Exception as e:
            print(f"[VideoGen] ⚠️  Slide {idx + 1} render failed: {e}")
            frames = []

        frame_lists.append(frames)
        audio_paths.append(audio_path if audio_dur > 0 else None)
        slide_durations.append(duration)

        total_so_far = sum(slide_durations)
        print(f"[VideoGen]   Duration: {duration:.1f}s | Running total: {total_so_far:.1f}s")

    # ── Step 4: Assemble MP4 ──────────────────────────────────────────────
    print(f"\n[VideoGen] Step 4 — Assembling MP4 …")
    output_path = os.path.join(temp_dir, "lesson_video.mp4")
    success     = _assemble_video(
        frame_lists      = frame_lists,
        audio_paths      = audio_paths,
        slide_durations  = slide_durations,
        output_path      = output_path,
        temp_dir         = temp_dir
    )

    if success:
        total = sum(slide_durations)
        print(f"[VideoGen] ✅ Complete — {total:.0f}s video at {output_path}")
        return output_path
    else:
        print("[VideoGen] ❌ Assembly failed — returning text fallback")
        return _text_fallback(topic, context, grade_level)
