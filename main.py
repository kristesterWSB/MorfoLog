import pytesseract
from pdf2image import convert_from_path
import pandas as pd  # Biblioteka do tabel
import matplotlib.pyplot as plt
import glob
import os
import re
import time
from analyzer import MedicalAnalyzer  # Import nowej klasy

# Inicjalizacja analizatora (załaduje klucze z .env wewnątrz klasy)
analyzer = MedicalAnalyzer()

# KONFIGURACJA ŚCIEŻEK
POPPLER_PATH = r'C:\poppler-25.12.0\Library\bin'
# Ścieżka do Tesseract OCR (dostosuj jeśli zainstalowałeś w innym miejscu)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Konfiguracja anonimizacji
USER_NAME_TO_REDACT = "GARUS KRZYSZTOF"  # <--- WPISZ SWOJE IMIĘ I NAZWISKO DO USUNIĘCIA


def extract_and_clean_text(pdf_path):
    """
    1. Konwertuje PDF na obrazy.
    2. Wykonuje OCR (Tesseract) aby uzyskać tekst.
    3. Anonimizuje dane wrażliwe (PESEL, Telefon, Nazwisko) używając Regex.
    """
    print(f"Przetwarzam: {pdf_path}...")
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        full_text = ""
        
        # Krok 1: OCR
        for img in images:
            # Używamy języka polskiego dla lepszego rozpoznawania
            text = pytesseract.image_to_string(img, lang='pol')
            full_text += text + "\n"

        # Krok 2: Anonimizacja (Regex)
        # Usuwanie PESEL (11 cyfr)
        full_text = re.sub(r'\b\d{11}\b', '[REDACTED_PESEL]', full_text)
        # Usuwanie numerów telefonów (formaty: 123-456-789, 123 456 789, +48...)
        full_text = re.sub(r'(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{3}(?!\d)', '[REDACTED_PHONE]', full_text)
        # Usuwanie imienia i nazwiska zdefiniowanego w konfiguracji
        if USER_NAME_TO_REDACT:
            full_text = re.sub(re.escape(USER_NAME_TO_REDACT), '[REDACTED_NAME]', full_text, flags=re.IGNORECASE)

        print(f"--- WYNIK OCR (po anonimizacji) ---\n{full_text}\n-----------------------------------")
        return full_text
    except Exception as e:
        print(f"Błąd OCR/Anonimizacji: {e}")
        return None


def main():
    print("Skanowanie folderu w poszukiwaniu plików PDF...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(current_dir, "*.pdf"))

    print(f"Znaleziono plików: {len(files)}")

    all_results = []

    for file in files:
        # 1. Lokalny OCR i Anonimizacja
        clean_text = extract_and_clean_text(file)

        # 2. Analiza tekstu przez AI
        if clean_text:
            # Domyślnie używamy Gemini, w razie błędu przełączy się na xAI
            data = analyzer.analyze_text(clean_text, provider='gemini')
            if data:
                print(f"Pobrane dane: {data}")
                all_results.append(data)
            else:
                print(f"Nie udało się pobrać danych z pliku: {os.path.basename(file)}")

        # Przy tekście limity są luźniejsze, wystarczy krótkie opóźnienie
        time.sleep(2)

    # 3. Tworzenie tabeli i wykresów
    if not all_results:
        print("Brak danych do analizy.")
        return

    df = pd.DataFrame(all_results)

    # Konwersja kolumn liczbowych (wszystkie poza datą)
    for col in df.columns:
        if col != 'Date':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print("\n--- ZESTAWIENIE WYNIKÓW ---")
    print(df.to_string(index=False))

    if df.empty or len(df) < 2:
        print("\n[!] Potrzebne są co najmniej dwa badania z różnymi datami, aby narysować trendy.")
        return

    # Sortowanie po dacie
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')

    # Lista kolumn do narysowania (wszystkie poza datą)
    parameters_to_plot = [col for col in df.columns if col != 'Date']

    # Filtrujemy tylko te, które mają jakieś dane (nie same NaN)
    parameters_to_plot = [col for col in parameters_to_plot if df[col].notna().any()]

    # Tworzymy tyle wykresów, ile mamy parametrów (jeden pod drugim)
    fig, axes = plt.subplots(nrows=len(parameters_to_plot), ncols=1, figsize=(10, 4 * len(parameters_to_plot)))

    if len(parameters_to_plot) == 1:
        axes = [axes]

    for ax, param in zip(axes, parameters_to_plot):
        # Rysujemy tylko punkty, gdzie są dane (dropna)
        subset = df.dropna(subset=[param])
        ax.plot(subset['Date'], subset[param], marker='o', linestyle='-', color='teal', linewidth=2)

        ax.set_title(f'Trend parametru: {param}', fontsize=12)
        ax.set_ylabel('Wartość')
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.tick_params(axis='x', rotation=30)

    plt.tight_layout()  # Żeby wykresy na siebie nie najeżdżały
    plt.show()


if __name__ == "__main__":
    main()