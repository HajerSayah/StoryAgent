import streamlit as st
import os
import glob
from Agent import play_scene, GENRES

st.set_page_config(page_title="📖 Interactive Story Agent", layout="wide")

# ===== CSS =====
st.markdown("""
    <style>
        .main-title {
            background: black;
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
        }
        .main-title h1 {
            color: #ffffff;
            font-size: 32px;
            font-weight: 700;
        }
        .main-title p {
            color: #aaaaaa;
            font-size: 16px;
            margin-top: 5px;
        }
        
        .scene-box {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            border-left: 6px solid #764ba2;
            margin: 20px 0;
            min-height: 150px;
        }
        
        .history-box {
            background: #f1f3f5;
            padding: 15px;
            border-radius: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .stButton > button {
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .image-container {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# ===== تهيئة الجلسة =====
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
if "scene_images" not in st.session_state:
    st.session_state.scene_images = []
if "scene_audios" not in st.session_state:
    st.session_state.scene_audios = []

# ===== العنوان =====
st.markdown('<div class="main-title"><h1>📖 Interactive Story Agent</h1><p>An AI-powered storytelling agent that generates images and audio for each scene</p></div>', unsafe_allow_html=True)

# ===== الشريط الجانبي =====
with st.sidebar:
    st.header("⚙️ Settings")
    genre_choice = st.selectbox(
        "Choose a genre:",
        list(GENRES.values())
    )
    
    if st.button("🚀 Start New Story", type="primary", use_container_width=True):
        st.session_state.history = []
        st.session_state.turn = 0
        st.session_state.story_ended = False
        st.session_state.genre = genre_choice
        st.session_state.current_scene = None
        st.session_state.scene_images = []
        st.session_state.scene_audios = []
        st.rerun()

# ===== عرض القصة =====
if st.session_state.genre and not st.session_state.story_ended:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📖 {st.session_state.genre} Story")
        
        if st.session_state.current_scene is None:
            with st.spinner("Generating scene..."):
                data = play_scene(
                    st.session_state.genre,
                    st.session_state.history,
                    st.session_state.turn
                )
                st.session_state.current_scene = data
                st.session_state.scene_images = sorted(glob.glob("story_images/*.png"), key=os.path.getmtime)
                st.session_state.scene_audios = sorted(glob.glob("story_audio/*.mp3"), key=os.path.getmtime)
        
        scene = st.session_state.current_scene
        st.markdown(f"### Scene {st.session_state.turn + 1}")
        st.markdown(f'<div class="scene-box">{scene["narration"]}</div>', unsafe_allow_html=True)
        
        if st.session_state.scene_images:
            latest_image = st.session_state.scene_images[-1]
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(latest_image, caption="🖼️ Scene Illustration", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.scene_audios:
            latest_audio = st.session_state.scene_audios[-1]
            st.audio(latest_audio)
        
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