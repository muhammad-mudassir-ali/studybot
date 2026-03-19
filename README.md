# StudyBot — AI Powered Study Assistant

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=langchain&logoColor=white)

AI tutor that lets students upload PDF textbooks and learn through RAG Q&A, topic explanations, Manim educational videos, and YouTube recommendations.

## Features
* 📚 PDF Upload and RAG Q&A
* 💡 Topic Explanation at grade level
* 🎬 Manim Educational Video Generation
* 🎥 Smart YouTube Video Recommendations
* 🎓 Grade 1-12 Support

## Tech Stack
Python, LangGraph, Groq LLaMA3, ChromaDB, Manim, Streamlit, YouTube API

## Installation
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`

## Environment Variables
Create a `.env` file in the root directory (see `.env.example`):
```text
GROQ_API_KEY=your_groq_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
HF_TOKEN=your_huggingface_token_here
```

## How to run
```bash
streamlit run app.py
```

## License
MIT
