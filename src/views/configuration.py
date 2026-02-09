import streamlit as st
import cv2
import numpy as np

def render(gm, game_name):
    # Paramètres globaux locaux pour cette vue si besoin
    # ou on peut les récupérer depuis app.py si passés en arg
    ppi = 10 
    seuil = 45

    st.subheader(f"⚙️ Configuration : {game_name}")
    
    # Charger la configuration
    try:
        config = gm._load_config(game_name)
        card_types = config.get("card_types", {})
    except:
        card_types = {}

    col_add, col_list = st.columns([1, 2])
    
    with col_add:
        with st.form("add_type_form"):
            st.markdown("### Ajouter un type")
            type_name = st.text_input("Nom (ex: Personnages)")
            width = st.number_input("Largeur (mm)", value=63, min_value=10)
            height = st.number_input("Hauteur (mm)", value=88, min_value=10)
            submit_type = st.form_submit_button("Ajouter ce type")
            
            if submit_type:
                if type_name:
                    succ, msg = gm.add_card_type(game_name, type_name, width, height)
                    if succ:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Veuillez entrer un nom.")
    
    with col_list:
        st.markdown("### Types existants")
        if not card_types:
            st.info("Aucun type de carte configuré.")
        else:
            for key, val in card_types.items():
                with st.container(border=True):
                    col_info, col_back = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"#### {val['name']}")
                        st.caption(f"Dimensions : {val['width_mm']} x {val['height_mm']} mm")
                        st.caption(f"Dossier : `{val['folder']}`")

                    with col_back:
                        # Gestion du dos de carte
                        back_path = gm.get_back_image_path(game_name, val['folder'])
                        if back_path:
                            st.image(back_path, caption="Dos actuel", width=100)
                        else:
                            st.info("Pas de dos")
                    
                    with st.expander("🖼️ Modifier le dos de carte"):
                        uploaded_back = st.file_uploader(f"Choisir une image pour {val['name']}", type=['png', 'jpg'], key=f"back_{key}")
                        if uploaded_back:
                            # Lecture
                            file_bytes = np.asarray(bytearray(uploaded_back.read()), dtype=np.uint8)
                            raw_back_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                            
                            # Traitement (Détection & Recadrage simple hardcodé ou paramétré)
                            # Pour éviter de redemander les sliders ici, on utilise des valeurs par défaut ou session
                            
                            with st.spinner("Détection..."):
                                from src.utils import detourer_carte_precise
                                res_back, success, msg = detourer_carte_precise(
                                    raw_back_img, 
                                    val['width_mm'], 
                                    val['height_mm'], 
                                    10, # PPI default
                                    45  # Seuil default
                                )
                            
                            if success:
                                succ_save, msg_save = gm.save_back_image(game_name, val['folder'], res_back)
                                if succ_save:
                                    st.success("Dos enregistré !")
                                    st.rerun()
                                else:
                                    st.error(msg_save)
                            else:
                                st.error(f"Echec détection: {msg}")
