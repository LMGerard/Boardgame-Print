import streamlit as st

def render(gm, game_name):
    st.subheader(f"🖼️ Galerie : {game_name}")
    
    try:
        config = gm._load_config(game_name)
        card_types = config.get("card_types", {})
    except:
        card_types = {}
        
    type_options = {v['name']: v for k, v in card_types.items()}
    
    if not card_types:
         st.info("Aucun type configuré.")
         return

    col_filter, col_size, col_edit = st.columns([2, 2, 1])
    with col_filter:
        type_filter = st.selectbox("Filtrer par type", ["Tous"] + list(type_options.keys()), key="filter_type")
    with col_size:
        nb_cols = st.slider("Taille de grille", min_value=2, max_value=10, value=6, help="Colonnes")
    with col_edit:
        edit_mode = st.toggle("✏️ Mode Édition", value=False)
    
    all_cards = []
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
                
                if not edit_mode:
                    st.markdown(f"**{card['name']}**")
                    st.caption(f"{card['type_name']} (x{card.get('count', 1)})")
                else:
                    with st.container(border=True):
                        new_name = st.text_input("Nom", value=card['name'], key=f"name_{i}", label_visibility="collapsed")
                        
                        current_type = folder_to_name.get(card['folder'], list(type_options.keys())[0])
                        try:
                            idx = list(type_options.keys()).index(current_type)
                        except: 
                            idx = 0
                        new_type = st.selectbox("Type", list(type_options.keys()), index=idx, key=f"t_{i}", label_visibility="collapsed")
                        new_count = st.number_input("Qté", min_value=1, value=int(card.get('count', 1)), step=1, key=f"q_{i}")

                        c1, c2 = st.columns(2)
                        if c1.button("💾", key=f"s_{i}"):
                            tf = type_options[new_type]['folder']
                            gm.update_card(game_name, card['folder'], card['name'], new_name, tf, new_count)
                            st.rerun()
                        
                        if c2.button("🗑️", key=f"d_{i}"):
                            gm.delete_card(game_name, card['folder'], card['name'])
                            st.rerun()
