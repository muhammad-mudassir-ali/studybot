"""
modules/slide_html_renderer.py
==============================
Converts a lesson plan slide (dict) into a 1280×720 PNG screenshot
by generating HTML via LLM and rendering it with Playwright.

Each slide goes through:
  1. LLM generates self-contained HTML for the slide
  2. Playwright headless Chromium loads the HTML
  3. Screenshot saved as PNG to temp directory
  4. PNG path returned to the video pipeline
"""

import os
import json
import tempfile
import re
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from modules.llm import get_llm
from modules.grade_themes import get_theme_css_block, get_grade_band


# ── Prompt loader ─────────────────────────────────────────────────────────

def _load_slide_prompt() -> PromptTemplate:
    with open("prompts/slide_html_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()
    return PromptTemplate(
        input_variables=["slide_json", "subject", "grade_level", "grade_band", "theme_css"],
        template=template
    )


# ── HTML cleaner ──────────────────────────────────────────────────────────

def _clean_html(raw: str) -> str:
    """
    Strips markdown fences if the LLM wrapped the HTML in ```html ... ```.
    Ensures the output starts with <!DOCTYPE html>.
    """
    clean = re.sub(r'```html\s*', '', raw)
    clean = re.sub(r'```\s*', '', clean)
    clean = clean.strip()

    # Find the actual start of the HTML document
    start = clean.lower().find('<!doctype')
    if start == -1:
        start = clean.lower().find('<html')
    if start > 0:
        clean = clean[start:]

    return clean


# ── Fallback slide HTML ───────────────────────────────────────────────────

def _fallback_slide_html(slide: dict, theme_css: str) -> str:
    """
    Generates a simple but clean fallback slide when the LLM call fails.
    Uses only inline styles — no dependencies.
    """
    heading  = slide.get("heading", "Lesson Slide")
    bullets  = slide.get("bullets", [])
    slide_type = slide.get("type", "concept")

    bullets_html = "".join(
        f'<div style="background:var(--surface);border-left:4px solid var(--accent);'
        f'padding:12px 16px;margin-bottom:10px;font-size:20px;border-radius:8px;">'
        f'{"①②③④"[i] if i < 4 else "•"} {b}</div>'
        for i, b in enumerate(bullets[:4])
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<style>
  :root {{ {theme_css} }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1280px; height: 720px; overflow: hidden;
    background: var(--bg-solid); font-family: var(--body-font);
    color: var(--text); display: flex; align-items: center;
    justify-content: center; padding: 48px;
  }}
  .card {{
    background: var(--surface); border-radius: var(--border-radius);
    padding: 40px 48px; width: 100%; box-shadow: var(--shadow);
  }}
  h1 {{ font-family: var(--heading-font); color: var(--accent);
        font-size: 36px; margin-bottom: 8px; }}
  .bar {{ width: 48px; height: 4px; background: var(--accent);
          margin-bottom: 24px; border-radius: 2px; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{heading}</h1>
    <div class="bar"></div>
    {bullets_html}
  </div>
</body>
</html>"""


# ── Playwright screenshotter ──────────────────────────────────────────────

def _screenshot_html(html: str, output_path: str) -> bool:
    """
    Saves HTML to a temp file and screenshots it at 1280×720 using Playwright.

    Returns True on success, False on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Renderer] ❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    # Write HTML to a temporary file
    tmp_html = output_path.replace(".png", ".html")
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            page = browser.new_page(
                viewport={"width": 1280, "height": 720}
            )
            # Load via file:// URL so relative resources work
            page.goto(f"file://{os.path.abspath(tmp_html)}")

            # Wait for animations to start (CSS keyframes begin immediately)
            # and for Chart.js to finish rendering if present
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(800)   # 800ms — enough for all CSS animations to settle

            page.screenshot(
                path=output_path,
                clip={"x": 0, "y": 0, "width": 1280, "height": 720},
                full_page=False
            )
            browser.close()

        # Clean up temp HTML file
        if os.path.exists(tmp_html):
            os.unlink(tmp_html)

        success = os.path.exists(output_path) and os.path.getsize(output_path) > 1000
        if success:
            print(f"[Renderer] ✅ Screenshot saved: {output_path}")
        else:
            print(f"[Renderer] ⚠️  Screenshot file too small — may be blank")
        return success

    except Exception as e:
        print(f"[Renderer] ❌ Playwright error: {e}")
        if os.path.exists(tmp_html):
            os.unlink(tmp_html)
        return False


# ── Per-slide hold frames ─────────────────────────────────────────────────

def _duplicate_frame(png_path: str, output_dir: str, slide_idx: int, count: int) -> list[str]:
    """
    Copies a single PNG frame `count` times to simulate the slide
    being held for `count` video frames. Returns list of paths.

    At 24fps:  5 seconds = 120 copies,  4 seconds = 96 copies.
    We use symlinks when possible for speed; fall back to copies.
    """
    import shutil
    paths = []
    for i in range(count):
        dest = os.path.join(output_dir, f"frame_{slide_idx:03d}_{i:04d}.png")
        try:
            if not os.path.exists(dest):
                os.symlink(os.path.abspath(png_path), dest)
        except (OSError, NotImplementedError):
            # Windows or cross-device — fall back to copy
            shutil.copy2(png_path, dest)
        paths.append(dest)
    return paths


# ── Main entry point ──────────────────────────────────────────────────────

def render_slide_to_png(
    slide: dict,
    subject: str,
    grade_level: str,
    output_dir: str,
    slide_idx: int,
    hold_seconds: float = 5.0,
    fps: int = 24
) -> list[str]:
    """
    Renders one lesson plan slide to a PNG and duplicates it for hold_seconds
    worth of video frames.

    Args:
        slide       : Single slide dict from the lesson plan JSON.
        subject     : e.g. "biology" — controls diagram colour.
        grade_level : e.g. "7th Grade" — selects theme and font sizes.
        output_dir  : Directory to write PNG frames into.
        slide_idx   : Slide index (for filename ordering).
        hold_seconds: How long this slide shows in the final video.
        fps         : Frames per second of the output video.

    Returns:
        list[str]: Ordered list of PNG frame paths for this slide.
    """
    print(f"[Renderer] Slide {slide_idx + 1} — type: {slide.get('type')} | "
          f"heading: {slide.get('heading', '')[:40]}")

    # ── Step 1: Build prompt inputs ──────────────────────────────────────
    theme_css  = get_theme_css_block(grade_level)
    grade_band = get_grade_band(grade_level)

    # Convert slide dict to clean JSON string for the prompt
    slide_json_str = json.dumps(slide, indent=2, ensure_ascii=False)

    # ── Step 2: Generate HTML via LLM ────────────────────────────────────
    html = None
    try:
        llm    = get_llm()
        prompt = _load_slide_prompt()
        chain  = prompt | llm

        print(f"[Renderer]   → Calling LLM for HTML generation …")
        response = chain.invoke({
            "slide_json":  slide_json_str,
            "subject":     subject,
            "grade_level": grade_level,
            "grade_band":  grade_band,
            "theme_css":   theme_css,
        })
        raw_html = response.content
        html     = _clean_html(raw_html)

        # Basic sanity check
        if len(html) < 200 or "<!doctype" not in html.lower():
            print(f"[Renderer]   ⚠️  LLM returned suspicious HTML (len={len(html)}) — using fallback")
            html = None

    except Exception as e:
        print(f"[Renderer]   ❌ LLM call failed: {e} — using fallback HTML")
        html = None

    # Use fallback if LLM failed
    if html is None:
        html = _fallback_slide_html(slide, get_theme_css_block(grade_level))
        print(f"[Renderer]   → Using fallback slide HTML")

    # ── Step 3: Screenshot with Playwright ───────────────────────────────
    png_path = os.path.join(output_dir, f"slide_{slide_idx:03d}.png")
    success  = _screenshot_html(html, png_path)

    if not success:
        # If Playwright failed, generate a plain white PNG using Pillow as last resort
        print(f"[Renderer]   ⚠️  Playwright failed — generating Pillow fallback PNG")
        png_path = _pillow_fallback_png(slide, png_path)

    # ── Step 4: Duplicate frame for hold duration ─────────────────────────
    frame_count = int(hold_seconds * fps)
    frames      = _duplicate_frame(png_path, output_dir, slide_idx, frame_count)
    print(f"[Renderer]   → {frame_count} frames generated ({hold_seconds}s @ {fps}fps)")
    return frames


def _pillow_fallback_png(slide: dict, output_path: str) -> str:
    """
    Absolute last resort: renders a plain text slide using Pillow.
    Only used if both LLM HTML generation AND Playwright fail.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        img  = Image.new("RGB", (1280, 720), (30, 30, 50))
        draw = ImageDraw.Draw(img)

        heading = slide.get("heading", "Lesson")
        bullets = slide.get("bullets", [])

        # Try to load a system font, fall back to default
        try:
            font_h = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except Exception:
            font_h = font_b = ImageFont.load_default()

        draw.text((80, 80),  heading, fill=(100, 200, 255), font=font_h)
        draw.rectangle([(80, 146), (180, 152)], fill=(100, 200, 255))

        y = 180
        for i, bullet in enumerate(bullets[:4]):
            draw.text((80, y), f"  {bullet}", fill=(220, 230, 240), font=font_b)
            y += 52

        img.save(output_path, format="PNG")
        print(f"[Renderer]   → Pillow fallback PNG saved: {output_path}")
    except Exception as e:
        print(f"[Renderer]   ❌ Even Pillow fallback failed: {e}")

    return output_path
