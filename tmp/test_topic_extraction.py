from graph.nodes import extract_topic

test_cases = [
    "Create a lesson about: Quantum Physics",
    "animate: Solar System",
    "teach me about Photosynthesis",
    "explain binary search",
    "Show me the structure of a cell",
    "Make a video about tectonic plates",
    "lesson about geometry",
    "Just a normal question about math"
]

for tc in test_cases:
    print(f"Input: '{tc}' -> Extracted: '{extract_topic(tc)}'")
