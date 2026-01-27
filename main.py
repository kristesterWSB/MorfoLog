import pandas as pd  # Biblioteka do tabel
import matplotlib.pyplot as plt
import glob
import os
import time
import json
import re
from analyzer import MedicalAnalyzer  # Import nowej klasy
from ocr_cleaner import PrivacyGuard, USER_PROFILE, save_ocr_to_txt
from google_vision_ocr import GoogleVisionOCR

# --- KONFIGURACJA ---
SAVE_JSON_ENABLED = True  # Ustaw na False, aby wyłączyć zapisywanie plików JSON
USE_GOOGLE_VISION = True  # True = Google Vision API, False = Tesseract (lokalny)
GCP_KEY_PATH = "gcp_key.json" # Ścieżka do klucza Google Cloud

# Inicjalizacja analizatora (załaduje klucze z .env wewnątrz klasy)
analyzer = MedicalAnalyzer()

# Mapa do normalizacji jednostek - standaryzuje popularne warianty i błędy OCR
UNIT_NORMALIZATION_MAP = {
    "min/ul": "mln/ul",
    "f": "fl",
    "fi": "fl",
    "fI": "fl",
    "UI": "U/l",
    "UJ": "U/l",
    "pe": "pg",   # Naprawa błędu AI (pg* -> pe)
    "pg*": "pg",  # Na wypadek gdyby AI przepuściło gwiazdkę
}

# Mapa do normalizacji nazw parametrów - standaryzuje popularne błędy OCR
PARAMETER_NAME_NORMALIZATION_MAP = {
    "NRBC$": "NRBC",
    "NRBCH": "NRBC",
    "NRBC #": "NRBC",
    "NRBC%" : "NRBC",
    "NRBC %" : "NRBC"
}


def _flatten_lab_results(data: dict) -> dict | None:
    """
    Spłaszcza zagnieżdżoną strukturę JSON z wynikami badań do płaskiego słownika.
    Tworzy unikalne klucze dla parametrów, łącząc nazwę z jednostką (np. "Neutrofile [%]").
    """
    # Sprawdź, czy odpowiedź ma nową, zagnieżdżoną strukturę
    if 'meta' not in data or 'examinations' not in data:
        print(f"Błąd formatu: Otrzymano dane bez klucza 'meta' lub 'examinations'. Dane: {data}")
        return None

    # Pobierz datę z zagnieżdżonego obiektu 'meta'
    flat_data = {'Date': data.get('meta', {}).get('date_examination')}

    for section in data.get('examinations', []):
        section_name = section.get('examination_name', 'Inne')
        # Czyścimy nazwę sekcji z kodów ICD-9, aby tytuły wykresów były ładniejsze
        clean_section_name = re.sub(r'\s*\(ICD-9:.*\)', '', section_name).strip()

        for result in section.get('results', []):
            if isinstance(result, dict) and 'name' in result and 'value' in result:
                param_name = result['name']
                
                # --- NOWOŚĆ: Czyszczenie nazwy parametru z jednostek w nawiasach ---
                # Usuwa: [%], (%), [#], (#), [tys/ul] itp. z końca nazwy
                param_name = re.sub(r'\s*[\[\(].*?[\]\)]$', '', param_name).strip()

                # Normalizacja nazwy parametru
                normalized_param_name = PARAMETER_NAME_NORMALIZATION_MAP.get(param_name, param_name)

                param_value = result['value']
                param_unit = result.get('unit')
                param_flag = result.get('flag')
                param_min = result.get('range_min')
                param_max = result.get('range_max')
                if param_flag:
                    param_flag = param_flag.strip()

                # Czyszczenie jednostki z artefaktów OCR przed normalizacją
                cleaned_unit = None
                if param_unit:
                    cleaned_unit = re.sub(r'[\*$\s]', '', param_unit)  # Usuwa znaki *, $ i białe znaki

                # Normalizacja jednostki
                normalized_unit = UNIT_NORMALIZATION_MAP.get(cleaned_unit, cleaned_unit)

                # Tworzenie unikalnego klucza, aby uniknąć nadpisywania (np. "Neutrofile [%]").
                # To kluczowe dla parametrów o tej samej nazwie ale różnych jednostkach.
                # Dodajemy nazwę sekcji dla lepszej czytelności na wykresach.
                base_key = f"{clean_section_name} - {normalized_param_name}"
                unique_key = f"{base_key} [{normalized_unit}]" if normalized_unit else base_key
                flat_data[unique_key] = param_value
                if param_flag:
                    flat_data[f"{unique_key}_flag"] = param_flag
                if param_min is not None:
                    flat_data[f"{unique_key}_min"] = param_min
                if param_max is not None:
                    flat_data[f"{unique_key}_max"] = param_max

    return flat_data


def main():
    print("Skanowanie folderu w poszukiwaniu plików PDF...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(current_dir, "*.pdf"))

    print(f"Znaleziono plików: {len(files)}")

    # Inicjalizacja OCR (jeśli wybrano Google Vision)
    vision_ocr = None
    if USE_GOOGLE_VISION:
        vision_ocr = GoogleVisionOCR(GCP_KEY_PATH, poppler_path=r'C:\poppler-25.12.0\Library\bin')

    all_results = []

    for file in files:
        page_texts = []
        
        # Krok 1: Wykonaj OCR (Vision lub Tesseract)
        if USE_GOOGLE_VISION:
            print(f"Przetwarzanie Google Vision dla: {os.path.basename(file)}...")
            page_texts = vision_ocr.extract_text(file)
            
            # Ręczny zapis surowego wyniku (dla Vision), bo save_ocr_to_txt robił to automatycznie dla Tesseracta
            if page_texts:
                raw_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts)
                output_dir = os.path.join(os.path.dirname(file), "ocr_results")
                os.makedirs(output_dir, exist_ok=True)
                txt_filename = os.path.splitext(os.path.basename(file))[0] + ".txt"
                txt_path = os.path.join(output_dir, txt_filename)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(raw_text)
                print(f"✅ [Vision] Zapisano surowy OCR do: {txt_path}")
        else:
            # Stara metoda (Tesseract) - funkcja sama zapisuje plik
            page_texts = save_ocr_to_txt(file)

        if page_texts:
            # Krok 2: Użyj klasy PrivacyGuard do anonimizacji tekstu
            print(f"--- Anonimizacja wyniku dla: {os.path.basename(file)} ---")
            guard = PrivacyGuard(USER_PROFILE)
            anonymized_text = guard.anonymize(page_texts)
            
            # Zapisz oczyszczony tekst do pliku (wymagane przez użytkownika)
            cleaned_output_dir = os.path.join(current_dir, "cleaned_results")
            os.makedirs(cleaned_output_dir, exist_ok=True)
            cleaned_filename = os.path.splitext(os.path.basename(file))[0] + "_cleaned.txt"
            cleaned_path = os.path.join(cleaned_output_dir, cleaned_filename)
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(anonymized_text)
            print(f"✅ Zapisano oczyszczony tekst do: {cleaned_path}")

            # Krok 3: Analiza oczyszczonego tekstu przez AI
            # Domyślnie używamy Gemini, w razie błędu przełączy się na xAI
            data = analyzer.analyze_text(anonymized_text, provider='gemini')
            if data:
                # Krok 3.1: Opcjonalny zapis odpowiedzi JSON do pliku
                if SAVE_JSON_ENABLED:
                    json_output_dir = os.path.join(current_dir, "json_results")
                    os.makedirs(json_output_dir, exist_ok=True)

                    json_filename = os.path.splitext(os.path.basename(file))[0] + ".json"
                    json_path = os.path.join(json_output_dir, json_filename)

                    try:
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                        print(f"   [ZAPIS] Zapisano odpowiedź JSON do: {json_path}")
                    except Exception as e:
                        print(f"   [BŁĄD ZAPISU] Nie udało się zapisać pliku JSON: {e}")

                # Krok 3.2: Spłaszczenie struktury JSON do formatu tabelarycznego
                flat_data = _flatten_lab_results(data)
                if flat_data:
                    print(f"Pobrane dane (spłaszczone): {flat_data}")
                    all_results.append(flat_data)
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
        if col != 'Date' and not col.endswith('_flag'):
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
    parameters_to_plot = [col for col in df.columns if col != 'Date' and not col.endswith('_flag') and not col.endswith('_min') and not col.endswith('_max')]

    # Filtrujemy tylko te, które mają jakieś dane (nie same NaN)
    parameters_to_plot = [col for col in parameters_to_plot if df[col].notna().any()]

    # Tworzymy tyle wykresów, ile mamy parametrów (jeden pod drugim)
    fig, axes = plt.subplots(nrows=len(parameters_to_plot), ncols=1, figsize=(10, 4 * len(parameters_to_plot)))

    if len(parameters_to_plot) == 1:
        axes = [axes]

    for ax, param in zip(axes, parameters_to_plot):
        # Rysujemy tylko punkty, gdzie są dane (dropna)
        subset = df.dropna(subset=[param])

        # --- RYSOWANIE ZAKRESU REFERENCYJNEGO (WSTĘGA) ---
        min_col = f"{param}_min"
        max_col = f"{param}_max"

        if min_col in df.columns and max_col in df.columns:
            # Pobieramy wartości norm dla punktów, które rysujemy
            # fillna(0) dla minimum obsługuje przypadki typu "< 5" (gdzie min to null)
            vals_min = subset[min_col].fillna(0)
            vals_max = subset[max_col]

            # Rysujemy wstęgę tylko jeśli mamy dane o maksimum
            if vals_max.notna().any():
                ax.fill_between(subset['Date'], vals_min, vals_max, color='green', alpha=0.15, label='Zakres normy')
                # Opcjonalnie: delikatne linie krawędziowe normy
                # ax.plot(subset['Date'], vals_max, color='green', linestyle=':', alpha=0.3, linewidth=0.5)
                # ax.plot(subset['Date'], vals_min, color='green', linestyle=':', alpha=0.3, linewidth=0.5)

        # Główna linia trendu łącząca wszystkie punkty
        ax.plot(subset['Date'], subset[param], linestyle='-', color='gray', linewidth=1, zorder=1)

        # Domyślne, zielone markery dla wszystkich punktów
        ax.scatter(subset['Date'], subset[param], color='teal', zorder=2, label='W normie')

        # Sprawdzenie i narysowanie punktów z flagami, które przykryją domyślne markery
        flag_col_name = f"{param}_flag"
        if flag_col_name in subset.columns:
            high_points = subset[subset[flag_col_name] == 'H']
            low_points = subset[subset[flag_col_name] == 'L']
            ax.scatter(high_points['Date'], high_points[param], color='red', s=80, zorder=3, edgecolors='black', label='Powyżej normy (H)')
            ax.scatter(low_points['Date'], low_points[param], color='blue', s=80, zorder=3, edgecolors='black', label='Poniżej normy (L)')

        ax.set_title(f'Trend parametru: {param}', fontsize=12)
        ax.set_ylabel('Wartość')
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.tick_params(axis='x', rotation=30)
        ax.legend()

    plt.tight_layout()  # Żeby wykresy na siebie nie najeżdżały
    plt.show()


if __name__ == "__main__":
    main()