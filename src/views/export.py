import streamlit as st
import os
import tempfile
from src.pdf_generator import PDFGenerator

def render(gm, game_name):
    st.subheader(f"🖨️ Export PDF : {game_name}")
    
    try:
        config = gm._load_config(game_name)
        card_types = config.get("card_types", {})
    except:
        card_types = {}
        
    if not card_types:
        st.warning("Aucun deck configuré.")
        return

    st.markdown("Cochez les decks à inclure dans le fichier PDF.")
    
    deck_names = [v['name'] for k, v in card_types.items()]
    type_options = {v['name']: v for k, v in card_types.items()}
    
    select_all = st.checkbox("Tout sélectionner", value=True)
    selected_decks = st.multiselect("Decks", deck_names, default=deck_names if select_all else [])

    if st.button("🚀 Générer PDF Recto-Verso", type="primary", use_container_width=True):
        if not selected_decks:
            st.warning("Sélectionnez au moins un deck.")
        else:
            pdf = PDFGenerator()
            grouped_cards = {}
            total_count = 0
            
            with st.status("Génération en cours...") as status:
                for d_name in selected_decks:
                    status.write(f"Ajout de {d_name}...")
                    data = type_options[d_name]
                    folder = data['folder']
                    w, h = data['width_mm'], data['height_mm']
                    
                    key = (w, h)
                    if key not in grouped_cards: grouped_cards[key] = []
                    
                    cards = gm.get_cards_by_type(game_name, folder)
                    back = gm.get_back_image_path(game_name, folder)
                    
                    for c in cards:
                        qty = int(c.get('count', 1))
                        for _ in range(qty):
                            grouped_cards[key].append({
                                'front': c['path'],
                                'back': back,
                                'width': w, 
                                'height': h
                            })
                            total_count += 1
                
                status.write("Assemblage PDF (téléchargement images)...")
                for dim, lst in grouped_cards.items():
                    pdf.add_deck_section(lst)
                
                t_file = f"Print_{game_name}.pdf"
                t_path = os.path.join(tempfile.gettempdir(), t_file)
                
                ok, msg = pdf.save(t_path)
                if ok:
                    status.update(label="Terminé!", state="complete")
                    with open(t_path, "rb") as f:
                        st.download_button("📥 Télécharger PDF", f, file_name=t_file)
                else:
                    st.error(msg)
