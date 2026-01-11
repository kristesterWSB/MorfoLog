import pytesseract
from pdf2image import convert_from_path
import re
import pandas as pd  # Biblioteka do tabel
import matplotlib.pyplot as plt
import glob
import os

# KONFIGURACJA ŚCIEŻEK
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPPLER_PATH = r'C:\poppler-25.12.0\Library\bin'


def extract_text_from_pdf(pdf_path):
    """Zamienia PDF na tekst za pomocą OCR."""
    print(f"Przetwarzam: {pdf_path}...")
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img, lang='pol+eng') + "\n"
        return full_text
    except Exception as e:
        print(f"Błąd OCR: {e}")
        return ""


def parse_results(raw_text):
    """Wyciąga konkretne liczby i datę z surowego tekstu."""
    data = {"Date": None}

    # Szukamy słowa "Data", potem czegokolwiek (.*?), słowa "pobrania"
    # i w końcu samej daty ( \d{4}-\d{2}-\d{2} )
    date_pattern = r'Data.*?pobrania.*?(\d{4}-\d{2}-\d{2})'

    # re.DOTALL pozwala kropce przechodzić przez nowe linie (jeśli data jest niżej)
    # re.IGNORECASE ignoruje wielkość liter
    date_match = re.search(date_pattern, raw_text, re.IGNORECASE | re.DOTALL)

    if date_match:
        data["Date"] = date_match.group(1)

    # --- GENERYCZNE PARSOWANIE WYNIKÓW ---
    # Mapa mapująca polskie nazwy na skróty medyczne (dla porządku na wykresach)
    # Jeśli nazwy nie ma w mapie, zostanie użyta pełna nazwa z PDF
    name_mapping = {
        "Leukocyty": "Leukocyty",
        "Erytrocyty": "Erytrocyty",
        "Hemoglobina": "Hemoglobina",
        "Hematokryt": "Hematokryt",
        "Płytki krwi": "Płytki krwi",
        "Plytki krwi": "Płytki krwi", # Obsługa literówek OCR
        "Glukoza": "Glukoza",
        "Cholesterol całkowity": "Cholesterol całkowity"
    }

    # Iterujemy linia po linii, szukając wzorca: Nazwa -> Wartość -> Jednostka
    for line in raw_text.split('\n'):
        # Regex: Nazwa (tekst) | Wartość (liczba, ew. z <, >) | Jednostka (litery, %, /, mikro)
        match = re.search(r"^\s*(?P<name>.*?)\s+(?P<val>[<>]?\s*\d+(?:[.,]\d+)?)\s+(?P<unit>[a-zA-Z%µ/*]+)", line)
        
        if match:
            name = match.group("name").strip()
            # Usuwamy kody ICD-9 z nazwy, np. "Glukoza (ICD-9: L43)" -> "Glukoza"
            name = re.sub(r'\s*\(ICD-9:.*?\)', '', name).strip()
            
            val_str = match.group("val").replace(',', '.').replace('<', '').replace('>', '').strip()
            key = name_mapping.get(name, name)
            
            try:
                data[key] = float(val_str)
            except ValueError:
                continue

    return data


# --- GŁÓWNA LOGIKA ---
print("Skanowanie folderu w poszukiwaniu plików PDF...")
# Pobieramy ścieżkę do folderu, w którym znajduje się ten skrypt
current_dir = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(os.path.join(current_dir, "*.pdf"))

print(f"Znaleziono plików: {len(files)}")

all_results = []

for file in files:
    raw_txt = extract_text_from_pdf(file)
    if raw_txt:
        parsed_data = parse_results(raw_txt)
        all_results.append(parsed_data)

# Tworzymy tabelę (DataFrame)
df = pd.DataFrame(all_results)

# Wyświetlamy wynik
print("\n--- ZESTAWIENIE WYNIKÓW ---")
print(df.to_string(index=False))

# Opcjonalnie: zapisz do Excela
# df.to_excel("wyniki_trend.xlsx", index=False)


# --- LOGIKA WYKRESU DLA WSZYSTKICH PARAMETRÓW ---

if not df.empty and len(df) >= 2:
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    # Lista kolumn do narysowania (wszystkie poza datą)
    # Wybieramy tylko te kolumny, które mają w nazwie skróty WBC, RBC, HGB, HCT, PLT
    parameters_to_plot = [col for col in df.columns if col != 'Date']

    # Tworzymy tyle wykresów, ile mamy parametrów (jeden pod drugim)
    fig, axes = plt.subplots(nrows=len(parameters_to_plot), ncols=1, figsize=(10, 4 * len(parameters_to_plot)))

    # Jeśli mamy tylko jeden parametr, axes nie jest listą, więc musimy to poprawić
    if len(parameters_to_plot) == 1:
        axes = [axes]

    for ax, param in zip(axes, parameters_to_plot):
        ax.plot(df['Date'], df[param], marker='o', linestyle='-', color='teal', linewidth=2)
        ax.set_title(f'Trend parametru: {param}', fontsize=12)
        ax.set_ylabel('Wartość')
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.tick_params(axis='x', rotation=30)

    plt.tight_layout()  # Żeby wykresy na siebie nie najeżdżały
    plt.show()
else:
    print("\n[!] Potrzebne są co najmniej dwa badania z różnymi datami, aby narysować trendy.")