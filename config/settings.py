"""
config/settings.py
==================
Central configuration for the entire StudyBot application.

All magic numbers, model names, file paths, and tuneable parameters live
here so they can be changed in one place without hunting through modules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file so API keys are available via os.getenv() ────────────
load_dotenv()

# ── Project Paths ───────────────────────────────────────────────────────
# ROOT_DIR points to the top-level project folder (g:\my-studybot)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Where ChromaDB stores its persistent vector database on disk
CHROMA_PERSIST_DIR = str(ROOT_DIR / "data" / "chroma_store")

# Where Manim will output rendered videos
MEDIA_DIR = str(ROOT_DIR / "media")

# Directory that holds prompt template files
PROMPTS_DIR = str(ROOT_DIR / "prompts")

# ── API Keys ────────────────────────────────────────────────────────────
# Groq provides free LLM inference — key is required
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# YouTube Data API v3 key — needed for video recommendations
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ── LLM Settings ────────────────────────────────────────────────────────
# Model hosted on Groq's infrastructure (LLaMA 3.3 70B, versatile)
LLM_MODEL_NAME = "llama-3.3-70b-versatile"

# Temperature controls randomness: 0 = deterministic, 1 = creative
LLM_TEMPERATURE = 0.3

# Maximum tokens the LLM can return in a single response
LLM_MAX_TOKENS = 2048

# ── Embedding Settings ──────────────────────────────────────────────────
# HuggingFace model used to create text embeddings (runs locally, ~80 MB)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ── PDF Chunking Settings ──────────────────────────────────────────────
# Number of characters per text chunk when splitting a PDF
CHUNK_SIZE = 1000

# Overlap between consecutive chunks to preserve context at boundaries
CHUNK_OVERLAP = 200

# ── ChromaDB Settings ──────────────────────────────────────────────────
# Name of the default collection inside ChromaDB
CHROMA_COLLECTION_NAME = "studybot_docs"

# ── YouTube Settings ───────────────────────────────────────────────────
# Maximum number of YouTube video results to return per query
YOUTUBE_MAX_RESULTS = 5
