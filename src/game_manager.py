import os
import io
import json
import boto3
from botocore.config import Config
import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class GameManager:
    def __init__(self):
        self.bucket = os.getenv("CLOUFLARE_R2_BUCKET_NAME")
        if not self.bucket:
             # Fallback ou erreur, mais on suppose .env chargé
             print("Warning: CLOUFLARE_R2_BUCKET_NAME not found")
        
        self.s3 = boto3.client(
            service_name="s3",
            endpoint_url=os.getenv("CLOUFLARE_R2_URL"),
            aws_access_key_id=os.getenv("CLOUFLARE_R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("CLOUFLARE_R2_SECRET_ACCESS_KEY"),
            region_name="auto", # Required for R2
            config=Config(signature_version='s3v4')
        )
        # Prefix racine pour organiser les fichiers
        self.root_prefix = "games/"

    def _get_game_path(self, game_name):
        return f"{self.root_prefix}{game_name}/"

    def get_games(self):
        """Retourne la liste des jeux (dossiers virtuels)"""
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, 
                Prefix=self.root_prefix, 
                Delimiter='/'
            )
            games = []
            if 'CommonPrefixes' in resp:
                for p in resp['CommonPrefixes']:
                    # p['Prefix'] = "games/MyGame/"
                    name = p['Prefix'].rstrip('/').split('/')[-1]
                    if name:
                        games.append(name)
            return games
        except Exception as e:
            print(f"Error get_games: {e}")
            return []

    def create_game(self, game_name):
        sanitized_name = "".join([c for c in game_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not sanitized_name:
            return False, "Nom invalide."
            
        key = f"{self._get_game_path(sanitized_name)}config.json"
        
        # Check exists (via list ou head)
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return False, "Ce jeu existe déjà."
        except:
            pass # N'existe pas
        
        # Init config
        initial_config = {"card_types": {}}
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(initial_config, indent=4),
                ContentType='application/json'
            )
            return True, f"Jeu '{sanitized_name}' créé !"
        except Exception as e:
            return False, f"Erreur S3: {str(e)}"

    def _get_config_key(self, game_name):
        return f"{self.root_prefix}{game_name}/config.json"

    def _load_config(self, game_name):
        key = self._get_config_key(game_name)
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp['Body'].read().decode('utf-8'))
        except:
            return {"card_types": {}}

    def _save_config(self, game_name, config):
        key = self._get_config_key(game_name)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(config, indent=4),
            ContentType='application/json'
        )

    def add_card_type(self, game_name, type_name, width_mm, height_mm):
        config = self._load_config(game_name)
        sanitized_type = "".join([c for c in type_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        if sanitized_type in config.get("card_types", {}):
            return False, "Ce type existe déjà."
            
        # On ne crée pas de dossier physique en S3, juste la config
        config["card_types"][sanitized_type] = {
            "name": type_name,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "folder": sanitized_type
        }
        self._save_config(game_name, config)
        return True, f"Type '{type_name}' ajouté."

    def get_card_types(self, game_name):
        config = self._load_config(game_name)
        return config.get("card_types", {})

    # --- METADATA (cards.json dans le "dossier" du deck) ---
    def _get_meta_key(self, game_name, deck_folder):
        return f"{self.root_prefix}{game_name}/{deck_folder}/cards.json"

    def _load_deck_metadata(self, game_name, deck_folder):
        key = self._get_meta_key(game_name, deck_folder)
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp['Body'].read().decode('utf-8'))
        except:
            return {}

    def _save_deck_metadata(self, game_name, deck_folder, data):
        key = self._get_meta_key(game_name, deck_folder)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType='application/json'
        )

    def save_card(self, game_name, card_type_folder, card_image, card_name=None, count=1):
        # 1. Nom fichier
        if not card_name:
            # On liste pour compter (approximatif mais ok)
            prefix = f"{self.root_prefix}{game_name}/{card_type_folder}/"
            try:
                objs = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
                cnt = objs.get('KeyCount', 0)
            except:
                cnt = 0
            card_name = f"carte_{cnt+1:03d}"
            
        sanitized = "".join([c for c in card_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{sanitized}.png"
        key = f"{self.root_prefix}{game_name}/{card_type_folder}/{filename}"
        
        # 2. Upload Image
        try:
            success, encoded_img = cv2.imencode('.png', card_image)
            if not success:
                return False, "Erreur encodage image."
                
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=encoded_img.tobytes(),
                ContentType='image/png'
            )
            
            # 3. Metadata
            meta = self._load_deck_metadata(game_name, card_type_folder)
            meta[filename] = {"count": int(count)}
            self._save_deck_metadata(game_name, card_type_folder, meta)
            
            return True, f"Carte sauvée : {filename}"
        except Exception as e:
            return False, f"Erreur S3: {str(e)}"

    def get_cards_by_type(self, game_name, card_type_folder):
        prefix = f"{self.root_prefix}{game_name}/{card_type_folder}/"
        meta = self._load_deck_metadata(game_name, card_type_folder)
        
        try:
            resp = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        except:
            return []
            
        cards = []
        if 'Contents' in resp:
            for obj in resp['Contents']:
                key = obj['Key']
                filename = key.split('/')[-1]
                if not filename.endswith('.png') or filename == "back.png":
                    continue
                    
                # Generate Presigned URL
                url = self.s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=3600
                )
                
                info = meta.get(filename, {})
                c_val = info.get("count", 1)
                
                cards.append({
                    "name": filename.replace('.png', ''),
                    "filename": filename,
                    "path": url,      # URL pour Streamlit
                    "s3_key": key,    # Key pour operations internes
                    "count": c_val
                })
        
        # Sort by filename
        cards.sort(key=lambda x: x['filename'])
        return cards

    def delete_card(self, game_name, card_type_folder, card_name):
        filename = f"{card_name}.png"
        key = f"{self.root_prefix}{game_name}/{card_type_folder}/{filename}"
        
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            
            # Update meta
            meta = self._load_deck_metadata(game_name, card_type_folder)
            if filename in meta:
                del meta[filename]
                self._save_deck_metadata(game_name, card_type_folder, meta)
                
            return True, "Supprimé."
        except Exception as e:
            return False, f"Erreur: {str(e)}"

    def update_card(self, game_name, current_type_folder, card_name, new_name=None, new_type_folder=None, new_count=None):
        old_filename = f"{card_name}.png"
        old_key = f"{self.root_prefix}{game_name}/{current_type_folder}/{old_filename}"
        
        target_folder = new_type_folder if new_type_folder else current_type_folder
        target_name = new_name if new_name else card_name
        sanitized = "".join([c for c in target_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        new_filename = f"{sanitized}.png"
        new_key = f"{self.root_prefix}{game_name}/{target_folder}/{new_filename}"
        
        # Check if change needed
        move_file = (new_key != old_key)
        
        try:
            if move_file:
                # Copy object
                copy_source = {'Bucket': self.bucket, 'Key': old_key}
                self.s3.copy_object(CopySource=copy_source, Bucket=self.bucket, Key=new_key)
                # Delete old
                self.s3.delete_object(Bucket=self.bucket, Key=old_key)
            
            # Update Metadata logic
            # 1. Load old meta
            old_meta = self._load_deck_metadata(game_name, current_type_folder)
            current_data = old_meta.get(old_filename, {"count": 1})
            
            if new_count is not None:
                current_data["count"] = int(new_count)
                
            if target_folder != current_type_folder:
                # Remove from old
                if old_filename in old_meta:
                    del old_meta[old_filename]
                    self._save_deck_metadata(game_name, current_type_folder, old_meta)
                # Add to new
                new_meta = self._load_deck_metadata(game_name, target_folder)
                new_meta[new_filename] = current_data
                self._save_deck_metadata(game_name, target_folder, new_meta)
                
            elif new_filename != old_filename:
                # Same folder, rename
                if old_filename in old_meta:
                    del old_meta[old_filename]
                old_meta[new_filename] = current_data
                self._save_deck_metadata(game_name, current_type_folder, old_meta)
                
            elif new_count is not None:
                # Just count update
                old_meta[old_filename] = current_data
                self._save_deck_metadata(game_name, current_type_folder, old_meta)
                
            return True, "Mis à jour."
            
        except Exception as e:
            return False, f"Erreur update S3: {str(e)}"

    def save_back_image(self, game_name, card_type_folder, image_data):
        key = f"{self.root_prefix}{game_name}/{card_type_folder}/back.png"
        try:
            success, encoded_img = cv2.imencode('.png', image_data)
            if success:
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=encoded_img.tobytes(),
                    ContentType='image/png'
                )
                return True, "Dos enregistré."
            return False, "Erreur encode."
        except Exception as e:
            return False, str(e)

    def get_back_image_path(self, game_name, card_type_folder):
        """Retourne une URL presignée pour le dos"""
        key = f"{self.root_prefix}{game_name}/{card_type_folder}/back.png"
        # Check existence via head
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=3600
            )
            return url
        except:
            return None
