import streamlit as st
from src.game_manager import GameManager
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def init_page(page_title="Boardgame Print"):
    st.set_page_config(
        page_title=page_title,
        page_icon="🎲",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS Style
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .stButton>button { border-radius: 8px; font-weight: 600; }
        div[data-testid="stSidebarNav"] { border-top: 1px solid #ddd; padding-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

    # Init GameManager
    if 'gm' not in st.session_state:
        st.session_state['gm'] = GameManager()
    
    # Init Session Vars
    if 'selected_game_name' not in st.session_state:
        st.session_state['selected_game_name'] = None

    # --- SIDEBAR COMMON ---
    with st.sidebar:
        st.header("🎲 Boardgame Print")
        
        gm = st.session_state['gm']
        games = gm.get_games()
        
        # Determine index
        index = 0
        if st.session_state['selected_game_name'] in games:
            index = games.index(st.session_state['selected_game_name'])
        
        # Select Game
        selected_game = st.selectbox(
            "📂 Jeu actif", 
            ["-- Sélectionner --"] + games, 
            index=index + 1 if st.session_state['selected_game_name'] else 0,
            key="sidebar_game_select"
        )

        if selected_game != "-- Sélectionner --":
             st.session_state['selected_game_name'] = selected_game
        else:
             st.session_state['selected_game_name'] = None

        st.divider()
        
        # Create Game
        with st.expander("➕ Nouveau Jeu"):
            new_game_name = st.text_input("Nom", key="new_game_input")
            if st.button("Créer", use_container_width=True):
                if new_game_name:
                    success, msg = gm.create_game(new_game_name)
                    if success:
                        st.success("Jeu créé !")
                        st.rerun()
                    else:
                        st.error(msg)
        
        st.divider()
        
        # Navigation Note
        if not st.session_state['selected_game_name']:
            st.warning("👈 Veuillez sélectionner un jeu pour commencer.")

    return st.session_state['gm'], st.session_state['selected_game_name']
