from fpdf import FPDF
import math
import os

class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(False)
        self.margin = 10
        self.page_w = 210
        self.page_h = 297

    def add_deck_section(self, cards_data):
        """
        Ajoute une section au PDF pour un groupe de cartes de même dimension.
        cards_data: liste de dict {'front': path, 'back': path, 'width': mm, 'height': mm}
        """
        if not cards_data:
            return

        # Récupérer les dimensions du premier élément
        card_w = cards_data[0]['width']
        card_h = cards_data[0]['height']
        
        # Calcul de la grille
        usable_w = self.page_w - (2 * self.margin)
        usable_h = self.page_h - (2 * self.margin)
        
        cols = int(usable_w // card_w)
        rows = int(usable_h // card_h)
        
        if cols == 0 or rows == 0:
            # Skip if impossible to fit
            return 
            
        items_per_page = cols * rows
        
        # Calcul de l'espacement pour centrer la grille
        total_grid_w = cols * card_w
        total_grid_h = rows * card_h
        start_x = self.margin + (usable_w - total_grid_w) / 2
        start_y = self.margin + (usable_h - total_grid_h) / 2
        
        total_cards = len(cards_data)
        num_pages_pairs = math.ceil(total_cards / items_per_page)
        
        for i in range(num_pages_pairs):
            batch = cards_data[i*items_per_page : (i+1)*items_per_page]
            
            # --- PAGE RECTO (Fronts) ---
            self.add_page()
            
            # Utiliser la police standard pour debug si besoin, mais ici images pures
            
            # Placer les cartes
            for idx, card in enumerate(batch):
                r = (idx // cols) % rows
                c = idx % cols
                
                x = start_x + (c * card_w)
                y = start_y + (r * card_h)
                
                # Image Front
                if os.path.exists(card['front']):
                    try:
                        self.image(card['front'], x=x, y=y, w=card_w, h=card_h)
                    except:
                        pass # Si image invalide
                    
                    # Cadre léger de coupe
                    self.set_draw_color(200, 200, 200)
                    self.rect(x, y, card_w, card_h)

            # --- PAGE VERSO (Backs) ---
            self.add_page()
            
            for idx, card in enumerate(batch):
                r = (idx // cols) % rows
                c = idx % cols
                
                # MIROIR HORIZONTAL pour verso
                # Col_Back = (Cols - 1) - c
                c_back = (cols - 1) - c
                
                x = start_x + (c_back * card_w)
                y = start_y + (r * card_h)
                
                back_path = card.get('back')
                if back_path and os.path.exists(back_path):
                    try:
                        self.image(back_path, x=x, y=y, w=card_w, h=card_h)
                    except:
                        pass
                
                # Cadre léger
                self.set_draw_color(200, 200, 200)
                self.rect(x, y, card_w, card_h)

    def save(self, output_path):
        try:
            self.output(output_path)
            return True, f"PDF généré : {os.path.basename(output_path)}"
        except Exception as e:
            return False, f"Erreur génération PDF : {str(e)}"
