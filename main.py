import pandas as pd  # Biblioteka do tabel
import matplotlib.pyplot as plt
import glob
import os
import time
from analyzer import MedicalAnalyzer  # Import nowej klasy
from ocr_cleaner import save_ocr_to_txt, PrivacyGuard, USER_PROFILE # Import klasy i profilu z ocr_cleaner

# Inicjalizacja analizatora (załaduje klucze z .env wewnątrz klasy)
analyzer = MedicalAnalyzer()


def main():
    print("Skanowanie folderu w poszukiwaniu plików PDF...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(current_dir, "*.pdf"))

    print(f"Znaleziono plików: {len(files)}")

    all_results = []

    for file in files:
        # Krok 1: Użyj funkcji z ocr_cleaner.py do OCR
        page_texts = save_ocr_to_txt(file)

        if page_texts:
            # Krok 2: Użyj klasy PrivacyGuard do anonimizacji tekstu
            print(f"--- Anonimizacja wyniku dla: {os.path.basename(file)} ---")
            guard = PrivacyGuard(USER_PROFILE)
            anonymized_text = guard.anonymize(page_texts)

            # Krok 3: Analiza oczyszczonego tekstu przez AI
            # Domyślnie używamy Gemini, w razie błędu przełączy się na xAI
            data = analyzer.analyze_text(anonymized_text, provider='gemini')
            if data:
                # Sprawdź, czy odpowiedź ma oczekiwaną zagnieżdżoną strukturę
                if 'results' in data and isinstance(data.get('results'), dict):
                    # Spłaszcz strukturę: weź słownik 'results' i dodaj do niego datę
                    flat_data = data['results']
                    flat_data['Date'] = data.get('Date')
                    
                    print(f"Pobrane dane (spłaszczone): {flat_data}")
                    all_results.append(flat_data)
                else:
                    print(f"Błąd formatu: Otrzymano dane bez klucza 'results'. Dane: {data}")
            else:
                print(f"Nie udało się pobrać danych z pliku: {os.path.basename(file)}")

        # Przy tekście limity są luźniejsze, wystarczy krótkie opóźnienie
        time.sleep(2)

    # Krok 4: Tworzenie tabeli i wykresów
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