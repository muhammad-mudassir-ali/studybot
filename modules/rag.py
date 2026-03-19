"""
modules/rag.py
==============
Core RAG (Retrieval-Augmented Generation) logic.
Combines retrieved document chunks with a system prompt to answer questions.
"""

from langchain_core.prompts import PromptTemplate
from modules.llm import get_llm
from typing import List
from langchain_core.documents import Document

def load_rag_prompt() -> PromptTemplate:
    """Loads the system prompt from the prompts directory."""
    with open("prompts/rag_prompt.txt", "r", encoding="utf-8") as f:
        template_text = f.read()
    
    return PromptTemplate(
        input_variables=["context", "question"],
        template=template_text
    )

def get_rag_answer(question: str, context: List[Document]) -> str:
    """
    Takes a question and a list of context documents (chunks),
    formats them, and calls the LLM to get an answer.
    """
    # 1. Format context into a single string
    context_text = "\n\n".join([doc.page_content for doc in context]) if context else "No context available."
    
    print(f"DEBUG: Final context length sent to LLM: {len(context_text)} chars")
    
    # 2. Setup LLM and Prompt
    llm = get_llm()
    prompt = load_rag_prompt()
    
    # 3. Build the chain (Simple LCEL: prompt | llm)
    chain = prompt | llm
    
    # 4. Invoke and return content
    response = chain.invoke({
        "context": context_text,
        "question": question
    })
    
    return response.content
