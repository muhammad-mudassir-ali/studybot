"""
graph/workflow.py
=================
Wires the nodes together into a LangGraph StateGraph.
Handles conditional routing based on intent.
"""

from langgraph.graph import StateGraph, END
from graph.state import StudyBotState
from graph.nodes import (
    classify_intent,
    retrieve_chunks,
    qa_answer,
    explain_node,
    recommend_youtube_node,
    animate_node,
    generate_lesson_node
)

def router(state: StudyBotState):
    """
    Decision function to route the graph based on the intent.
    """
    return state["intent"]

def create_study_bot_graph():
    """
    Builds and compiles the StudyBot workflow graph.
    """
    # 1. Initialize the StateGraph with our StudyBotState
    workflow = StateGraph(StudyBotState)
    
    # 2. Add Nodes
    workflow.add_node("classify", classify_intent)
    workflow.add_node("retrieve", retrieve_chunks)
    workflow.add_node("qa_answer", qa_answer)
    workflow.add_node("explain", explain_node)
    workflow.add_node("youtube", recommend_youtube_node)
    workflow.add_node("animate", animate_node)
    workflow.add_node("lesson", generate_lesson_node)
    
    # 3. Define Edges (Start at classify)
    workflow.set_entry_point("classify")
    
    # 4. Define Conditional Edges from 'classify'
    workflow.add_conditional_edges(
        "classify",
        router,
        {
            "qa": "retrieve",
            "explain": "explain",
            "youtube": "youtube",
            "animate": "animate",
            "lesson": "lesson"
        }
    )
    
    # 5. Define End Edges
    workflow.add_edge("retrieve", "qa_answer")
    workflow.add_edge("qa_answer", END)
    workflow.add_edge("explain", END)
    workflow.add_edge("youtube", END)
    workflow.add_edge("animate", END)
    workflow.add_edge("lesson", END)
    
    # 6. Compile the graph
    app = workflow.compile()
    return app

# Initialize the graph globally for easy access
graph = create_study_bot_graph()

# ── Simple test if run directly ─────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("--- Testing Graph Flow ---")
    test_input = {"question": "What is Photosynthesis?", "context": [], "intent": None, "answer": None}
    
    # Execute the graph
    for output in graph.stream(test_input):
        for key, value in output.items():
            print(f"Finished Node: {key}")
            if "intent" in value:
                print(f"Intent classified as: {value['intent']}")
            if "answer" in value:
                print(f"Answer generated!")
