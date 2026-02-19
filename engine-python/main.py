import glob
import os
import time
import json
import re
from analyzer import MedicalAnalyzer  # Import nowej klasy
from ocr_cleaner import PrivacyGuard, USER_PROFILE
from google_vision_ocr import GoogleVisionOCR

# --- KONFIGURACJA ---
SAVE_JSON_ENABLED = True  # Ustaw na False, aby wyłączyć zapisywanie plików JSON
USE_GOOGLE_VISION = True  # ZAWSZE TRUE - Tesseract usunięty
GCP_KEY_PATH = "gcp_key.json"  # Ścieżka do klucza Google Cloud (względem engine-python)


def process_single_file(file_content, vision_ocr_client, analyzer_instance, patient_context=None, original_filename=None):
    """
    Przetwarza pojedynczy plik: OCR -> Anonimizacja -> Analiza AI.
    Zwraca surowy JSON z wynikami (nie spłaszczony).
    Accepts bytes or file path.
    """
    page_texts = []
    
    # Determine if input is file path or bytes
    is_bytes = isinstance(file_content, bytes)
    # Use provided filename for logs, fallback to generic
    file_identifier = original_filename if (is_bytes and original_filename) else ("uploaded_file" if is_bytes else os.path.basename(file_content))

    # Krok 1: Wykonaj OCR (Vision only)
    if vision_ocr_client:
        print(f"Przetwarzanie Google Vision dla: {file_identifier}...")
        # Modified to accept bytes if available
        if is_bytes:
             page_texts = vision_ocr_client.extract_text_from_bytes(file_content)
        else:
             page_texts = vision_ocr_client.extract_text(file_content)
        
        # Ręczny zapis surowego wyniku (dla Vision)
        # Modified: Always save OCR results for debugging, even for bytes input
        if page_texts:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr_results")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename for bytes input if needed
            base_name = os.path.splitext(os.path.basename(file_identifier))[0]
            if is_bytes and file_identifier == "uploaded_file":
                # Use timestamp for unique filename
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = f"upload_{timestamp}"
            
            txt_filename = base_name + ".txt"
            txt_path = os.path.join(output_dir, txt_filename)
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n\n--- PAGE BREAK ---\n\n".join(page_texts))
                print(f"✅ [Vision] Zapisano surowy OCR do: {txt_path}")
            except Exception as e:
                print(f"⚠️ Błąd zapisu OCR: {e}")
    else:
        print("Błąd: Brak klienta Google Vision OCR. Tesseract został usunięty.")
        return None

    if not page_texts:
        return None

    # Krok 2: Użyj klasy PrivacyGuard do anonimizacji tekstu
    print(f"--- Anonimizacja wyniku dla: {file_identifier} ---")
    
    # Konstrukcja profilu na podstawie kontekstu pacjenta (jeśli dostępny)
    # Convert Pydantic model to dict if needed, or access attributes directly
    # Assuming patient_context is Pydantic model
    
    current_profile = USER_PROFILE.copy()
    if patient_context:
        # Check if it's pydantic model or dict
        first_name = getattr(patient_context, 'first_name', None) or patient_context.get('first_name')
        last_name = getattr(patient_context, 'last_name', None) or patient_context.get('last_name')
        dob_fragment = getattr(patient_context, 'dob_fragment', None) or patient_context.get('dob_fragment')
        address = getattr(patient_context, 'address', None) or patient_context.get('address')

        current_profile.update({
            "name": first_name,
            "lastname": last_name,
            "dob_fragment": dob_fragment,
            "address": address
        })
        print(f"Using provided patient context.") # USUNIĘTO PII

    guard = PrivacyGuard(current_profile)
    anonymized_text = guard.anonymize(page_texts)
    
    # Save cleaned (anonymized) text for debugging
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaned_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename logic repeated
    base_name = os.path.splitext(os.path.basename(file_identifier))[0]
    if is_bytes and file_identifier == "uploaded_file":
         import datetime
         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
         base_name = f"upload_{timestamp}"

    txt_filename = base_name + "_cleaned.txt"
    txt_path = os.path.join(output_dir, txt_filename)
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(anonymized_text)
        print(f"✅ Zapisano zanonimizowany tekst do: {txt_path}")
    except Exception as e:
        print(f"⚠️ Błąd zapisu cleaned_results: {e}")

    # Krok 3: Analiza medyczna przez LLM
    print(f"--- Analiza LLM dla: {file_identifier} ---")
    analysis_result = analyzer_instance.analyze_text(anonymized_text)
    
    # Przetwarzanie wyniku
    if analysis_result:
        # Zapisz JSON z wynikami (zawsze włączone dla debugowania)
        if SAVE_JSON_ENABLED:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json_results")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename logic repeated (should refactor, but keeping inline for now)
            base_name = os.path.splitext(os.path.basename(file_identifier))[0]
            if is_bytes and file_identifier == "uploaded_file":
                 import datetime
                 # Reuse timestamp if possible or generate new one (might differ slightly from OCR if heavy load)
                 # Better to pass filename from server.py, but for now unique enough
                 timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                 base_name = f"upload_{timestamp}"

            json_filename = base_name + ".json"
            json_path = os.path.join(output_dir, json_filename)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(analysis_result, f, indent=4, ensure_ascii=False)
                print(f"✅ Zapisano wynik JSON do: {json_path}")
            except Exception as e:
                print(f"⚠️ Błąd zapisu JSON: {e}")

        # Spłaszczanie wyników do tabeli (opcjonalne, zależne od potrzeb)
        # return flat_result if flat_result else analysis_result
        return analysis_result # Zwracamy pełny JSON zgodnie z oczekiwaniami serwera
    
    return None

def main():
    print("Skanowanie folderu w poszukiwaniu plików PDF...")
    # Zmieniono ścieżkę na katalog uploads w root projektu
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    uploads_dir = os.path.join(project_root, "uploads")
    
    # Upewnij się, że katalog uploads istnieje
    if not os.path.exists(uploads_dir):
        print(f"Katalog {uploads_dir} nie istnieje. Tworzę go...")
        os.makedirs(uploads_dir)
        
    files = glob.glob(os.path.join(uploads_dir, "*.pdf"))

    print(f"Znaleziono plików: {len(files)}")

    # Inicjalizacja OCR (jeśli wybrano Google Vision)
    vision_ocr = None
    if USE_GOOGLE_VISION:
        # Ścieżka do klucza GCP względem katalogu engine-python
        key_path = os.path.abspath(os.path.join(current_dir, GCP_KEY_PATH))
        
        # Sprawdzenie czy plik klucza istnieje
        if not os.path.exists(key_path):
            print(f"BŁĄD: Nie znaleziono pliku klucza GCP pod ścieżką: {key_path}")
            print("Upewnij się, że plik gcp_key.json znajduje się w katalogu engine-python.")
            return

        vision_ocr = GoogleVisionOCR(key_path, poppler_path=r'C:\poppler-25.12.0\Library\bin')

    # Inicjalizacja analizatora
    analyzer = MedicalAnalyzer()

    all_results = []

    for file in files:
        data = process_single_file(file, vision_ocr, analyzer)
        
        if data:
            all_results.append(data)
        else:
            print(f"Nie udało się pobrać danych z pliku: {os.path.basename(file)}")

        # Przy tekście limity są luźniejsze, wystarczy krótkie opóźnienie
        time.sleep(2)

    # Krok 4: Wyświetlenie wyników (JSON)
    if not all_results:
        print("Brak danych do analizy.")
        return

    print("\n--- WYNIKI ANALIZY (JSON) ---")
    print(json.dumps(all_results, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()