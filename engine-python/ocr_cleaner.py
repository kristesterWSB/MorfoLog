import pytesseract
from pdf2image import convert_from_path
import os
import glob
import re
from dotenv import load_dotenv

# --- KONFIGURACJA ---
# Te ścieżki muszą być dostosowane do Twojego systemu
POPPLER_PATH = r'C:\poppler-25.12.0\Library\bin'
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --------------------

# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()

# --- PROFIL UŻYTKOWNIKA DO ANONIMIZACJI ---
# Dane są teraz ładowane z pliku .env
USER_PROFILE = {
    "name": os.getenv("USER_NAME"),
    "lastname": os.getenv("USER_LASTNAME"),
    "pesel": os.getenv("USER_PESEL"),
    "address": os.getenv("USER_ADDRESS")
}

class PrivacyGuard:
    """
    Klasa do anonimizacji danych osobowych z surowego tekstu OCR, używająca precyzyjnego zastępowania słów.
    """
    def __init__(self, user_profile: dict):
        self.profile = user_profile

        # Wartości do bezpośredniego, precyzyjnego zastąpienia
        self.direct_values = [
            self.profile.get("name"),
            self.profile.get("lastname"),
            self.profile.get("pesel"),
        ]
        
        # Podziel adres na części, aby usunąć np. samą nazwę ulicy lub miasto
        address = self.profile.get("address", "")
        if address:
            # Usuń przecinki i podziel po spacjach
            address_parts = re.split(r'[\s,]+', address)
            self.direct_values.extend([part for part in address_parts if len(part) > 3 and not part.isdigit()])

        # Usuń puste wpisy (None) i ewentualne duplikaty
        self.direct_values = list(set([v for v in self.direct_values if v]))

    def anonymize(self, page_texts: list[str]) -> str:
        """Działa wieloetapowo, precyzyjnie zastępując słowa i czyszcząc szum tylko na ostatniej stronie."""
        
        processed_pages = []
        num_pages = len(page_texts)

        for i, page_text in enumerate(page_texts):
            is_last_page = (i == num_pages - 1)
            anonymized_text = page_text
            
            # Etap 1: Bezpośrednie zastąpienie precyzyjnych danych (Imię, Nazwisko, PESEL, fragmenty adresu)
            for value in self.direct_values:
                # Użyj \b do dopasowania całych słów, aby uniknąć zastępowania części słów
                pattern = r'\b' + re.escape(value) + r'\b'
                anonymized_text = re.sub(pattern, '[REDACTED]', anonymized_text, flags=re.IGNORECASE)

            # Etap 2: Czyszczenie za pomocą dodatkowych, ogólnych reguł Regex
            # Usuń każdy pozostały 11-cyfrowy ciąg (potencjalny PESEL)
            anonymized_text = re.sub(r'\b\d{11}\b', '[REDACTED_PESEL]', anonymized_text)
            
            # Zastąp słowa-klucze ról (np. "Pacjent:"), a nie całe linie
            anonymized_text = re.sub(r'\b(Pacjent|Odbiorca|Lekarz)\b\s*:?', '[REDACTED_ROLE_INFO]', anonymized_text, flags=re.IGNORECASE)

            # Anonimizuj datę urodzenia - bardziej elastyczny Regex, który obsługuje różne separatory (spacja, kropka, dwukropek)
            anonymized_text = re.sub(r'\bData ur[\s.:]*\n?\d{4}-\d{2}-\d{2}', '[REDACTED_DOB]', anonymized_text, flags=re.IGNORECASE)

            lines = anonymized_text.split('\n')
            current_page_processed_lines = lines

            # Etap 3: Usuwanie linii z metadanymi - TYLKO DLA OSTATNIEJ STRONY
            if is_last_page:
                noise_patterns = [
                    r'przyjęcia prób',
                    r'Data wykonania',
                    r'Data/godz\. wydania',
                    r'DIAGNOSTYKA S\.A\.',
                    r'KREW ŻYLNA',
                    r'Strona:? \d+ z \d+'
                ]
                noise_regex = re.compile('|'.join(noise_patterns), re.IGNORECASE)
                current_page_processed_lines = [line for line in current_page_processed_lines if not noise_regex.search(line)]

            processed_pages.append("\n".join(current_page_processed_lines))

        return "\n".join(processed_pages)

def save_ocr_to_txt(pdf_path):
    """
    Wykonuje OCR na podanym pliku PDF i zapisuje wynik do pliku .txt
    w tym samym folderze.

    Args:
        pdf_path (str): Ścieżka do pliku PDF.
    """
    if not os.path.exists(pdf_path):
        print(f"Błąd: Plik nie istnieje: {pdf_path}")
        return None

    # Ustawienie ścieżki do Tesseracta
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    print(f"Przetwarzanie OCR dla: {os.path.basename(pdf_path)}...")
    try:
        # Konwersja PDF na listę obrazów
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        
        page_texts = []
        # Pętla przez wszystkie strony i wykonanie OCR
        for i, img in enumerate(images):
            print(f"  - Przetwarzanie strony {i + 1}/{len(images)}")
            text = pytesseract.image_to_string(img, lang='pol')
            page_texts.append(text)

        # Zapis całego, surowego tekstu do pliku .txt dla celów logowania
        full_raw_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts)
        # Stwórz folder 'ocr_results' jeśli nie istnieje
        output_dir = os.path.join(os.path.dirname(pdf_path), "../ocr_results")
        os.makedirs(output_dir, exist_ok=True)

        # Stwórz ścieżkę do pliku w nowym folderze
        txt_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".txt"
        txt_path = os.path.join(output_dir, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_raw_text)
            
        print(f"✅ Pomyślnie zapisano wynik OCR do: {txt_path}")
        return page_texts

    except Exception as e:
        print(f"❌ Wystąpił błąd podczas przetwarzania OCR: {e}")
        return None
#tylko do lokalnego sprawdzania rezultatu OCR
if __name__ == "__main__":
    """
    Ten blok zostanie wykonany tylko wtedy, gdy uruchomisz ten plik bezpośrednio
    (np. przez 'python ocr_cleaner.py').
    """
    print("--- Uruchamianie samodzielnego skryptu OCR i Czyszczenia ---")
    # Znajdź folder, w którym znajduje się ten skrypt
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Wyszukaj wszystkie pliki .pdf w tym folderze
    pdf_files = glob.glob(os.path.join(current_dir, "*.pdf"))
    
    print(f"Znaleziono {len(pdf_files)} plików PDF do przetworzenia.")
    
    for pdf_file in pdf_files:
        # Krok 1: Wykonaj OCR i zapisz surowy plik .txt
        page_texts = save_ocr_to_txt(pdf_file)
        
        # Krok 2: Jeśli OCR się powiódł, zanonimizuj tekst i zapisz go do nowego pliku
        if page_texts:
            print(f"--- Anonimizacja wyniku dla: {os.path.basename(pdf_file)} ---")
            guard = PrivacyGuard(USER_PROFILE)
            anonymized_text = guard.anonymize(page_texts)

            # Stwórz folder 'cleaned_results' jeśli nie istnieje
            cleaned_output_dir = os.path.join(current_dir, "../cleaned_results")
            os.makedirs(cleaned_output_dir, exist_ok=True)

            # Stwórz ścieżkę do pliku w nowym folderze
            cleaned_filename = os.path.splitext(os.path.basename(pdf_file))[0] + "_cleaned.txt"
            anonymized_txt_path = os.path.join(cleaned_output_dir, cleaned_filename)
            with open(anonymized_txt_path, "w", encoding="utf-8") as f:
                f.write(anonymized_text)
            print(f"✅ Pomyślnie zapisano zanonimizowany tekst do: {anonymized_txt_path}\n")
        
    print("\n--- Zakończono przetwarzanie wszystkich plików. ---")