import streamlit as st
import os

# ════════════════════════════════════════════════════════════
# PAGE CONFIG — MUST BE FIRST STREAMlit CALL
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="StudyBot — Professional AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load env AFTER page config
from dotenv import load_dotenv
load_dotenv()

# ════════════════════════════════════════════════════════════
# LAZY IMPORTS 
# ════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="Loading AI models...")
def load_llm():
    from modules.llm import get_llm
    return get_llm()

@st.cache_resource(show_spinner="Loading embedding model...")
def load_embeddings():
    from modules.embeddings import get_embeddings
    return get_embeddings()

# ════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False
if "current_pdf_name" not in st.session_state:
    st.session_state.current_pdf_name = None
if "collection_name" not in st.session_state:
    st.session_state.collection_name = None
if "grade_num" not in st.session_state:
    st.session_state.grade_num = 10
if "grade_level" not in st.session_state:
    st.session_state.grade_level = "10th Grade"
if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""

# ════════════════════════════════════════════════════════════
# PROFESSIONAL CSS THEME
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── BASE THEME ── */
:root {
    --primary: #6366f1;
    --primary-hover: #4f46e5;
    --primary-light: rgba(99, 102, 241, 0.1);
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-tertiary: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* ── RESET & BASE ── */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    overflow-x: hidden !important;
}

/* ── HIDE STREAMLIT CHROME (Except toggle) ── */
#MainMenu, .stDeployButton, footer {
    display: none !important;
}

header, .stAppHeader {
    background: transparent !important;
}

/* ── SIDEBAR ── */
/* Sidebar Base Removed Duplication */

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
    visibility: visible !important;
    display: block !important;
    width: 339px !important; /* Standard 336px + 3px */
}

[data-testid="stSidebarContent"] {
    background: var(--bg-secondary) !important;
    overflow-x: hidden !important;
}

/* Sidebar flex container */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    padding: 0rem 0rem !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0.5rem !important;
}

/* ── LOGO AREA ── */
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 1.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}

.sidebar-logo-icon {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-hover) 100%);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: var(--shadow-md);
}

.sidebar-logo-text h1 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin: 0;
    line-height: 1.2;
}

.sidebar-logo-text span {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── SIDEBAR GRID FIX REMOVED ── */

/* ── GRADE SELECTOR ── */
.grade-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.75rem;
}

.grade-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 1.5rem;
}

/* ── BUTTONS ── */
/* Force compact square grade buttons */
[data-testid="stSidebar"] [data-testid="column"] .stButton,
[data-testid="stSidebar"] [data-testid="column"] .stButton > button {
    width: 48px !important; 
    height: 48px !important;
    max-width: 48px !important;
    max-height: 48px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 auto !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    font-size: 10px !important;
    line-height: normal !important;
    aspect-ratio: 1 / 1 !important;
}

/* Ensure the columns don't stretch vertically */
[data-testid="stSidebar"] [data-testid="column"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: auto !important;
}

.stButton > button {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border: 1px solid transparent !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 501 !important;
    font-size: 11px !important;
    padding: 0.4rem 0.8rem !important;
    transition: all 0.2s ease !important;
    height: auto !important;
    min-width: 0 !important;
    width: 100% !important;
}

/* Clear Chat button specific styling to make it small */
.clear-chat-container .stButton > button {
    font-size: 10px !important;
    padding: 0.2rem 0.5rem !important;
    width: auto !important;
    min-height: 0 !important;
    margin: 0 auto !important;
    display: block !important;
}

.stButton > button:hover {
    background: var(--primary-light) !important;
    border-color: var(--primary) !important;
    transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
    background: var(--primary) !important;
    color: white !important;
    box-shadow: var(--shadow-sm);
}

.stButton > button[kind="primary"]:hover {
    background: var(--primary-hover) !important;
}

/* ── UPLOAD AREA ── */
.upload-container {
    border: 2px dashed var(--border);
    border-radius: var(--radius-md);
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0;
    transition: all 0.2s ease;
}

.upload-container:hover {
    border-color: var(--primary);
    background: var(--primary-light);
}

[data-testid="stFileUploader"] label {
    color: white !important;
}

.uploaded-file {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.75rem;
    background: var(--primary-light);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: var(--radius-sm);
    color: white !important;
    font-size: 13px;
    font-weight: 500;
    margin-top: 0.75rem;
}

/* ── MAIN CONTENT ── */
.main-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 2rem;
    margin: -1rem -1rem 2rem -1rem;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0) 100%);
    border-bottom: 1px solid var(--border);
}

.header-title {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.5px;
}

.grade-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: var(--primary-light) !important; /* Explicit background */
    color: var(--primary);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── WELCOME SCREEN ── */
.welcome-container {
    max-width: 800px;
    margin: 1.5rem auto; /* Adjusted for laptop screens */
    text-align: center;
    padding: 0 2rem;
    max-height: calc(100vh - 200px); /* Limit height on small screens */
    overflow-y: auto; /* Allow internal scrolling if needed */
}

.welcome-icon {
    font-size: 48px; /* Reduced from 64px */
    margin-bottom: 1.5rem;
    filter: drop-shadow(0 10px 20px rgba(99, 102, 241, 0.3));
}

.welcome-title {
    font-size: 32px; /* Reduced from 42px */
    font-weight: 700;
    color: var(--text-primary) !important; /* Color fix */
    margin-bottom: 1rem;
    letter-spacing: -1px;
}

.welcome-subtitle {
    font-size: 15px; /* Reduced from 18px */
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 2rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
}

/* ── QUICK ACTIONS ── */
/* Quick actions wrapper removed as requested */

/* Action card classes removed as they are no longer used with the new button layout */

.action-desc {
    font-size: 13px;
    color: var(--text-secondary); /* Changed from var(--text-muted) for better visibility */
    line-height: 1.4;
}

/* ── CHAT MESSAGES ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.5rem 2rem !important;
}

[data-testid="stChatMessageContent"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.25rem !important;
    box-shadow: var(--shadow-sm);
    max-width: 80%;
    color: white !important; /* Force all chat text to white */
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-hover) 100%) !important;
    border-color: var(--primary) !important;
    color: white !important;
}

[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"], 
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
    background: transparent !important; /* Use base theme background */
    border: 1px solid var(--border);
    font-size: 18px;
    color: var(--text-primary) !important;
}

/* ── CHAT INPUT ── */
.stChatInputContainer {
    padding: 1rem 2rem 2rem 2rem !important;
}

.stChatInputContainer textarea {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.875rem 1rem !important;
    font-size: 15px !important;
    box-shadow: var(--shadow-sm);
}

.stChatInputContainer textarea::placeholder {
    color: var(--text-muted) !important;
}

.stChatInputContainer textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-light) !important;
}

/* ── SPINNER ── */
.stSpinner > div {
    border-color: var(--primary) !important;
}

/* ── ALERTS ── */
.stAlert {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

.stAlert[data-baseweb="notification"] {
    border-left: 4px solid var(--warning) !important;
}

/* ── DIVIDER ── */
hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
    background: var(--bg-tertiary);
    border-radius: 5px;
    border: 2px solid var(--bg-primary);
}

::-webkit-scrollbar-thumb:hover {
    background: var(--primary);
}
/* ── MORPHIC BOTTOM AREA ── */
[data-testid="stBottomBlockContainer"] {
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-top: 1px solid var(--border) !important;
}

/* Ensure the chat input container itself is transparent to show the background blur */
.stChatInputContainer {
    background-color: transparent !important;
    padding: 1rem 2rem 2rem 2rem !important;
}

/* Ensure the wrapper around the input is transparent */
[data-testid="stChatInput"] {
    background-color: transparent !important;
}

/* Chat input text area styling */
[data-testid="stChatInputTextArea"] {
    background-color: rgba(30, 41, 59, 1) !important;
    border: 1px solid var(--border) !important;
    color: white !important;
}

/* Remove any white spacing at the very bottom */
[data-testid="stBottomBlockContainer"] + div {
    background-color: transparent !important;
}

/* Global overflow fix */
html, body {
    overflow-x: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════
def grade_label(n):
    if n == 1: return "1st"
    if n == 2: return "2nd"
    if n == 3: return "3rd"
    return f"{n}th"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo" style="margin-bottom: 0.5rem;">
        <div class="sidebar-logo-icon">🎓</div>
        <div class="sidebar-logo-text">
            <h1>StudyBot</h1>
            <span>AI Tutor</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Collaborative Collapse Button Removed - Unreliable JS
    
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    
    # Grade Selector
    st.markdown('<div class="grade-label">Select Grade Level</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for i in range(1, 13):
        with cols[(i - 1) % 4]:
            active = st.session_state.grade_num == i
            if st.button(grade_label(i), key=f"gb_{i}", use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.grade_num = i
                st.session_state.grade_level = f"{grade_label(i)} Grade"
                st.rerun()
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # File Upload
    uploaded_file = st.file_uploader(
        "📄 Upload your textbook PDF", 
        type="pdf",
        help="Upload a PDF to enable personalized tutoring based on your material"
    )
    
    if uploaded_file:
        collection_name = uploaded_file.name.replace(" ", "_").lower()[:32]
        
        if st.session_state.current_pdf_name != uploaded_file.name:
            import tempfile
            tmp_path = None
            try:
                with st.spinner("Processing PDF..."):
                    from modules.pdf_loader import load_and_split_pdf, get_pdf_info
                    from modules.embeddings import store_embeddings
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    chunks = load_and_split_pdf(tmp_path)
                    info = get_pdf_info(chunks, uploaded_file.name)
                    
                    if store_embeddings(chunks, collection_name):
                        st.session_state.pdf_processed = True
                        st.session_state.current_pdf_name = uploaded_file.name
                        st.session_state.collection_name = collection_name
                        st.markdown(f"""
                        <div class="uploaded-file">
                            <span>✓</span>
                            <span>{uploaded_file.name[:25]}{'...' if len(uploaded_file.name) > 25 else ''}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Failed to process PDF")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            st.markdown(f"""
            <div class="uploaded-file">
                <span>✓</span>
                <span>{uploaded_file.name[:25]}{'...' if len(uploaded_file.name) > 25 else ''}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown('<div class="clear-chat-container">', unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat History", use_container_width=False, type="secondary"):
        st.session_state.messages = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# MAIN CONTENT
# ════════════════════════════════════════════════════════════
# Header
st.markdown(f"""
<div class="main-header">
    <div class="header-title">StudyBot Chat</div>
    <div class="grade-badge">
        <span>🎯</span>
        <span>{st.session_state.grade_level}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Welcome Screen or Chat History
# Logic: Show welcome only if no messages AND no prepopulated input is waiting
if not st.session_state.messages and not st.session_state.chat_input_value:
    # Welcome Screen
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">📚</div>
        <h1 class="welcome-title">How can I help you study today?</h1>
        <p class="welcome-subtitle">
            Upload your textbook and I'll create personalized lessons, answer questions, 
            and explain concepts at your grade level.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions (4 Columns Layout strictly using st.columns)
    if st.session_state.pdf_processed:
        col1, col2, col3, col4 = st.columns(4)
        
        actions = [
            ("❓", "Ask Question", "Get specific answers from your material"),
            ("💡", "Explain Topic", "Simple explanations of complex concepts"),
            ("🎥", "Find Videos", "Curated educational videos"),
            ("📖", "Create Lesson", "Generate animated lessons")
        ]
        
        for col, (icon, title, desc) in zip([col1, col2, col3, col4], actions):
            with col:
                # Target .stButton > button styling happens in CSS
                if st.button(f"{icon}\n\n**{title}**\n\n{desc}", 
                             key=f"qa_{title}", 
                             use_container_width=True):
                    prompts = {
                        "Ask Question": "I have a question about the material: ",
                        "Explain Topic": "Please explain this concept simply: ",
                        "Find Videos": "Find educational videos about: ",
                        "Create Lesson": "Create a lesson about: "
                    }
                    st.session_state.prefill_input = prompts[title]
                    st.rerun()
    else:
        st.info("👆 Upload a PDF in the sidebar to get started with personalized tutoring")
        
else:
    # Chat History
    for msg in st.session_state.messages:
        avatar = "👤" if msg["role"] == "user" else "🎓"
        with st.chat_message(msg["role"], avatar=avatar):
            msg_type = msg.get("type", "text")

            if msg_type == "video":
                # Inline video from bytes
                st.video(msg["content"])
                st.caption("📖 Lesson generated from your PDF")
            elif msg_type == "youtube":
                videos = msg.get("content", [])[:3]
                cols = st.columns(len(videos)) if videos else []
                for col, video in zip(cols, videos):
                    with col:
                        # Purple subtopic badge
                        if video.get("subtopic"):
                            st.markdown(
                                f'<span style="display:inline-block;background:#7c3aed;color:#ede9fe;'
                                f'font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;'
                                f'margin-bottom:8px;letter-spacing:0.3px;">📌 {video["subtopic"]}</span>',
                                unsafe_allow_html=True,
                            )
                        # Clickable thumbnail
                        if video.get("thumbnail"):
                            st.markdown(
                                f'<a href="{video["url"]}" target="_blank">'
                                f'<img src="{video["thumbnail"]}" style="width:100%;border-radius:8px;margin-bottom:6px;">'
                                f'</a>',
                                unsafe_allow_html=True,
                            )
                        # Bold title link
                        st.markdown(
                            f'<a href="{video["url"]}" target="_blank" style="font-weight:600;color:#a5b4fc;text-decoration:none;">'
                            f'{video["title"]}</a>',
                            unsafe_allow_html=True,
                        )
                        if video.get("channel"):
                            st.caption(f"📺 {video['channel']}")
                        if video.get("description"):
                            st.markdown(
                                f'<p style="font-size:12px;color:#94a3b8;margin-top:4px;">{video["description"][:120]}…</p>',
                                unsafe_allow_html=True,
                            )
            else:
                # Plain text / markdown
                if msg.get("content"):
                    st.markdown(msg["content"])

# ════════════════════════════════════════════════════════════
# CHAT INPUT
# ════════════════════════════════════════════════════════════
if st.session_state.pdf_processed:
    # Use session state to prepopulate input if needed
    prefill = st.session_state.pop("prefill_input", "")
    prompt = st.chat_input(prefill or "Ask your tutor anything...", 
                           key="chat_input")
    
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("Thinking..."):
                try:
                    from graph.workflow import graph
                    state = {
                        "question": prompt,
                        "collection_name": st.session_state.collection_name,
                        "grade_level": st.session_state.grade_level,
                        "context": [],
                        "intent": None,
                        "answer": None,
                        "video_bytes": None,
                        "youtube_results": None,
                    }
                    result = graph.invoke(state)

                    intent = result.get("intent")
                    answer = result.get("answer", "")
                    video_bytes = result.get("video_bytes")
                    youtube_results = result.get("youtube_results") or []

                    if intent in ["animate", "lesson"] and video_bytes:
                        # ── Video: play inline, store bytes in history ──
                        st.video(video_bytes)
                        st.caption("📖 Lesson generated from your PDF")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "video",
                            "content": video_bytes,
                        })
                    elif intent in ["animate", "lesson"] and answer:
                        # Text fallback when video generation failed
                        st.markdown(answer)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "text",
                            "content": answer,
                        })
                    elif intent == "youtube" and youtube_results:
                        cols = st.columns(len(youtube_results)) if youtube_results else []
                        for col, video in zip(cols, youtube_results):
                            with col:
                                # Purple subtopic badge
                                if video.get("subtopic"):
                                    st.markdown(
                                        f'<span style="display:inline-block;background:#7c3aed;color:#ede9fe;'
                                        f'font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;'
                                        f'margin-bottom:8px;letter-spacing:0.3px;">📌 {video["subtopic"]}</span>',
                                        unsafe_allow_html=True,
                                    )
                                # Clickable thumbnail
                                if video.get("thumbnail"):
                                    st.markdown(
                                        f'<a href="{video["url"]}" target="_blank">'
                                        f'<img src="{video["thumbnail"]}" style="width:100%;border-radius:8px;margin-bottom:6px;">'
                                        f'</a>',
                                        unsafe_allow_html=True,
                                    )
                                # Bold title link
                                st.markdown(
                                    f'<a href="{video["url"]}" target="_blank" style="font-weight:600;color:#a5b4fc;text-decoration:none;">'
                                    f'{video["title"]}</a>',
                                    unsafe_allow_html=True,
                                )
                                if video.get("channel"):
                                    st.caption(f"📺 {video['channel']}")
                                if video.get("description"):
                                    st.markdown(
                                        f'<p style="font-size:12px;color:#94a3b8;margin-top:4px;">{video["description"][:120]}…</p>',
                                        unsafe_allow_html=True,
                                    )
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "youtube",
                            "content": youtube_results,
                        })
                    else:
                        st.markdown(answer)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "text",
                            "content": answer,
                        })

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Try refreshing the page or uploading your PDF again")
        
        # Rerun to update chat history display
        st.rerun()
else:
    st.chat_input("Upload a PDF to start chatting...", disabled=True, key="disabled_input")