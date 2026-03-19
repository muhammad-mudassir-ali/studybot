"""
modules/grade_themes.py
=======================
CSS theme definitions for each grade band (1-3, 4-6, 7-9, 10-12).
Each theme defines CSS custom properties that the HTML slide prompt injects
directly into the generated slide, ensuring consistent visual identity
and age-appropriate aesthetics across all slides in a lesson.
"""

from dataclasses import dataclass


@dataclass
class GradeTheme:
    name: str
    grade_band: str          # "primary" | "elementary" | "middle" | "high"
    css_variables: str       # injected verbatim into the slide's :root {}
    subject_emoji: dict      # subject → emoji for title slides
    description: str         # human-readable description for debugging


# ── PRIMARY (Grades 1–3) ─────────────────────────────────────────────────
# Bright, playful, chunky. Maximum readability. Cartoon-like shapes.
PRIMARY_THEME = GradeTheme(
    name="Bright Explorer",
    grade_band="primary",
    css_variables="""
        --bg: linear-gradient(160deg, #fff9f0 0%, #fff0f9 100%);
        --bg-solid: #fff9f0;
        --surface: #ffffff;
        --surface-alt: #fff3e0;
        --accent: #ff6b35;
        --accent-dark: #e85520;
        --accent-alt: #7bc67e;
        --text: #2d2d2d;
        --text-muted: #777777;
        --border: #ffe0cc;
        --border-radius: 20px;
        --heading-font: 'Comic Sans MS', 'Chalkboard SE', 'Bradley Hand', cursive;
        --body-font: 'Arial Rounded MT Bold', 'Nunito', 'Trebuchet MS', sans-serif;
        --shadow: 0 6px 24px rgba(255,107,53,0.15);
        --bullet-prefix: '★ ';
    """,
    subject_emoji={
        "biology": "🌿", "chemistry": "🧪", "physics": "🌈",
        "math": "🔢", "history": "🏰", "geography": "🌍",
        "literature": "📖", "computer_science": "🤖", "general": "⭐"
    },
    description="Grades 1–3: Warm, playful, high-contrast with rounded shapes"
)

# ── ELEMENTARY (Grades 4–6) ──────────────────────────────────────────────
# Friendly but structured. Introduction to real diagrams. Colour-coded.
ELEMENTARY_THEME = GradeTheme(
    name="Curious Learner",
    grade_band="elementary",
    css_variables="""
        --bg: linear-gradient(160deg, #f0f4ff 0%, #f5f0ff 100%);
        --bg-solid: #f0f4ff;
        --surface: #ffffff;
        --surface-alt: #eef2ff;
        --accent: #4361ee;
        --accent-dark: #3451d1;
        --accent-alt: #7209b7;
        --text: #1a1a2e;
        --text-muted: #6b7280;
        --border: #c7d2fe;
        --border-radius: 14px;
        --heading-font: 'Trebuchet MS', 'Segoe UI', 'Helvetica Neue', sans-serif;
        --body-font: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        --shadow: 0 4px 20px rgba(67,97,238,0.12);
        --bullet-prefix: '→ ';
    """,
    subject_emoji={
        "biology": "🔬", "chemistry": "⚗️", "physics": "⚡",
        "math": "📐", "history": "📜", "geography": "🗺️",
        "literature": "📚", "computer_science": "💻", "general": "🎓"
    },
    description="Grades 4–6: Blue/purple palette, structured layout, friendly shapes"
)

# ── MIDDLE SCHOOL (Grades 7–9) ───────────────────────────────────────────
# Confident, modern, slightly edgy. Dense but clean. Tech-forward feel.
MIDDLE_THEME = GradeTheme(
    name="Sharp Thinker",
    grade_band="middle",
    css_variables="""
        --bg: linear-gradient(160deg, #0f172a 0%, #1e1b4b 100%);
        --bg-solid: #0f172a;
        --surface: #1e293b;
        --surface-alt: #334155;
        --accent: #38bdf8;
        --accent-dark: #0ea5e9;
        --accent-alt: #a78bfa;
        --text: #f1f5f9;
        --text-muted: #94a3b8;
        --border: #334155;
        --border-radius: 10px;
        --heading-font: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
        --body-font: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', sans-serif;
        --shadow: 0 4px 24px rgba(56,189,248,0.15);
        --bullet-prefix: '▸ ';
    """,
    subject_emoji={
        "biology": "🧬", "chemistry": "🔬", "physics": "⚛️",
        "math": "∑", "history": "🗿", "geography": "🌐",
        "literature": "✍️", "computer_science": "⌨️", "general": "💡"
    },
    description="Grades 7–9: Dark mode, cyan accent, modern tech aesthetic"
)

# ── HIGH SCHOOL (Grades 10–12) ───────────────────────────────────────────
# Professional, minimal, academic. Data-dense. Clean typography.
HIGH_THEME = GradeTheme(
    name="Academic Pro",
    grade_band="high",
    css_variables="""
        --bg: linear-gradient(160deg, #fafafa 0%, #f0f0f5 100%);
        --bg-solid: #fafafa;
        --surface: #ffffff;
        --surface-alt: #f5f5f7;
        --accent: #1d4ed8;
        --accent-dark: #1e40af;
        --accent-alt: #059669;
        --text: #111827;
        --text-muted: #6b7280;
        --border: #e5e7eb;
        --border-radius: 8px;
        --heading-font: 'Georgia', 'Times New Roman', serif;
        --body-font: 'Helvetica Neue', Arial, 'Segoe UI', sans-serif;
        --shadow: 0 2px 16px rgba(0,0,0,0.08);
        --bullet-prefix: '• ';
    """,
    subject_emoji={
        "biology": "🧫", "chemistry": "⚗️", "physics": "🔭",
        "math": "∫", "history": "📰", "geography": "🗾",
        "literature": "🖊️", "computer_science": "🖥️", "general": "🎓"
    },
    description="Grades 10–12: Clean academic look, serif headings, professional"
)


# ── Grade-to-theme lookup ─────────────────────────────────────────────────

_GRADE_MAP: dict[int, GradeTheme] = {
    1: PRIMARY_THEME,  2: PRIMARY_THEME,  3: PRIMARY_THEME,
    4: ELEMENTARY_THEME, 5: ELEMENTARY_THEME, 6: ELEMENTARY_THEME,
    7: MIDDLE_THEME,   8: MIDDLE_THEME,   9: MIDDLE_THEME,
    10: HIGH_THEME,    11: HIGH_THEME,    12: HIGH_THEME,
}


def get_theme(grade_level: str) -> GradeTheme:
    """
    Returns the correct GradeTheme for a grade level string.

    Accepts formats like "5th Grade", "Grade 7", "10", "3rd Grade", "11th Grade".
    Falls back to ELEMENTARY_THEME if the grade cannot be parsed.

    Args:
        grade_level: Grade string from Streamlit session state.

    Returns:
        GradeTheme dataclass with CSS variables and metadata.
    """
    import re
    match = re.search(r'\d+', str(grade_level))
    if match:
        grade_num = int(match.group())
        grade_num = max(1, min(12, grade_num))   # clamp to 1–12
        return _GRADE_MAP[grade_num]

    print(f"[Themes] Could not parse grade from '{grade_level}' — using elementary theme")
    return ELEMENTARY_THEME


def get_theme_css_block(grade_level: str) -> str:
    """
    Returns a complete CSS :root { } block ready to inject into a <style> tag.

    Usage in slide HTML:
        <style>
            :root { {theme_css} }
            /* ... rest of slide CSS ... */
        </style>
    """
    theme = get_theme(grade_level)
    return f":root {{\n{theme.css_variables}\n}}"


def get_subject_emoji(grade_level: str, subject: str) -> str:
    """Returns the appropriate emoji for a subject at the given grade level."""
    theme = get_theme(grade_level)
    return theme.subject_emoji.get(subject.lower(), "🎓")


def get_subject_emoji(grade_level: str, subject: str) -> str:
    """Returns the appropriate emoji for a subject at the given grade level."""
    theme = get_theme(grade_level)
    return theme.subject_emoji.get(subject.lower(), "🎓")


def get_grade_band(grade_level: str) -> str:
    """Returns the grade band string: 'primary', 'elementary', 'middle', or 'high'."""
    return get_theme(grade_level).grade_band


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for g in ["1st Grade", "4th Grade", "7th Grade", "10th Grade", "12th Grade"]:
        theme = get_theme(g)
        print(f"{g:15} → {theme.name:20} ({theme.grade_band})")
