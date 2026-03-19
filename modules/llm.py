"""
modules/llm.py
==============
Shared Groq LLM client for the StudyBot application.

This module initializes a single ChatGroq instance using settings from
config/settings.py. Every other module that needs the LLM imports
get_llm() from here — so the client is created once and reused.
"""

from langchain_groq import ChatGroq          # LangChain wrapper for Groq API
from config.settings import (                # Import config values (not hardcoded)
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)

# ── Module-level cache ──────────────────────────────────────────────────
# Holds the single ChatGroq instance so we don't recreate it on every call
_llm_instance = None


def get_llm() -> ChatGroq:
    """
    Returns a reusable ChatGroq client.

    On the first call it creates the instance using settings from
    config/settings.py. On subsequent calls it returns the cached instance.
    """
    global _llm_instance

    if _llm_instance is None:
        # Create the ChatGroq client with our config values
        _llm_instance = ChatGroq(
            api_key=GROQ_API_KEY,            # loaded from .env via settings
            model_name=LLM_MODEL_NAME,       # "llama3-70b-8192"
            temperature=LLM_TEMPERATURE,     # 0.3 — slightly creative
            max_tokens=LLM_MAX_TOKENS,       # 2048 token response limit
        )

    return _llm_instance


def test_connection() -> None:
    """
    Quick smoke test — sends 'Say hello' to Groq and prints the response.
    Run this directly to verify your API key works:
        python -m modules.llm
    """
    llm = get_llm()                          # get (or create) the client
    response = llm.invoke("Say hello")       # send a simple prompt
    print("✅ Groq responded:", response.content)


# ── Run test when executed directly ─────────────────────────────────────
if __name__ == "__main__":
    test_connection()
