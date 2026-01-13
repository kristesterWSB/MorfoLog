import pytesseract
from pdf2image import convert_from_path
import os
import glob
import re

# --- KONFIGURACJA ---
# Te ścieżki muszą być dostosowane do Twojego systemu
POPPLER_PATH = r'C:\poppler-25.12.0\Library\bin'
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --------------------

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
        
        full_text = ""
        # Pętla przez wszystkie strony i wykonanie OCR
        for i, img in enumerate(images):
            print(f"  - Przetwarzanie strony {i + 1}/{len(images)}")
            text = pytesseract.image_to_string(img, lang='pol')
            full_text += text + "\n"

        # Zapis do pliku .txt
        # Stwórz folder 'ocr_results' jeśli nie istnieje
        output_dir = os.path.join(os.path.dirname(pdf_path), "ocr_results")
        os.makedirs(output_dir, exist_ok=True)

        # Stwórz ścieżkę do pliku w nowym folderze
        txt_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".txt"
        txt_path = os.path.join(output_dir, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print(f"✅ Pomyślnie zapisano wynik OCR do: {txt_path}")
        return full_text

    except Exception as e:
        print(f"❌ Wystąpił błąd podczas przetwarzania OCR: {e}")
        return None


def clean_medical_ocr(raw_text: str) -> str:
    """
    Oczyszcza surowy tekst z OCR wyników badań krwi (Diagnostyka),
    wyodrębniając datę i kluczowe parametry morfologii.

    Args:
        raw_text: Surowy string z OCR.

    Returns:
        Czysty string z datą i przefiltrowanymi wynikami lub komunikat o błędzie.
    """
    # 1. Znajdź datę badania za pomocą Regex
    # Uogólniony Regex, który obsługuje "Data/godz. pobrania" oraz "Data pobrania" z opcjonalnym dwukropkiem
    date_match = re.search(r"Data(?:/godz\.)?\s*pobrania\s*:?\s*(\d{4}-\d{2}-\d{2})", raw_text, re.IGNORECASE)
    if not date_match:
        return "Błąd: Nie znaleziono daty badania we wzorcu 'Data pobrania: RRRR-MM-DD'."
    
    date_str = date_match.group(1)

    # 2. Wyodrębnij TYLKO sekcję "Morfologia krwi"
    # Znajdź linię nagłówka, aby ją zachować
    morphology_header_match = re.search(r"^\s*(Morfologia krwi.*)", raw_text, re.MULTILINE | re.IGNORECASE)
    if not morphology_header_match:
        return f"Data badania: {date_str}\nBłąd: Nie znaleziono sekcji 'Morfologia krwi'."

    morphology_header_line = morphology_header_match.group(1).strip()

    # Weź tekst od początku sekcji morfologii
    text_from_morphology = raw_text[morphology_header_match.start():]

    # Znajdź koniec sekcji (początek następnego dużego badania)
    next_section_match = re.search(r"\n\s*(OB|Badanie ogólne moczu|Rozmaz krwi|Biochemia|Koagulologia|Immunochemia)", text_from_morphology, re.IGNORECASE)

    if next_section_match:
        # Jeśli znaleziono następną sekcję, utnij tekst w tym miejscu
        morphology_section = text_from_morphology[:next_section_match.start()]
    else:
        # W przeciwnym razie, bierzemy wszystko do końca
        morphology_section = text_from_morphology

    # 3. & 4. Wewnątrz sekcji przefiltruj linie, zachowując kluczowe parametry
    keywords = [
        "Leukocyty", "Erytrocyty", "Hemoglobina", "Hematokryt", "MCV", "MCH", "MCHC", 
        "Płytki krwi", "RDW", "PDW", "MPV", "P-LCR", "PCT", "Neutrofile", "Limfocyty", 
        "Monocyty", "Eozynofile", "Bazofile", "Niedojrzałe granulocyty", "NRBC"
    ]

    clean_lines = []
    for line in morphology_section.split('\n'):
        stripped_line = line.strip()
        # Sprawdź, czy linia zaczyna się od jednego ze słów kluczowych
        if any(stripped_line.startswith(kw) for kw in keywords):
            clean_lines.append(stripped_line)

    if not clean_lines:
        return f"Data badania: {date_str}\nBłąd: Nie znaleziono żadnych wyników morfologii w wyodrębnionej sekcji."

    # 5. Zwróć czysty string
    final_output = [f"Data badania: {date_str}"]
    final_output.append(morphology_header_line)
    final_output.extend(clean_lines)
    
    return "\n".join(final_output)


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
        raw_text = save_ocr_to_txt(pdf_file)
        
        # Krok 2: Jeśli OCR się powiódł, oczyść tekst i zapisz go do nowego pliku
        if raw_text:
            print(f"--- Czyszczenie wyniku dla: {os.path.basename(pdf_file)} ---")
            cleaned_text = clean_medical_ocr(raw_text)

            # Stwórz folder 'cleaned_results' jeśli nie istnieje
            cleaned_output_dir = os.path.join(current_dir, "cleaned_results")
            os.makedirs(cleaned_output_dir, exist_ok=True)

            # Stwórz ścieżkę do pliku w nowym folderze
            cleaned_filename = os.path.splitext(os.path.basename(pdf_file))[0] + "_cleaned.txt"
            cleaned_txt_path = os.path.join(cleaned_output_dir, cleaned_filename)
            with open(cleaned_txt_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)
            print(f"✅ Pomyślnie zapisano oczyszczony tekst do: {cleaned_txt_path}\n")
        
    print("\n--- Zakończono przetwarzanie wszystkich plików. ---")