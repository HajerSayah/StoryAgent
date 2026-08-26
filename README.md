# 🎭 Multi-Agent Interactive Storytelling System

AI-powered storytelling system using **LangGraph** and **Groq** with multiple specialized agents working together.

## Architecture

```
                    ┌─────────────────┐
                    │  Orchestrator   │ ← Plans and delegates tasks
                    │     Agent       │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Story Writer   │ │  Image Agent    │ │  Audio Agent    │
│     Agent       │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Features
- **Orchestrator Agent**: Plans each scene and decides which agents to activate
- **Story Writer Agent**: Generates narration text and interactive choices
- **Image Agent**: Generates scene illustrations using Pollinations.ai
- **Audio Agent**: Generates audio narration using gTTS
- 7 genres: Romance, Comedy, Action, Horror, Fantasy, Sci-Fi, Drama
- Interactive choices (A/B) that affect the story
- Safety guardrails for content filtering

## Technologies
- LangGraph (Multi-Agent framework)
- Groq (LLM: openai/gpt-oss-20b)
- Pollinations.ai (Image generation)
- gTTS (Text-to-Speech)
- Streamlit (UI)

## Installation
```bash
pip install -r requirements.txt
```

## Usage
1. Create a `.env` file with your Groq API key:
GROQ_API_KEY=your_key_here

2. Run the Streamlit app:
streamlit run app.py

3. Choose a genre and start your interactive story.

## Project Structure
```
StoryAgent/
├── Agent.py              # Multi-Agent system (Orchestrator + Agents)
├── app.py                # Streamlit UI
├── requirements.txt      # Dependencies
├── .gitignore            # Ignored files
├── .env                  # API key (not uploaded)
├── story_images/         # Generated images
└── story_audio/          # Generated audio files
```


