import streamlit as st
import cv2
import numpy as np
import io
import os
import json
from PIL import Image

# Import des modules locaux
try:
    from src.utils import detourer_carte_precise
    from src.game_manager import GameManager
    from src.pdf_generator import PDFGenerator
except ImportError:
    # Fallback pour le premier run si les modules ne sont pas encore chargés par python
    import sys
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from src.utils import detourer_carte_precise
    from src.game_manager import GameManager
    from src.pdf_generator import PDFGenerator

# Initialisation du gestionnaire
# On instancie à chaque run pour être sûr d'avoir la dernière version du code
gm = GameManager()

# Configuration de la page
st.set_page_config(
    page_title="Boardgame Print - Scanner Multi-Decks",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background: #f8f9fa; }
    
    h1, h2, h3 { color: #2c3e50; }
    
    .card-container {
        background: white;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        text-align: center;
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Style pour la grille batch */
    .batch-item {
        background: white;
        border-radius: 8px;
        padding: 5px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE INIT -----------------
if 'selected_game_name' not in st.session_state:
    st.session_state['selected_game_name'] = None 
if 'batch_results' not in st.session_state:
    st.session_state['batch_results'] = None

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.header("🎲 Gestion des Jeux")
    
    # 1. Sélection du Jeu
    games = gm.get_games()
    
    # Gérer la sélection
    index = 0
    if st.session_state['selected_game_name'] in games:
        index = games.index(st.session_state['selected_game_name'])
        
    selected_game = st.selectbox(
        "📂 Sélectionner un jeu", 
        ["-- Sélectionner --"] + games, 
        index=index + 1 if st.session_state['selected_game_name'] else 0
    )

    if selected_game != "-- Sélectionner --":
         st.session_state['selected_game_name'] = selected_game
    else:
         st.session_state['selected_game_name'] = None

    st.divider()

    # 2. Création de Jeu
    with st.expander("➕ Nouveau Jeu", expanded=False):
        new_game_name = st.text_input("Nom du nouveau jeu")
        if st.button("Créer le jeu", use_container_width=True):
            if new_game_name:
                if gm.create_game(new_game_name)[0]:
                    st.success(f"Jeu '{new_game_name}' créé !")
                    st.rerun()
                else:
                    st.error("Erreur lors de la création.")
            else:
                st.warning("Nom invalide.")
    
    st.divider()
    
    # Paramètres globaux (cachés)
    with st.expander("⚙️ Paramètres Avancés"):
        ppi = st.slider("Qualité (PPI)", 5, 20, 10, help="Plus élevé = meilleure qualité mais plus lent")
        seuil = st.slider("Seuil détection", 20, 100, 45, help="Ajuster si la carte n'est pas détectée")


# ----------------- MAIN CONTENT -----------------

game_name = st.session_state['selected_game_name']

if game_name:
    st.title(f"Jeu : {game_name}")
    
    # Charger la configuration
    try:
        config = gm._load_config(game_name)
        card_types = config.get("card_types", {})
    except:
        card_types = {}

    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Configuration", "📸 Scanner (Batch)", "🖼️ Galerie", "🖨️ Export PDF"])
    
    # --- TAB 1: CONFIGURATION ---
    with tab1:
        st.subheader("Gérer les Types de Cartes (Decks)")
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
                                
                                # Traitement (Détection & Recadrage)
                                with st.spinner("Détection et recadrage du dos..."):
                                    res_back, success, msg = detourer_carte_precise(
                                        raw_back_img, 
                                        val['width_mm'], 
                                        val['height_mm'], 
                                        ppi, 
                                        seuil
                                    )
                                
                                if success:
                                    # On sauvegarde
                                    succ_save, msg_save = gm.save_back_image(game_name, val['folder'], res_back)
                                    if succ_save:
                                        st.success("Dos détecté et sauvegardé avec succès !")
                                        st.rerun()
                                    else:
                                        st.error(msg_save)
                                else:
                                    st.error(f"Impossible de détecter le dos : {msg}")
                                    st.warning("Assurez-vous que le dos est sur un fond sombre et bien éclairé.")

    # --- TAB 2: SCANNER ---
    with tab2:
        if not card_types:
            st.warning("⚠️ Veuillez d'abord configurer au moins un type de carte.")
        else:
            # 1. Sélection du type (commun à tout le batch)
            st.markdown("### 1. Configuration du Batch")
            type_options = {v['name']: v for k, v in card_types.items()}
            
            # Layout des settings
            c_set1, c_set2 = st.columns([1, 2])
            with c_set1:
                selected_type_name = st.selectbox("Type de carte(s) à scanner", list(type_options.keys()))
                selected_type_data = type_options[selected_type_name]
                st.info(f"Dimensions cibles : **{selected_type_data['width_mm']} x {selected_type_data['height_mm']} mm**")
            
            # 2. Upload
            with c_set2:
                uploaded_files = st.file_uploader(
                    "Déposez vos images (Une ou plusieurs)", 
                    type=['png', 'jpg', 'jpeg'], 
                    accept_multiple_files=True
                )

            st.divider()

            if uploaded_files:
                # Mode SINGLE FILE (Interface détaillée)
                if len(uploaded_files) == 1:
                    col_scan1, col_scan2 = st.columns([1, 1], gap="large")
                    
                    file = uploaded_files[0]
                    
                    with col_scan1:
                        st.subheader("Prévisualisation")
                        # Lecture
                        file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        file.seek(0) # Reset pointer
                        
                        st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), caption="Original", width=300)
                        
                        # Bouton de traitement
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

                # Mode BATCH (Interface Grille)
                else:
                    st.subheader(f"🔄 Mode Batch : {len(uploaded_files)} images détectées")
                    
                    # Bouton d'action global
                    if st.button(f"🚀 Lancer le traitement de {len(uploaded_files)} images", type="primary"):
                        progress_bar = st.progress(0)
                        results = []
                        
                        for i, file in enumerate(uploaded_files):
                            # Lecture
                            file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                            
                            # Traitement
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
                    
                    # Affichage des résultats du batch
                    if st.session_state.get('batch_results'):
                        results = st.session_state['batch_results']
                        success_count = sum(1 for r in results if r['success'])
                        
                        st.success(f"Traitement terminé : {success_count}/{len(results)} réussis")
                        
                        # Formulaire de sauvegarde groupée
                        with st.form("save_batch"):
                            col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                            with col_b1:
                                base_name = st.text_input("Nom de base (ex: 'Monstre')", placeholder="Laissez vide pour garder le nom du fichier")
                            with col_b3:
                                batch_qty = st.number_input("Exemplaires par carte", min_value=1, value=1, step=1)
                            with col_b2:
                                save_all = st.form_submit_button("💾 Tout Enregistrer")

                            if save_all:
                                count_saved = 0
                                for i, r in enumerate(results):
                                    if r['success']:
                                        # Déterminer le nom
                                        if base_name:
                                            final_name = f"{base_name}_{i+1}"
                                        else:
                                            # Utiliser nom fichier sans extension
                                            final_name = os.path.splitext(r['filename'])[0]
                                            
                                        gm.save_card(game_name, st.session_state['batch_type'], r['image'], final_name, count=batch_qty)
                                        count_saved += 1
                                
                                st.success(f"{count_saved} cartes enregistrées avec succès !")
                                st.session_state['batch_results'] = None # Clear
                                st.rerun()

                        # Grille de prévisualisation
                        st.markdown("### Aperçu des résultats")
                        cols = st.columns(4)
                        for i, r in enumerate(results):
                            with cols[i % 4]:
                                if r['success']:
                                    img_rgb = cv2.cvtColor(r['image'], cv2.COLOR_BGRA2RGBA)
                                    st.image(img_rgb, use_container_width=True)
                                    st.markdown(f"✅ **{r['filename']}**")
                                else:
                                    st.error(f"❌ {r['filename']}")
                                    st.caption(r['msg'])

    # --- TAB 3: GALERIE ---
    with tab3:
        st.subheader("Galerie")
        if not card_types:
             st.info("Aucun type configuré.")
        else:
            col_filter, col_size, col_edit = st.columns([2, 2, 1])
            with col_filter:
                type_filter = st.selectbox("Filtrer par type", ["Tous"] + list(type_options.keys()), key="filter_type")
            with col_size:
                nb_cols = st.slider("Taille de grille", min_value=2, max_value=10, value=6, help="Ajuster le nombre de cartes par ligne")
            with col_edit:
                # Toggle pour le mode édition
                edit_mode = st.toggle("✏️ Mode Édition", value=False)
            
            all_cards = []
            
            # Map folder -> type name for reverse lookup
            folder_to_name = {v['folder']: v['name'] for k, v in card_types.items()}
            
            if type_filter == "Tous":
                 for t_key, t_val in card_types.items():
                     c_list = gm.get_cards_by_type(game_name, t_val['folder'])
                     for c in c_list:
                         c['type_name'] = t_val['name']
                         c['folder'] = t_val['folder']
                         all_cards.append(c)
            else:
                 folder = type_options[type_filter]['folder']
                 all_cards = gm.get_cards_by_type(game_name, folder)
                 for c in all_cards:
                     c['type_name'] = type_filter
                     c['folder'] = folder

            if not all_cards:
                st.info("Aucune carte trouvée.")
            else:
                cols = st.columns(nb_cols)
                for i, card in enumerate(all_cards):
                    with cols[i % nb_cols]:
                        st.image(card['path'], use_container_width=True)
                        
                        # --- MODE LECTURE ---
                        if not edit_mode:
                            st.markdown(f"**{card['name']}**")
                            st.caption(f"{card['type_name']} (x{card.get('count', 1)})")
                        
                        # --- MODE ÉDITION ---
                        else:
                            with st.container(border=True):
                                # Input Nom
                                new_name = st.text_input("Nom", value=card['name'], key=f"name_{i}", label_visibility="collapsed")
                                
                                # Selectbox Type
                                current_type_name = folder_to_name.get(card['folder'], list(type_options.keys())[0])
                                type_list = list(type_options.keys())
                                try:
                                    default_idx = type_list.index(current_type_name)
                                except ValueError:
                                    default_idx = 0
                                    
                                new_type_name = st.selectbox("Type", type_list, index=default_idx, key=f"type_{i}", label_visibility="collapsed")
                                
                                # Input Quantité
                                new_count = st.number_input("Qté", min_value=1, value=int(card.get('count', 1)), step=1, key=f"qty_{i}")

                                col_save, col_del = st.columns(2)
                                
                                # Bouton Sauvegarder
                                if col_save.button("💾", key=f"save_{i}", help="Sauvegarder", use_container_width=True):
                                    target_folder = type_options[new_type_name]['folder']
                                    succ, msg = gm.update_card(
                                        game_name, 
                                        card['folder'], 
                                        card['name'], 
                                        new_name=new_name, 
                                        new_type_folder=target_folder,
                                        new_count=new_count
                                    )
                                    if succ:
                                        st.success("OK")
                                        st.rerun()
                                    else:
                                        st.error("Erreur")
                                
                                # Bouton Supprimer
                                if col_del.button("🗑️", key=f"del_{i}", help="Supprimer", use_container_width=True):
                                     del_success, del_msg = gm.delete_card(game_name, card['folder'], card['name'])
                                     if del_success:
                                         st.rerun()
                                     else:
                                         st.error("Erreur")

    # --- TAB 4: EXPORT PDF ---
    with tab4:
        st.subheader("🖨️ Générer le PDF d'impression")
        
        if not card_types:
            st.warning("Aucun deck configuré.")
        else:
            # Sélection des Decks
            st.markdown("Sélectionnez les decks à inclure dans le PDF :")
            deck_names = list(type_options.keys())
            
            # Select All toggle
            select_all = st.checkbox("Tout sélectionner", value=True)
            selected_decks = st.multiselect(
                "Decks", 
                deck_names, 
                default=deck_names if select_all else []
            )

            if st.button("🚀 Générer le PDF Recto-Verso", type="primary", use_container_width=True):
                if not selected_decks:
                    st.warning("Veuillez sélectionner au moins un deck.")
                else:
                    pdf = PDFGenerator()
                    
                    # Logique de regroupement par dimensions
                    # Format: {(w, h): [list_cards]}
                    grouped_cards = {}
                    
                    total_cards_count = 0
                    
                    with st.status("Génération en cours...") as status:
                        for deck_name in selected_decks:
                            status.write(f"Traitement du deck : {deck_name}...")
                            deck_data = type_options[deck_name]
                            folder = deck_data['folder']
                            w = deck_data['width_mm']
                            h = deck_data['height_mm']
                            
                            key = (w, h)
                            if key not in grouped_cards:
                                grouped_cards[key] = []
                            
                            # Récupérer les cartes
                            cards = gm.get_cards_by_type(game_name, folder)
                            back_path = gm.get_back_image_path(game_name, folder)
                            
                            for c in cards:
                                # Gestion de la quantité
                                count_copies = int(c.get('count', 1))
                                for _ in range(count_copies):
                                    # Data structure for PDF generator
                                    card_entry = {
                                        'front': c['path'],
                                        'back': back_path,
                                        'width': w,
                                        'height': h
                                    }
                                    grouped_cards[key].append(card_entry)
                                    total_cards_count += 1
                        
                        status.write("Assemblage du PDF...")
                        
                        # Génération des sections
                        for dim, cards_list in grouped_cards.items():
                            pdf.add_deck_section(cards_list)
                        
                        # Création du fichier temporaire
                        import tempfile
                        tmp_filename = f"Print_{game_name.replace(' ', '_')}.pdf"
                        tmp_path = os.path.join(tempfile.gettempdir(), tmp_filename)
                        
                        success, result_msg = pdf.save(tmp_path)
                        
                        if success:
                            status.update(label="PDF prêt !", state="complete")
                            st.success(f"PDF généré avec succès ! ({total_cards_count} cartes)")
                            
                            with open(tmp_path, "rb") as pdf_file:
                                PDFbyte = pdf_file.read()

                            st.download_button(
                                label="📥 Télécharger le PDF",
                                data=PDFbyte,
                                file_name=tmp_filename,
                                mime='application/octet-stream',
                                use_container_width=True
                            )
                        else:
                            st.error(result_msg)

else:
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h2>👋 Bienvenue sur Boardgame Print</h2>
        <p>Commencez par sélectionner un jeu existant dans la barre latérale ou créez-en un nouveau.</p>
    </div>
    """, unsafe_allow_html=True)
