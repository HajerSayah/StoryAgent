"""
Multi-Agent Interactive Storytelling System
- Orchestrator Agent: plans and delegates tasks
- Story Writer Agent: generates narration and choices
- Image Agent: generates scene images
- Audio Agent: generates audio narration
"""
import os
import json
import re
import requests
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# ===== Story genres =====
GENRES = {
    "1": "Romance",
    "2": "Comedy",
    "3": "Action Adventure",
    "4": "Horror Mystery",
    "5": "Fantasy Epic",
    "6": "Sci-Fi Thriller",
    "7": "Drama",
}

# ===== Guardrails =====
UNSAFE_WORDS = ["violent", "gore", "explicit", "naked", "blood", "weapon", "drug", "murder", "suicide", "rape", "torture", "slave", "abuse", "horror", "satan", "hell", "demon", "curse", "kill", "hate", "terror"]

def is_safe(text: str) -> bool:
    if not text: return True
    return not any(word in text.lower() for word in UNSAFE_WORDS)

def sanitize_text(text: str) -> str:
    replacements = {"violent": "intense", "gore": "dramatic", "blood": "red", "weapon": "tool", "drug": "substance", "murder": "mystery", "suicide": "tragedy", "rape": "harm", "torture": "pressure", "slave": "servant", "abuse": "stress", "horror": "mystery", "demon": "spirit", "curse": "challenge", "kill": "defeat", "hate": "dislike", "terror": "fear"}
    for old, new in replacements.items():
        if old in text.lower():
            text = text.replace(old, new)
    return text

# ===== Tools =====
_current_turn = {"n": 0}

@tool
def generate_scene_image(description: str) -> str:
    """Generates an image for the current scene using Pollinations.ai."""
    if not is_safe(description):
        description = sanitize_text(description)
        print(f"🛡️ Image description sanitized")
    try:
        safe_prompt = requests.utils.quote(description[:200])
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=768&height=512&nologo=true"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        os.makedirs("story_images", exist_ok=True)
        path = f"story_images/scene_{_current_turn['n']}.png"
        with open(path, "wb") as f:
            f.write(response.content)
        return f"Image saved to {path}"
    except Exception as e:
        return f"Image generation failed: {e}"

@tool
def generate_scene_audio(narration_text: str) -> str:
    """Generates audio narration for the current scene using gTTS."""
    if not is_safe(narration_text):
        narration_text = sanitize_text(narration_text)
        print(f"🛡️ Audio text sanitized")
    try:
        from gtts import gTTS
        os.makedirs("story_audio", exist_ok=True)
        path = f"story_audio/scene_{_current_turn['n']}.mp3"
        gTTS(text=narration_text, lang="en").save(path)
        return f"Audio saved to {path}"
    except Exception as e:
        return f"Audio generation failed: {e}"

TOOLS = [generate_scene_image, generate_scene_audio]

# ===== Model =====
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.8, groq_api_key=api_key)
llm_with_tools = llm.bind_tools(TOOLS)

# ===== State =====
class MultiAgentState(TypedDict):
    genre: str
    user_choice: str
    history: List[str]
    turn: int
    plan: str
    assigned_agent: str
    narration: str
    choice_a: str
    choice_b: str
    is_ending: bool
    image_path: str
    audio_path: str
    next_step: str
    error: str

# ===== 1. Orchestrator Agent =====
def orchestrator_node(state: MultiAgentState) -> dict:
    _current_turn["n"] = state["turn"]
    
    system_prompt = """You are the Orchestrator of a multi-agent storytelling system.
Your job is to plan the story and decide which agent should work on each scene.

Available agents:
1. Story Writer: generates narration text and choices
2. Image Agent: generates scene images
3. Audio Agent: generates audio narration

Based on the genre and current scene, decide which agents to activate.
Return your plan as JSON:
{
  "plan": "Brief description of what you want to happen in this scene",
  "agent": "writer" or "image" or "audio" or "all"
}"""
    
    user_prompt = f"""Genre: {state['genre']}
Story so far: {state['history']}
Turn: {state['turn'] + 1}
User choice: {state.get('user_choice', 'start')}"""
    
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    response = llm.invoke(messages)
    
    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(json)?", "", raw).strip("`").strip()
        data = json.loads(raw)
        return {
            "plan": data.get("plan", "Continue the story"),
            "assigned_agent": data.get("agent", "writer"),
            "next_step": "writer"
        }
    except:
        return {
            "plan": "Continue the story",
            "assigned_agent": "writer",
            "next_step": "writer"
        }

# ===== 2. Story Writer Agent =====
def writer_node(state: MultiAgentState) -> dict:
    force_ending = state["turn"] >= 6
    story_so_far = "\n".join(state["history"]) if state["history"] else "(the story is just beginning)"
    
    opening = "This is the OPENING scene. Invent an original premise that fits the genre." if state["turn"] == 0 else ""
    ending = "This MUST be the final scene: set is_ending to true." if force_ending else "Set is_ending to false and provide two real choices."
    
    system_text = f"""You are the Story Writer Agent. Write a short scene based on the plan.
Genre: {state['genre']}
Plan: {state.get('plan', 'Continue the story')}
{opening}

Story so far:
{story_so_far}

Write a short scene (3-5 sentences), second person ("you"), vivid and cinematic.
{ending}

Reply with ONLY valid JSON:
{{"narration": "...", "choice_a": "...", "choice_b": "...", "is_ending": true or false}}"""
    
    messages = [SystemMessage(content=system_text), HumanMessage(content="Write the scene.")]
    response = llm.invoke(messages)
    
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(json)?", "", raw).strip("`").strip()
    
    try:
        data = json.loads(raw)
        # Post-LLM Guardrail
        if not is_safe(data.get("narration", "")):
            data["narration"] = sanitize_text(data["narration"])
        if not is_safe(data.get("choice_a", "")):
            data["choice_a"] = sanitize_text(data["choice_a"])
        if not is_safe(data.get("choice_b", "")):
            data["choice_b"] = sanitize_text(data["choice_b"])
        
        return {
            "narration": data.get("narration", "The story continues..."),
            "choice_a": data.get("choice_a", "Continue"),
            "choice_b": data.get("choice_b", "Continue"),
            "is_ending": data.get("is_ending", force_ending),
        }
    except:
        return {
            "narration": "The story continues...",
            "choice_a": "Continue",
            "choice_b": "Continue",
            "is_ending": force_ending,
        }

# ===== 3. Image Agent =====
def image_node(state: MultiAgentState) -> dict:
    if state.get("assigned_agent") in ["image", "all"]:
        image_desc = state.get("plan", state.get("narration", ""))[:200]
        result = generate_scene_image.invoke({"description": image_desc})
        print(f"[Image Agent] {result}")
        return {"image_path": result, "next_step": END}
    return {"next_step": END}

# ===== 4. Audio Agent =====
def audio_node(state: MultiAgentState) -> dict:
    if state.get("assigned_agent") in ["audio", "all"]:
        audio_text = state.get("narration", "")
        result = generate_scene_audio.invoke({"narration_text": audio_text})
        print(f"[Audio Agent] {result}")
        return {"audio_path": result, "next_step": END}
    return {"next_step": END}

# ===== Routing =====
def route_after_writer(state: MultiAgentState) -> str:
    assigned = state.get("assigned_agent", "writer")
    if state.get("is_ending"):
        return END
    elif assigned in ["all", "image"]:
        return "image"
    elif assigned == "audio":
        return "audio"
    else:
        return END

def route_after_orchestrator(state: MultiAgentState) -> str:
    return "writer"

# ===== Graph =====
graph = StateGraph(MultiAgentState)

graph.add_node("orchestrator", orchestrator_node)
graph.add_node("writer", writer_node)
graph.add_node("image", image_node)
graph.add_node("audio", audio_node)

graph.set_entry_point("orchestrator")

graph.add_conditional_edges("orchestrator", route_after_orchestrator)
graph.add_conditional_edges("writer", route_after_writer)
graph.add_edge("image", END)
graph.add_edge("audio", END)

app = graph.compile()

# ===== Run =====
def run_story():
    print("🎭 Multi-Agent Interactive Storytelling System")
    print("=" * 60)
    print("Choose a genre:")
    for key, name in GENRES.items():
        print(f"  {key}) {name}")

    genre_choice = ""
    while genre_choice not in GENRES:
        genre_choice = input("Genre: ").strip()
    genre = GENRES[genre_choice]

    print(f"\n📖 Generating your {genre} story...\n")

    history = []
    turn = 0

    while True:
        initial_state: MultiAgentState = {
            "genre": genre,
            "user_choice": "",
            "history": history,
            "turn": turn,
            "plan": "",
            "assigned_agent": "",
            "narration": "",
            "choice_a": "",
            "choice_b": "",
            "is_ending": False,
            "image_path": "",
            "audio_path": "",
            "next_step": "",
            "error": ""
        }
        
        result = app.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print(f"📝 Scene {turn + 1}")
        print(f"📋 Plan: {result.get('plan', '')}")
        print(f"🤖 Agent used: {result.get('assigned_agent', 'writer')}")
        print("-" * 40)
        print(result["narration"])
        print("=" * 60)

        history.append(f"Scene {turn + 1}: {result['narration']}")

        if result.get("is_ending"):
            print("\n*** THE END ***\n")
            break

        print(f"\nA) {result['choice_a']}")
        print(f"B) {result['choice_b']}")

        choice = ""
        while choice not in ("a", "b"):
            choice = input("Your choice (A/B): ").strip().lower()

        history.append(f"You chose: {result['choice_a'] if choice == 'a' else result['choice_b']}")
        turn += 1


if __name__ == "__main__":
    run_story()