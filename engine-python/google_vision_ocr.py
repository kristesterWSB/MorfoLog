import os
import io
from google.cloud import vision
from pdf2image import convert_from_path
from collections import defaultdict

class GoogleVisionOCR:
    def __init__(self, key_path, poppler_path=None):
        """
        Inicjalizuje klienta Google Vision API.
        :param key_path: Ścieżka do pliku JSON z kluczem konta serwisowego.
        :param poppler_path: Ścieżka do binariów Poppler (wymagane dla PDF).
        """
        self.client = vision.ImageAnnotatorClient.from_service_account_json(key_path)
        self.poppler_path = poppler_path

    def extract_text(self, file_path):
        """
        Główna metoda: obsługuje pliki PDF i obrazy, zwraca listę stron (tekst).
        """
        if not os.path.exists(file_path):
            print(f"Błąd: Nie znaleziono pliku {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()
        pages_text = []

        try:
            if file_ext == '.pdf':
                if not self.poppler_path:
                    print("Ostrzeżenie: Brak ścieżki do Poppler. Obsługa PDF może nie działać.")
                
                # Konwersja PDF na obrazy
                images = convert_from_path(file_path, poppler_path=self.poppler_path)
                
                for img in images:
                    # Konwersja PIL Image na bytes
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG')
                    content = img_byte_arr.getvalue()
                    
                    # Przetwarzanie obrazu
                    text = self._process_image_content(content)
                    pages_text.append(text)

            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                with open(file_path, "rb") as image_file:
                    content = image_file.read()
                
                text = self._process_image_content(content)
                pages_text.append(text)
            
            else:
                print(f"Błąd: Nieobsługiwany format pliku: {file_ext}")
                return None

            return pages_text

        except Exception as e:
            print(f"Błąd podczas przetwarzania Vision API: {e}")
            return None

    def _process_image_content(self, image_content):
        image = vision.Image(content=image_content)
        # Używamy document_text_detection, bo zwraca gęstą strukturę
        response = self.client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f'{response.error.message}')

        # Używamy nowej funkcji rekonstrukcji geometrii
        return self.reconstruct_text_from_geometry(response)

    def reconstruct_text_from_geometry(self, response, y_tolerance=10):
        """
        Sortuje słowa po ich fizycznym położeniu (Y), ignorując "inteligentne"
        grupowanie bloków przez Google, które psuje tabele.
        """
        words = []
        
        # 1. Wyciągnij wszystkie słowa ze struktur Google'a
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = "".join([symbol.text for symbol in word.symbols])
                        
                        vs = word.bounding_box.vertices
                        ys = [v.y for v in vs if v.y is not None]
                        xs = [v.x for v in vs if v.x is not None]
                        
                        if not ys or not xs: continue
                            
                        min_y, max_y = min(ys), max(ys)
                        min_x = min(xs)
                        center_y = (min_y + max_y) / 2
                        
                        words.append({"text": word_text, "y": center_y, "x": min_x, "height": max_y - min_y})

        if not words: return ""

        # 2. Sortowanie zgrubne po Y
        words.sort(key=lambda w: w["y"])

        # 3. Grupowanie w wiersze (Line Clustering)
        lines = []
        current_line = []
        if words:
            current_line_y = words[0]["y"]
            current_line.append(words[0])
            
        for word in words[1:]:
            tolerance = max(10, word["height"] * 0.6) 
            if abs(word["y"] - current_line_y) <= tolerance:
                current_line.append(word)
            else:
                current_line.sort(key=lambda w: w["x"])
                lines.append(" ".join([w["text"] for w in current_line]))
                current_line = [word]
                current_line_y = word["y"]
        
        if current_line:
            current_line.sort(key=lambda w: w["x"])
            lines.append(" ".join([w["text"] for w in current_line]))

        return "\n".join(lines)