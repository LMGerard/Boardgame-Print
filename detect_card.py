import cv2
import numpy as np

def debug_show(image, title):
    image = cv2.resize(image.copy(), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.imshow(title, image)
    cv2.waitKey(0)

def ordonner_points(pts):
    # Initialisation du rectangle de 4 points
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

def detourer_carte_precise(image_path, output_path="carte_finale.png"):
    # 1. Chargement de l'image
    img = cv2.imread(image_path)
    if img is None:
        print("Erreur : Image non trouvée.")
        return
    orig = img.copy()
    
    # Configuration des dimensions cibles (60mm x 113mm)
    L_mm, H_mm = 60, 113
    ppi = 10  # 10 pixels par mm
    dst_w, dst_h = L_mm * ppi, H_mm * ppi

    # 2. Prétraitement pour fond noir
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    # On isole la carte (claire) du fond (noir)
    _, thresh = cv2.threshold(blurred, 45, 255, cv2.THRESH_BINARY)
    debug_show(thresh, "Thresh")
    # 3. Détection du contour
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        print("Erreur : Aucun contour détecté.")
        return
    
    # On prend le plus grand contour (la carte)
    c = max(cnts, key=cv2.contourArea)
    
    # --- GESTION DU TRAPÈZE ---
    # On récupère les points extrêmes du contour pour épouser la perspective
    pts_contour = c.reshape(c.shape[0], 2)
    rect_source = ordonner_points(pts_contour.astype("float32"))

    # 4. Correction de Perspective (Warp)
    # On mappe le trapèze de la photo vers un rectangle parfait
    dst = np.array([
        [0, 0],
        [dst_w - 1, 0],
        [dst_w - 1, dst_h - 1],
        [0, dst_h - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect_source, dst)
    warped = cv2.warpPerspective(orig, M, (dst_w, dst_h))

    # 5. Création du masque pour bords arrondis (Rayon de 3mm)
    rayon_px = int(3 * ppi)
    mask = np.zeros((dst_h, dst_w), dtype="uint8")
    
    # On dessine la forme arrondie sur le masque
    cv2.rectangle(mask, (rayon_px, 0), (dst_w - rayon_px, dst_h), 255, -1)
    cv2.rectangle(mask, (0, rayon_px), (dst_w, dst_h - rayon_px), 255, -1)
    
    # Coins avec Anti-Aliasing (bords lisses)
    coins = [
        (rayon_px, rayon_px), (dst_w - rayon_px, rayon_px), 
        (rayon_px, dst_h - rayon_px), (dst_w - rayon_px, dst_h - rayon_px)
    ]
    for centre in coins:
        cv2.circle(mask, centre, rayon_px, 255, -1, lineType=cv2.LINE_AA)

    # 6. Assemblage final avec canal Alpha (transparence)
    b, g, r = cv2.split(warped)
    resultat = cv2.merge([b, g, r, mask])

    # Sauvegarde
    cv2.imwrite(output_path, resultat)
    debug_show(resultat, "Carte detectee")
    print(f"Succès ! Carte redressée enregistrée : {output_path} ({dst_w}x{dst_h}px)")


if __name__ == "__main__":
    detourer_carte_precise(r"C:\Users\lmgd\OneDrive\Bureau\Nouveau dossier (2)\WhatsApp Image 2026-02-09 at 16.27.54 (2).jpeg")
