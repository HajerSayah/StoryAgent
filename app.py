import streamlit as st
import os
import glob
from Agent import app as agent_app, GENRES, MultiAgentState  

st.set_page_config(page_title="📖 Interactive Story Agent", layout="wide")

# CSS 
st.markdown("""...""", unsafe_allow_html=True)

# تهيئة الجلسة 
if "history" not in st.session_state:
    st.session_state.history = []
if "genre" not in st.session_state:
    st.session_state.genre = None
if "turn" not in st.session_state:
    st.session_state.turn = 0
if "current_scene" not in st.session_state:
    st.session_state.current_scene = None
if "story_ended" not in st.session_state:
    st.session_state.story_ended = False

# العنوان 
st.markdown('<div class="main-title"><h1>🎭 Multi-Agent Story Agent</h1><p>Orchestrator + Writer + Image + Audio</p></div>', unsafe_allow_html=True)

#  الشريط الجانبي
with st.sidebar:
    st.header("⚙️ Settings")
    genre_choice = st.selectbox("Choose a genre:", list(GENRES.values()))
    
    if st.button("🚀 Start New Story", type="primary", use_container_width=True):
        st.session_state.history = []
        st.session_state.turn = 0
        st.session_state.story_ended = False
        st.session_state.genre = genre_choice
        st.session_state.current_scene = None
        st.rerun()

# عرض القصة 
if st.session_state.genre and not st.session_state.story_ended:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📖 {st.session_state.genre} Story")
        
        if st.session_state.current_scene is None:
            with st.spinner("Generating scene..."):
                initial_state = MultiAgentState(
                    genre=st.session_state.genre,
                    user_choice="",
                    history=st.session_state.history,
                    turn=st.session_state.turn,
                    plan="",
                    assigned_agent="",
                    narration="",
                    choice_a="",
                    choice_b="",
                    is_ending=False,
                    image_path="",
                    audio_path="",
                    next_step="",
                    error=""
                )
                result = agent_app.invoke(initial_state)
                st.session_state.current_scene = result
        
        scene = st.session_state.current_scene
        st.markdown(f"### Scene {st.session_state.turn + 1}")
        st.markdown(f'<div class="scene-box">{scene["narration"]}</div>', unsafe_allow_html=True)
        
        # عرض الصورة إذا وجدت
        if scene.get("image_path") and "failed" not in scene["image_path"]:
            image_files = sorted(glob.glob("story_images/*.png"), key=os.path.getmtime)
            if image_files:
                st.image(image_files[-1], caption="🖼️ Scene Illustration", use_container_width=True)
        
        # عرض الصوت إذا وجد
        audio_files = sorted(glob.glob("story_audio/*.mp3"), key=os.path.getmtime)
        if audio_files:
            st.audio(audio_files[-1])
        
        if not scene.get("is_ending", False):
            st.markdown("### 🎯 Choose your next move:")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(f"🅰️ {scene['choice_a']}", use_container_width=True):
                    st.session_state.history.append(f"You chose: {scene['choice_a']}")
                    st.session_state.turn += 1
                    st.session_state.current_scene = None
                    st.rerun()
            with col_b:
                if st.button(f"🅱️ {scene['choice_b']}", use_container_width=True):
                    st.session_state.history.append(f"You chose: {scene['choice_b']}")
                    st.session_state.turn += 1
                    st.session_state.current_scene = None
                    st.rerun()
        else:
            st.success("🏁 **The End!**")
            st.session_state.story_ended = True
    
    with col2:
        st.markdown("### 📜 Story History")
        st.markdown('<div class="history-box">', unsafe_allow_html=True)
        for i, h in enumerate(st.session_state.history[-8:]):
            st.caption(f"**Scene {i+1}:** {h[:80]}...")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🔄 Reset Story", use_container_width=True):
            st.session_state.history = []
            st.session_state.turn = 0
            st.session_state.story_ended = False
            st.session_state.current_scene = None
            st.rerun()

else:
    st.info("👈 Choose a genre and click **'Start New Story'** to begin your adventure!")