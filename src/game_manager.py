import os
import cv2
import shutil
from pathlib import Path
import json

DATA_DIR = Path("data")

class GameManager:
    def __init__(self):
        # Créer le dossier data s'il n'existe pas
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True)
            
    def get_games(self):
        """Retourne la liste des jeux existants (dossiers dans data)"""
        return [d.name for d in DATA_DIR.iterdir() if d.is_dir()]

    def create_game(self, game_name):
        """Crée un nouveau jeu (dossier)"""
        sanitized_name = "".join([c for c in game_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not sanitized_name:
            return False, "Nom de jeu invalide."
            
        game_path = DATA_DIR / sanitized_name
        if game_path.exists():
            return False, "Ce jeu existe déjà."
            
        try:
            game_path.mkdir(parents=True)
            # Initialiser le fichier de config vide
            self._save_config(sanitized_name, {"card_types": {}})
            return True, f"Jeu '{sanitized_name}' créé avec succès !"
        except Exception as e:
            return False, f"Erreur lors de la création : {str(e)}"

    def _get_config_path(self, game_name):
        return DATA_DIR / game_name / "config.json"

    def _load_config(self, game_name):
        config_path = self._get_config_path(game_name)
        if not config_path.exists():
            return {"card_types": {}}
        with open(config_path, 'r') as f:
            return json.load(f)

    def _save_config(self, game_name, config):
        with open(self._get_config_path(game_name), 'w') as f:
            json.dump(config, f, indent=4)

    def add_card_type(self, game_name, type_name, width_mm, height_mm):
        """Ajoute un nouveau type de carte (ex: 'Personnages', 63x88mm)"""
        config = self._load_config(game_name)
        
        # Sanitization du nom du type pour le dossier
        sanitized_type = "".join([c for c in type_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        if sanitized_type in config.get("card_types", {}):
            return False, "Ce type de carte existe déjà."
            
        # Créer le dossier physique
        type_path = DATA_DIR / game_name / sanitized_type
        try:
            type_path.mkdir(exist_ok=True)
        except Exception as e:
            return False, f"Erreur création dossier : {str(e)}"
            
        # Sauvegarder la config
        config["card_types"][sanitized_type] = {
            "name": type_name,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "folder": sanitized_type
        }
        self._save_config(game_name, config)
        return True, f"Type '{type_name}' ajouté ({width_mm}x{height_mm}mm)"

    def get_card_types(self, game_name):
        """Récupère les types de cartes configurés pour un jeu"""
        config = self._load_config(game_name)
        return config.get("card_types", {})

    def _get_deck_metadata_path(self, game_name, deck_folder):
        return DATA_DIR / game_name / deck_folder / "cards.json"

    def _load_deck_metadata(self, game_name, deck_folder):
        path = self._get_deck_metadata_path(game_name, deck_folder)
        if not path.exists():
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_deck_metadata(self, game_name, deck_folder, data):
        path = self._get_deck_metadata_path(game_name, deck_folder)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def save_card(self, game_name, card_type_folder, card_image, card_name=None, count=1):
        """Sauvegarde une carte dans le dossier du type spécifique"""
        type_path = DATA_DIR / game_name / card_type_folder
        if not type_path.exists():
            return False, "Le dossier du type de carte n'existe pas."
            
        # Générer un nom si non fourni
        if not card_name:
            # Compter les fichiers existants
            count_files = len(list(type_path.glob("*.png"))) + 1
            card_name = f"carte_{count_files:03d}"
            
        sanitized_card_name = "".join([c for c in card_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{sanitized_card_name}.png"
        file_path = type_path / filename
        
        try:
            cv2.imwrite(str(file_path), card_image)
            
            # Sauvegarder les métadonnées (quantité)
            meta = self._load_deck_metadata(game_name, card_type_folder)
            meta[filename] = {"count": int(count)}
            self._save_deck_metadata(game_name, card_type_folder, meta)
            
            return True, f"Carte enregistrée : {filename} (x{count})"
        except Exception as e:
            return False, f"Erreur de sauvegarde : {str(e)}"

    def get_cards_by_type(self, game_name, card_type_folder):
        """Récupère la liste des cartes d'un type spécifique avec leur quantité"""
        type_path = DATA_DIR / game_name / card_type_folder
        if not type_path.exists():
            return []
            
        meta = self._load_deck_metadata(game_name, card_type_folder)
        cards = []
        
        for file_path in sorted(type_path.glob("*.png")):
            if file_path.name == "back.png":
                continue
                
            info = meta.get(file_path.name, {})
            count = info.get("count", 1)
            
            cards.append({
                "name": file_path.stem,
                "filename": file_path.name,
                "path": str(file_path),
                "count": count
            })
        return cards
        
    def delete_card(self, game_name, card_type_folder, card_name):
        """Supprime une carte"""
        filename = f"{card_name}.png"
        file_path = DATA_DIR / game_name / card_type_folder / filename
        try:
            if file_path.exists():
                file_path.unlink()
                
                # Update metadata
                meta = self._load_deck_metadata(game_name, card_type_folder)
                if filename in meta:
                    del meta[filename]
                    self._save_deck_metadata(game_name, card_type_folder, meta)
                    
                return True, "Carte supprimée."
            return False, "Fichier introuvable."
        except Exception as e:
            return False, f"Erreur : {str(e)}"

    def update_card(self, game_name, current_type_folder, card_name, new_name=None, new_type_folder=None, new_count=None):
        """Met à jour une carte (renommage, changement de type, ou quantité)"""
        old_filename = f"{card_name}.png"
        old_path = DATA_DIR / game_name / current_type_folder / old_filename
        
        if not old_path.exists():
            return False, "Carte introuvable."
            
        # Déterminer le dossier cible
        target_folder = new_type_folder if new_type_folder else current_type_folder
        target_dir = DATA_DIR / game_name / target_folder
        
        if not target_dir.exists():
            return False, "Nouveau type de carte introuvable."
            
        # Déterminer le nom cible
        target_name = new_name if new_name else card_name
        sanitized_name = "".join([c for c in target_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        new_filename = f"{sanitized_name}.png"
        new_path = target_dir / new_filename
        
        # Gestion du déplacement/renommage physique
        if new_path != old_path:
            if new_path.exists():
                return False, "Une carte porte déjà ce nom dans la destination."
            try:
                shutil.move(str(old_path), str(new_path))
            except Exception as e:
                return False, f"Erreur déplacer fichier : {str(e)}"

        # Gestion des métadonnées
        # 1. Charger ancien meta
        old_meta = self._load_deck_metadata(game_name, current_type_folder)
        current_data = old_meta.get(old_filename, {"count": 1})
        
        # 2. Mettre à jour la quantité si demandée
        if new_count is not None:
            current_data["count"] = int(new_count)
            
        # 3. Si on change de dossier
        if target_folder != current_type_folder:
            # Supprimer de l'ancien
            if old_filename in old_meta:
                del old_meta[old_filename]
                self._save_deck_metadata(game_name, current_type_folder, old_meta)
            
            # Ajouter au nouveau
            new_meta = self._load_deck_metadata(game_name, target_folder)
            new_meta[new_filename] = current_data
            self._save_deck_metadata(game_name, target_folder, new_meta)
            
        # 4. Si on reste dans le même dossier mais nom change
        elif new_filename != old_filename:
            if old_filename in old_meta:
                del old_meta[old_filename]
            old_meta[new_filename] = current_data
            self._save_deck_metadata(game_name, current_type_folder, old_meta)
            
        # 5. Si juste la quantité change (même dossier, même nom)
        elif new_count is not None:
             old_meta[old_filename] = current_data
             self._save_deck_metadata(game_name, current_type_folder, old_meta)

        return True, "Carte mise à jour avec succès."

    def save_back_image(self, game_name, card_type_folder, image_data):
        """Sauvegarde l'image du dos pour un type de carte"""
        type_path = DATA_DIR / game_name / card_type_folder
        if not type_path.exists():
            return False, "Dossier du type introuvable."
            
        file_path = type_path / "back.png"
        try:
            cv2.imwrite(str(file_path), image_data)
            return True, "Dos de carte sauvegardé !"
        except Exception as e:
            return False, f"Erreur de sauvegarde : {str(e)}"

    def get_back_image_path(self, game_name, card_type_folder):
        """Retourne le chemin du dos de carte s'il existe"""
        path = DATA_DIR / game_name / card_type_folder / "back.png"
        if path.exists():
            return str(path)
        return None
