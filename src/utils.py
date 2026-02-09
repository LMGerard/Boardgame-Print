import cv2
import numpy as np

def ordonner_points(pts):
    """Ordonne les 4 points d'un quadrilatère dans l'ordre: haut-gauche, haut-droite, bas-droite, bas-gauche"""
    rect = np.zeros((4, 2), dtype="float32")
    
    # Somme des coordonnées : le haut-gauche a la plus petite, le bas-droite la plus grande
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Différence des coordonnées : le haut-droite a la plus petite, le bas-gauche la plus grande
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def detourer_carte_precise(image, L_mm=60, H_mm=113, ppi=10, seuil=45):
    """
    Détecte et redresse une carte depuis une image
    Args:
        image: Image numpy array (BGR)
        L_mm: Largeur de la carte en mm
        H_mm: Hauteur de la carte en mm
        ppi: Pixels par mm
        seuil: Seuil de binarisation pour la détection
    Returns:
        tuple: (carte_redressée, succès, message)
    """
    orig = image.copy()
    
    # Configuration des dimensions cibles
    dst_w, dst_h = L_mm * ppi, H_mm * ppi

    # Prétraitement pour fond noir
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    _, thresh = cv2.threshold(blurred, seuil, 255, cv2.THRESH_BINARY)
    
    # Détection du contour
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, False, "Aucun contour détecté."
    
    # On prend le plus grand contour (la carte)
    c = max(cnts, key=cv2.contourArea)
    
    # Gestion du trapèze - points extrêmes du contour
    pts_contour = c.reshape(c.shape[0], 2)
    
    # Vérification simple si on a bien trouvé quelque chose qui ressemble à un quadrilatère
    if len(pts_contour) < 4:
         return None, False, "Contour trop petit ou invalide."

    rect_source = ordonner_points(pts_contour.astype("float32"))

    # Correction de Perspective (Warp)
    dst = np.array([
        [0, 0],
        [dst_w - 1, 0],
        [dst_w - 1, dst_h - 1],
        [0, dst_h - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect_source, dst)
    warped = cv2.warpPerspective(orig, M, (dst_w, dst_h))

    # Création du masque pour bords arrondis (Rayon de 3mm)
    rayon_px = int(3 * ppi)
    mask = np.zeros((dst_h, dst_w), dtype="uint8")
    
    # Forme arrondie sur le masque
    cv2.rectangle(mask, (rayon_px, 0), (dst_w - rayon_px, dst_h), 255, -1)
    cv2.rectangle(mask, (0, rayon_px), (dst_w, dst_h - rayon_px), 255, -1)
    
    # Coins avec Anti-Aliasing
    coins = [
        (rayon_px, rayon_px), (dst_w - rayon_px, rayon_px), 
        (rayon_px, dst_h - rayon_px), (dst_w - rayon_px, dst_h - rayon_px)
    ]
    for centre in coins:
        cv2.circle(mask, centre, rayon_px, 255, -1, lineType=cv2.LINE_AA)

    # Assemblage final avec canal Alpha
    b, g, r = cv2.split(warped)
    resultat = cv2.merge([b, g, r, mask])

    return resultat, True, f"Carte détectée ({dst_w}x{dst_h}px)"
