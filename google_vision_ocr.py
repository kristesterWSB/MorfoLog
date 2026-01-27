import os
import io
from google.cloud import vision
from pdf2image import convert_from_path


class GoogleVisionOCR:
    def __init__(self, service_account_json_path, poppler_path=None):
        """
        Inicjalizuje klienta Google Cloud Vision.
        :param service_account_json_path: Ścieżka do pliku JSON z kluczem konta serwisowego.
        :param poppler_path: Opcjonalna ścieżka do folderu bin popplera (np. C:/poppler/bin).
        """
        if not os.path.exists(service_account_json_path):
            print(f"Ostrzeżenie: Plik klucza '{service_account_json_path}' nie został znaleziony.")
        
        # Ustawienie zmiennej środowiskowej dla uwierzytelniania
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_json_path
        self.client = vision.ImageAnnotatorClient()
        self.poppler_path = poppler_path

    def extract_text(self, file_path):
        """
        Ekstrahuje tekst z pliku PDF lub obrazu.
        :param file_path: Ścieżka do pliku (PDF, JPG, PNG).
        :return: Lista stringów (jeden element na stronę) lub None w przypadku błędu.
        """
        if not os.path.exists(file_path):
            print(f"Błąd: Nie znaleziono pliku {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()
        full_text_parts = []

        try:
            if file_ext == '.pdf':
                # Konwersja PDF na obrazy (w pamięci)
                # Przekazujemy poppler_path jeśli został zdefiniowany
                if self.poppler_path:
                    images = convert_from_path(file_path, poppler_path=self.poppler_path)
                else:
                    images = convert_from_path(file_path)
                
                for image in images:
                    # Konwersja obrazu PIL na bajty
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG')
                    content = img_byte_arr.getvalue()
                    
                    text = self._process_image_content(content)
                    full_text_parts.append(text)

            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                # Odczyt pliku obrazu
                with io.open(file_path, 'rb') as image_file:
                    content = image_file.read()
                
                text = self._process_image_content(content)
                full_text_parts.append(text)
            
            else:
                print(f"Błąd: Nieobsługiwany format pliku: {file_ext}")
                return None

            return full_text_parts

        except Exception as e:
            error_msg = str(e)
            if "poppler" in error_msg.lower():
                print(f"Błąd: Nie znaleziono Popplera. Upewnij się, że jest zainstalowany i dodany do PATH "
                        f"lub podaj ścieżkę w konstruktorze.\nSzczegóły: {error_msg}")
            print(f"Błąd podczas przetwarzania: {error_msg}")
            return None

    def _process_image_content(self, content):
        """
        Wysyła bajty obrazu do Google Vision API i zwraca wykryty tekst.
        """
        image = vision.Image(content=content)
        
        # Używamy document_text_detection dla gęstego tekstu
        response = self.client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Google Vision API Error: {response.error.message}")

        return response.full_text_annotation.text

if __name__ == "__main__":
    # Przykład użycia
    POPPLER_PATH = r'C:\poppler-25.12.0\Library\bin'
    
    # Upewnij się, że plik klucza (gcp_jey.json) znajduje się w tym samym katalogu lub podaj pełną ścieżkę
    ocr = GoogleVisionOCR("gcp_key.json", poppler_path=POPPLER_PATH)
    
    # Przykładowy plik do testów (jeśli istnieje)
    test_file = "wyniki-31_12_25_morfologia.pdf"
    if os.path.exists(test_file):
        text = ocr.extract_text(test_file)
        print(text)
    else:
        print(f"Plik testowy '{test_file}' nie istnieje. Podaj ścieżkę do istniejącego pliku.")
