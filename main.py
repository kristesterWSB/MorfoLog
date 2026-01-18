import pandas as pd  # Biblioteka do tabel
import matplotlib.pyplot as plt
import glob
import os
import time
import json
import re
from analyzer import MedicalAnalyzer  # Import nowej klasy
from ocr_cleaner import save_ocr_to_txt, PrivacyGuard, USER_PROFILE # Import klasy i profilu z ocr_cleaner

# --- KONFIGURACJA ---
SAVE_JSON_ENABLED = True  # Ustaw na False, aby wyłączyć zapisywanie plików JSON

# Inicjalizacja analizatora (załaduje klucze z .env wewnątrz klasy)
analyzer = MedicalAnalyzer()

# Mapa do normalizacji jednostek - standaryzuje popularne warianty i błędy OCR
UNIT_NORMALIZATION_MAP = {
    "min/ul": "mln/ul",
    "f": "fl",
    "fi": "fl",
    "UI": "U/l",
    "UJ": "U/l",
}

# Mapa do normalizacji nazw parametrów - standaryzuje popularne błędy OCR
PARAMETER_NAME_NORMALIZATION_MAP = {
    "NRBC$": "NRBC #",
    "NRBCH": "NRBC #"
}


def _flatten_lab_results(data: dict) -> dict | None:
    """
    Spłaszcza zagnieżdżoną strukturę JSON z wynikami badań do płaskiego słownika.
    Tworzy unikalne klucze dla parametrów, łącząc nazwę z jednostką (np. "Neutrofile [%]").
    """
    # Sprawdź, czy odpowiedź ma nową, zagnieżdżoną strukturę
    if 'meta' not in data or 'badania' not in data:
        print(f"Błąd formatu: Otrzymano dane bez klucza 'meta' lub 'badania'. Dane: {data}")
        return None

    # Pobierz datę z zagnieżdżonego obiektu 'meta'
    flat_data = {'Date': data.get('meta', {}).get('data_badania')}

    for section in data.get('badania', []):
        section_name = section.get('nazwa_sekcji', 'Inne')
        # Czyścimy nazwę sekcji z kodów ICD-9, aby tytuły wykresów były ładniejsze
        clean_section_name = re.sub(r'\s*\(ICD-9:.*\)', '', section_name).strip()

        for result in section.get('wyniki', []):
            if isinstance(result, dict) and 'n' in result and 'v' in result:
                param_name = result['n']
                
                # --- NOWOŚĆ: Czyszczenie nazwy parametru z jednostek w nawiasach ---
                # Usuwa: [%], (%), [#], (#), [tys/ul] itp. z końca nazwy
                param_name = re.sub(r'\s*[\[\(].*?[\]\)]$', '', param_name).strip()

                # Normalizacja nazwy parametru
                normalized_param_name = PARAMETER_NAME_NORMALIZATION_MAP.get(param_name, param_name)

                param_value = result['v']
                param_unit = result.get('u')
                param_flag = result.get('f')

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

    return flat_data


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
    parameters_to_plot = [col for col in df.columns if col != 'Date' and not col.endswith('_flag')]

    # Filtrujemy tylko te, które mają jakieś dane (nie same NaN)
    parameters_to_plot = [col for col in parameters_to_plot if df[col].notna().any()]

    # Tworzymy tyle wykresów, ile mamy parametrów (jeden pod drugim)
    fig, axes = plt.subplots(nrows=len(parameters_to_plot), ncols=1, figsize=(10, 4 * len(parameters_to_plot)))

    if len(parameters_to_plot) == 1:
        axes = [axes]

    for ax, param in zip(axes, parameters_to_plot):
        # Rysujemy tylko punkty, gdzie są dane (dropna)
        subset = df.dropna(subset=[param])

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