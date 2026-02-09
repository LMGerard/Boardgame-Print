# 🎴 Détection et Détourage de Cartes de Jeu

Scripts Python pour détecter et détourer automatiquement des cartes de jeu scannées.

## 📋 Scripts Disponibles

### 1. `detect_card_sam.py` ⭐ **RECOMMANDÉ**
Utilise **SAM (Segment Anything Model)** de Meta AI via Hugging Face.

**Avantages:**
- ✅ Détection ultra-précise grâce à l'IA
- ✅ Fonctionne avec n'importe quel fond
- ✅ Gère les ombres et reflets
- ✅ Segmentation au pixel près

**Installation:**
```bash
pip install -r requirements_sam.txt
```

**Utilisation:**
```bash
python detect_card_sam.py
```

**Note:** Le modèle (~350MB) sera téléchargé automatiquement lors de la première utilisation.

---

### 2. `detect_card_ai.py`
Utilise des techniques de Computer Vision avancées (sans modèle lourd).

**Avantages:**
- ✅ Pas de téléchargement de modèle
- ✅ Plus rapide
- ✅ Fonctionne bien sur des scans propres

**Installation:**
```bash
pip install opencv-python numpy pillow
```

**Utilisation:**
```bash
python detect_card_ai.py
```

---

## 🚀 Guide Rapide

### Installation des dépendances

**Pour SAM (recommandé):**
```bash
cd "c:/Developpement/Boardgame Print"
.venv/Scripts/activate  # Si vous utilisez un environnement virtuel
pip install -r requirements_sam.txt
```

**Pour la version légère:**
```bash
pip install opencv-python numpy pillow
```

### Utilisation

1. Lancez le script de votre choix
2. Sélectionnez votre image scannée
3. Le script détecte automatiquement la carte
4. La carte détourée est affichée
5. Appuyez sur une touche pour sauvegarder

### Format de sortie

Les cartes détourées sont sauvegardées au format PNG avec le suffixe:
- `_sam_card.png` pour SAM
- `_ai_card.png` pour la version AI classique

---

## 💡 Conseils pour de meilleurs résultats

### Pour le scan
- ✅ Placez la carte sur un fond uni (blanc, noir, ou couleur unie)
- ✅ Assurez-vous d'un bon éclairage uniforme
- ✅ Évitez les ombres portées
- ✅ La carte doit être bien à plat

### Si la détection échoue
- Essayez avec un fond différent
- Améliorez l'éclairage
- Assurez-vous que la carte occupe au moins 20% de l'image
- Utilisez SAM pour les cas difficiles

---

## 🔧 Configuration Système

### Minimum requis
- Python 3.8+
- 4 GB RAM
- 2 GB espace disque (pour les modèles)

### Recommandé pour SAM
- Python 3.10+
- 8 GB RAM
- GPU NVIDIA avec CUDA (optionnel, accélère le traitement)
- 5 GB espace disque

---

## 📊 Comparaison des méthodes

| Critère | SAM | CV Classique |
|---------|-----|--------------|
| Précision | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Vitesse | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Robustesse | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Taille | ~350 MB | ~50 MB |
| GPU requis | Non (mais +rapide) | Non |

---

## 🐛 Dépannage

### Erreur: "Module 'transformers' not found"
```bash
pip install transformers torch torchvision
```

### Erreur: "CUDA out of memory"
Le modèle SAM utilise le CPU par défaut. Si vous avez un GPU mais pas assez de VRAM, c'est normal.

### La détection ne trouve pas la carte
- Vérifiez que la carte contraste bien avec le fond
- Essayez d'augmenter la taille de la carte dans l'image
- Utilisez SAM qui est plus robuste

### Erreur numpy "int0"
Mettez à jour numpy:
```bash
pip install --upgrade numpy
```

---

## 📝 Exemples d'utilisation

### Traiter plusieurs cartes
```python
import glob
import subprocess

for image in glob.glob("*.jpg"):
    subprocess.run(["python", "detect_card_sam.py", image])
```

### Personnaliser la sortie
Modifiez la ligne de sauvegarde dans le script:
```python
cv2.imwrite(output, card, [cv2.IMWRITE_PNG_COMPRESSION, 9])
# 9 = compression maximale, 0 = aucune compression
```

---

## 📚 Ressources

- [SAM Paper](https://arxiv.org/abs/2304.02643)
- [Hugging Face SAM](https://huggingface.co/facebook/sam-vit-base)
- [OpenCV Documentation](https://docs.opencv.org/)

---

## 🎯 Prochaines améliorations possibles

- [ ] Traitement par lot (batch processing)
- [ ] Interface graphique (GUI)
- [ ] Détection automatique de l'orientation
- [ ] Correction automatique des couleurs
- [ ] Export en PDF multi-pages

---

**Créé avec ❤️ pour faciliter la numérisation de cartes de jeu de société**
