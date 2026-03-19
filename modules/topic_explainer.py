"""
modules/topic_explainer.py
==========================
Generates a simple explanation for a given topic and grade level,
grounded in facts retrieved from the vector database.
"""

from typing import List
from langchain_core.prompts import PromptTemplate
from modules.llm import get_llm
from modules.embeddings import query_embeddings

# Load the prompt template from the file
def load_prompt() -> PromptTemplate:
    with open("prompts/explain_prompt.txt", "r", encoding="utf-8") as f:
        template_text = f.read()
    
    return PromptTemplate(
        input_variables=["topic", "grade_level", "context"],
        template=template_text
    )

def explain_topic(topic: str, grade_level: str) -> str:
    """
    Searches ChromaDB for chunks related to the topic, merges them into context,
    and sends them to the LLM to get a simplified explanation.
    
    Args:
        topic (str): The subject to explain.
        grade_level (str): The target reading/comprehension level (e.g., "5th grade").
        
    Returns:
        str: The generated explanation.
    """
    # 1. Retrieve relevant chunks from the database
    # We query ChromaDB for the specific topic to find the best matched textbook context.
    chunks = query_embeddings(topic, top_k=3)
    
    # Extract the text content from the Document objects
    context_text = "\n\n".join([chunk.page_content for chunk in chunks]) if chunks else "No specific textbook context found."
    
    # 2. Get the LLM client
    llm = get_llm()
    
    # 3. Load the prompt template
    prompt = load_prompt()
    
    # 4. Create an LangChain LCEL pipeline (Prompt | LLM)
    chain = prompt | llm
    
    # 5. Execute the chain
    response = chain.invoke({
        "topic": topic,
        "grade_level": grade_level,
        "context": context_text
    })
    
    # Return the string content of the response
    return response.content

# ── Run test when executed directly ─────────────────────────────────────
if __name__ == "__main__":
    print("--- Testing Topic Explainer ---")
    test_topic = "Photosynthesis"
    test_grade = "5th Grade"
    print(f"Topic: {test_topic} | Grade Level: {test_grade}")
    print("\nExplanation:")
    print(explain_topic(test_topic, test_grade))
