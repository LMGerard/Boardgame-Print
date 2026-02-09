import streamlit as st
from src.layout import init_page
from src.views import configuration, scanner, gallery, export

# 1. Init Page & Sidebar
# This handles the Game Selector in Sidebar
gm, game_name = init_page("Boardgame Print")

# 2. Main Content Area
if not game_name:
    st.title("👋 Bienvenue sur Boardgame Print")
    st.markdown("""
    <div style='text-align: center; padding: 50px; background: white; border-radius: 8px;'>
        <h2>Votre assistant de création de prototypes</h2>
        <p>Ce logiciel vous permet de scanner, organiser et imprimer vos cartes.</p>
        <br>
        <p>👈 <strong>Commencez par sélectionner ou créer un jeu dans la barre latérale.</strong></p>
    </div>
    """, unsafe_allow_html=True)
else:
    # 3. Tabs Navigation (Contextual to the selected game)
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚙️ Configuration", 
        "📸 Scanner", 
        "🖼️ Galerie", 
        "🖨️ Export PDF"
    ])
    
    with tab1:
        configuration.render(gm, game_name)
    
    with tab2:
        scanner.render(gm, game_name)
        
    with tab3:
        gallery.render(gm, game_name)
        
    with tab4:
        export.render(gm, game_name)
