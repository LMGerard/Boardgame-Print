import streamlit as st
import cv2
import numpy as np
import os
from src.utils import detourer_carte_precise

def render(gm, game_name):
    st.subheader(f"📸 Scanner : {game_name}")
    
    # Paramètres de détection
    with st.expander("🛠️ Paramètres de détection (Avancés)"):
        ppi = st.slider("Qualité (PPI)", 5, 20, 10, help="Plus élevé = meilleure qualité mais plus lent", key="ppi_scan")
        seuil = st.slider("Seuil détection", 20, 100, 45, help="Ajuster si la carte n'est pas détectée", key="seuil_scan")

    # Charger la configuration
    try:
        config = gm._load_config(game_name)
        card_types = config.get("card_types", {})
    except:
        card_types = {}

    if not card_types:
        st.warning("⚠️ Veuillez d'abord configurer au moins un type de carte dans l'onglet Configuration.")
        return

    # 1. Sélection du type (commun à tout le batch)
    col_sel, col_up = st.columns([1, 2])
    type_options = {v['name']: v for k, v in card_types.items()}
    
    with col_sel:
        selected_type_name = st.selectbox("Type de carte(s) à scanner", list(type_options.keys()))
        selected_type_data = type_options[selected_type_name]
        st.info(f"Cible : **{selected_type_data['width_mm']} x {selected_type_data['height_mm']} mm**")
    
    # 2. Upload / Camera
    with col_up:
        input_method = st.radio("Source", ["📁 Fichier", "📷 Caméra"], horizontal=True, label_visibility="collapsed")
        
        uploaded_files = []
        if input_method == "📁 Fichier":
            files = st.file_uploader(
                "Déposez vos images (Une ou plusieurs)", 
                type=['png', 'jpg', 'jpeg'], 
                accept_multiple_files=True
            )
            if files:
                uploaded_files = files
        else:
            camera_img = st.camera_input("Prendre une photo")
            if camera_img:
                # Add a name attribute to mimic UploadedFile behavior if needed, though camera_input returns UploadedFile
                camera_img.name = "camera_capture.jpg" 
                uploaded_files = [camera_img]

    st.divider()

    if uploaded_files:
        # Mode SINGLE FILE
        if len(uploaded_files) == 1:
            col_scan1, col_scan2 = st.columns([1, 1], gap="large")
            file = uploaded_files[0]
            
            with col_scan1:
                st.subheader("Prévisualisation")
                file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                file.seek(0)
                st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), caption="Original", width=300)
                
                if st.button("✨ Traiter l'image", type="primary", use_container_width=True):
                    with st.spinner("Traitement..."):
                        res, success, msg = detourer_carte_precise(
                            image, 
                            selected_type_data['width_mm'], 
                            selected_type_data['height_mm'], 
                            ppi, 
                            seuil
                        )
                        if success:
                            st.session_state['last_processed'] = res
                            st.session_state['last_processed_type'] = selected_type_data['folder']
                            st.success(msg)
                        else:
                            st.error(msg)

            with col_scan2:
                st.subheader("Résultat")
                if 'last_processed' in st.session_state:
                    res_rgb = cv2.cvtColor(st.session_state['last_processed'], cv2.COLOR_BGRA2RGBA)
                    st.image(res_rgb, caption="Carte Détectée", use_container_width=True)
                    
                    with st.form("save_single"):
                        card_name = st.text_input("Nom de la carte")
                        quantity = st.number_input("Nombre d'exemplaires", min_value=1, value=1, step=1)
                        if st.form_submit_button("💾 Enregistrer"):
                            gm.save_card(
                                game_name, 
                                st.session_state['last_processed_type'], 
                                st.session_state['last_processed'], 
                                card_name or None,
                                count=quantity
                            )
                            st.success("Enregistré !")
                            del st.session_state['last_processed']
                            st.rerun()

        # Mode BATCH
        else:
            st.subheader(f"🔄 Mode Batch : {len(uploaded_files)} images")
            
            if st.button(f"🚀 Traiter {len(uploaded_files)} images", type="primary"):
                progress_bar = st.progress(0)
                results = []
                
                for i, file in enumerate(uploaded_files):
                    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    
                    res, success, msg = detourer_carte_precise(
                        image, 
                        selected_type_data['width_mm'], 
                        selected_type_data['height_mm'], 
                        ppi, 
                        seuil
                    )
                    results.append({
                        "filename": file.name,
                        "image": res if success else None,
                        "success": success,
                        "msg": msg
                    })
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                st.session_state['batch_results'] = results
                st.session_state['batch_type'] = selected_type_data['folder']
            
            if st.session_state.get('batch_results'):
                results = st.session_state['batch_results']
                success_count = sum(1 for r in results if r['success'])
                st.success(f"{success_count}/{len(results)} réussis")
                
                with st.form("save_batch"):
                    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                    with col_b1:
                        base_name = st.text_input("Nom de base", placeholder="Optionnel")
                    with col_b3:
                        batch_qty = st.number_input("Exemplaires", min_value=1, value=1)
                    with col_b2:
                        save_all = st.form_submit_button("💾 Tout Enregistrer")

                    if save_all:
                        count = 0
                        for i, r in enumerate(results):
                            if r['success']:
                                final_name = f"{base_name}_{i+1}" if base_name else os.path.splitext(r['filename'])[0]
                                gm.save_card(game_name, st.session_state['batch_type'], r['image'], final_name, count=batch_qty)
                                count += 1
                        st.success(f"{count} cartes enregistrées !")
                        st.session_state['batch_results'] = None
                        st.rerun()

                st.markdown("### Aperçu")
                cols = st.columns(4)
                for i, r in enumerate(results):
                    with cols[i % 4]:
                        if r['success']:
                            st.image(cv2.cvtColor(r['image'], cv2.COLOR_BGRA2RGBA), use_container_width=True)
                            st.caption(f"✅ {r['filename']}")
                        else:
                            st.error(f"❌ {r['filename']}")
