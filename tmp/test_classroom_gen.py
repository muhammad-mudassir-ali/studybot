import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.getcwd())

from modules.manim_generator import generate_classroom_video

def main():
    load_dotenv()
    topic = "Photosynthesis"
    # Note: We need a collection that exists. I'll use "default" or check if one exists.
    # If no collection exists, the script should handle it gracefully.
    print(f"Testing classroom video generation for topic: {topic}")
    video_path = generate_classroom_video(topic, grade_level="5th Grade", collection_name="test_collection")
    print(f"Result: {video_path}")

if __name__ == "__main__":
    main()
