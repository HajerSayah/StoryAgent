"""
Interactive Storytelling Agent - Real Tool-Calling Agent (LangGraph)
------------------------------------------------------------------------
This version is a genuine Agent: the LLM itself decides, on every scene,
whether to call the image tool, the audio tool, both, or neither. Claude/
Groq is NOT told "always generate an image" -- it is given the tools and
told what they're for, and it chooses.

Architecture (two graphs working together):

  1. TURN graph (runs once per scene) -- a classic ReAct tool-calling loop:

        START -> [agent] --tool call?--> [tools] --> [agent] --> ... -> END
                     |
                     +--no tool call, final JSON--> END

  2. STORY loop (outer Python loop) -- repeatedly runs the TURN graph,
     shows the scene, asks the user for A/B, and feeds the growing story
     history back in, until the Agent itself decides the story has ended.

This mirrors how real production agents are built: a tool-calling core
(the graph) wrapped by an outer control loop.
"""

import os
import json
import re
import requests
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

# Genre menu
GENRES = {
    "1": "Romance",
    "2": "Comedy",
    "3": "Action Adventure",
    "4": "Horror Mystery",
    "5": "Fantasy Epic",
    "6": "Sci-Fi Thriller",
    "7": "Drama",
}

MAX_TURNS = 6  # a longer story now that it's a real multi-tool agent

# Simple counter the tools use to name their output files.
# (Tools only receive the arguments the LLM decides to pass them,
#  so we track "which scene are we on" separately, at module level.)
_current_turn = {"n": 0}


@tool
def generate_scene_image(description: str) -> str:
    """Generate and save an illustration for the current story scene.
    Use this when a visual would meaningfully enrich the scene (a key
    location, a dramatic moment, a character reveal). Do not use it for
    every single scene if it wouldn't add much. The argument should be a
    short, vivid visual description of what to draw.
    Returns the local file path of the saved image."""
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
    """Generate and save a spoken-voice narration (mp3) of the given text
    for the current scene. Use this for scenes where hearing the narration
    read aloud adds impact (tense moments, emotional beats, an opening).
    Not every scene needs audio. The argument should be the narration text
    to speak aloud.
    Returns the local file path of the saved audio file."""
    try:
        from gtts import gTTS

        os.makedirs("story_audio", exist_ok=True)
        path = f"story_audio/scene_{_current_turn['n']}.mp3"
        gTTS(text=narration_text, lang="en").save(path)
        return f"Audio saved to {path}"
    except Exception as e:
        return f"Audio generation failed: {e}"


TOOLS = [generate_scene_image, generate_scene_audio]

# LLM with tools bound -- THIS is what turns it into an Agent.
llm = ChatGroq(
    model="openai/gpt-oss-20b", 
    temperature=0.8,
    groq_api_key=api_key  
)
llm_with_tools = llm.bind_tools(TOOLS)


# TURN graph state: just a running list of messages for ONE scene's
# tool-calling loop (system prompt, tool calls, tool results, final answer)
class TurnState(TypedDict):
    messages: Annotated[list, add_messages]


def agent_node(state: TurnState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


turn_graph = StateGraph(TurnState)
turn_graph.add_node("agent", agent_node)
turn_graph.add_node("tools", ToolNode(TOOLS))
turn_graph.set_entry_point("agent")
turn_graph.add_conditional_edges("agent", tools_condition)
turn_graph.add_edge("tools", "agent")
turn_app = turn_graph.compile()


# ---------------------------------------------------------
# One full scene: build the prompt, run the tool-calling loop,
# parse the final JSON scene, and report which tools were used.
# ---------------------------------------------------------
def play_scene(genre: str, history: list[str], turn: int) -> dict:
    _current_turn["n"] = turn
    force_ending = turn >= MAX_TURNS
    story_so_far = "\n".join(history) if history else "(the story is just beginning)"

    opening_instruction = (
        "This is the OPENING scene. Invent an original, specific premise that "
        "fits the genre (setting, main character, a hook) and dive straight "
        "into the action -- do not ask the user for any input about the premise."
        if turn == 0 else ""
    )

    ending_instruction = (
        "This MUST be the final scene: bring the story to a satisfying close, "
        "set is_ending to true, and leave choice_a and choice_b as empty strings."
        if force_ending else
        "This is NOT the ending yet. Set is_ending to false and provide two real, "
        "meaningfully different choices."
    )

    system_text = f"""You are the narrator and director of an interactive story.
Genre/tone: {genre} -- every scene, the narration style, and the choices you
offer must clearly match this genre and tone throughout.
{opening_instruction}

Story so far:
{story_so_far}

You have two tools available: generate_scene_image and generate_scene_audio.
Decide for YOURSELF whether this particular scene would benefit from an
image, an audio narration, both, or neither -- use your judgment, don't
call a tool just because it exists.

Write the next short scene (3-5 sentences), second person ("you"), vivid
and cinematic. {ending_instruction}

Once you are done (after using any tools you decided to use), reply with
ONLY valid JSON in exactly this format, no extra text, no markdown fences:
{{
  "narration": "...",
  "choice_a": "...",
  "choice_b": "...",
  "is_ending": true or false
}}"""

    messages = [SystemMessage(content=system_text), HumanMessage(content="Continue the story.")]

    result = turn_app.invoke({"messages": messages}, config={"recursion_limit": 25})

    # Report which tools the Agent decided to use this turn
    for m in result["messages"]:
        if isinstance(m, ToolMessage):
            print(f"[Agent used tool '{m.name}' -> {m.content}]")

    raw = result["messages"][-1].content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(json)?", "", raw).strip("`").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "narration": "The story falters for a moment... (invalid response, try again)",
            "choice_a": "Try again",
            "choice_b": "Try again",
            "is_ending": force_ending,
        }


# ---------------------------------------------------------
# Outer story loop
# ---------------------------------------------------------
def run_story():
    print("Interactive Storytelling Agent")
    print("=" * 60)
    print("Choose a genre:")
    for key, name in GENRES.items():
        print(f"  {key}) {name}")

    genre_choice = ""
    while genre_choice not in GENRES:
        genre_choice = input("Genre: ").strip()
    genre = GENRES[genre_choice]

    print(f"\nGenerating your {genre} story...\n")

    history: list[str] = []
    turn = 0

    while True:
        data = play_scene(genre, history, turn)

        print("\n" + "=" * 60)
        print(data["narration"])
        print("=" * 60)

        history.append(f"Scene {turn + 1}: {data['narration']}")

        if data.get("is_ending"):
            print("\n*** THE END ***\n")
            break

        print(f"\nA) {data['choice_a']}")
        print(f"B) {data['choice_b']}")

        choice = ""
        while choice not in ("a", "b"):
            choice = input("Your choice (A/B): ").strip().lower()

        chosen_text = data["choice_a"] if choice == "a" else data["choice_b"]
        history.append(f"You chose: {chosen_text}")
        turn += 1


if __name__ == "__main__":
    run_story()