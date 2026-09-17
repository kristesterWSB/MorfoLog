import os
import json
import re
import typing_extensions as typing
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# --- DATA SCHEMA DEFINITIONS (Structured Output) ---
# Fixed schema compatible with google-genai requirements (Pydantic validation)
# Types must be uppercase (STRING, NUMBER, etc.)
# The nullable field is defined by "nullable": True (if supported) or just the STRING type.

MEDICAL_REPORT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "meta": {
            "type": "OBJECT",
            "properties": {
                "date_examination": {"type": "STRING"}
            },
            "required": ["date_examination"]
        },
        "examinations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "examination_name": {"type": "STRING"},
                    "code_icd": {"type": "STRING"},
                    "results": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {"type": "STRING"},
                                "value": {"type": "NUMBER"},
                                "unit": {"type": "STRING"},
                                "range_min": {"type": "NUMBER", "nullable": True},
                                "range_max": {"type": "NUMBER", "nullable": True},
                                "flag": {"type": "STRING", "nullable": True}
                            },
                            "required": ["name", "value", "unit", "range_min", "range_max", "flag"]
                        }
                    }
                },
                "required": ["examination_name", "code_icd", "results"]
            }
        }
    },
    "required": ["meta", "examinations"]
}

class MedicalAnalyzer:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        # Initialize Gemini client (google-genai)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        else:
            self.gemini_client = None
            print("⚠️ Missing GEMINI_API_KEY")

        # Common System Prompt (without JSON instructions, because we use Structured Output)
        self.system_prompt = r"""
        Jesteś ekspertem medycznym AI. Twoim celem jest bezbłędna konwersja surowego OCR na ustrukturyzowane dane.
        
        WAŻNE: Używaj polskich znaków (UTF-8) bezpośrednio w JSON (np. "ł", "ą", "ś"), NIE używaj escape sequences (np. "\u0142").

        ANALIZA DOKUMENTU (Specyfika tego pliku):
        1. **Artefakty w Jednostkach:** OCR błędnie interpretuje jednostki jako wzory matematyczne, np. "$tys/\mu l^{*}$" lub "$mg/dl^{*}$".
            - ZADANIE: Oczyść to. Zamiast śmieci zwróć czystą jednostkę: "mln/ul", "tys/ul", "mg/dl", "g/dl", "%", "pg", "fl". Ignoruj gwiazdki (*) przy jednostkach (np. "pg*" -> "pg").
        2. **Flagi (H/L):** W wynikach pojawiają się litery "H" (High) i "L" (Low) oznaczające przekroczenie norm.
           - ZADANIE: Jeśli widzisz "H", "L" lub strzałki przy wyniku, wpisz to do pola "f" (flaga).
        3. **Nowe badania (Lipidogram, Testosteron):**
           - Wykrywaj sekcje dynamicznie po kodach ICD-9 w nawiasach. Nie hardkoduj nazw.
        4. **Ignorowanie Odnośników:**
           - Jeśli nazwa badania ma cyfrę na końcu (np. "Glukoza (ICD-9: L43) 2"), ta cyfra "2" to przypis. Ignoruj ją.
        5. **Szum OCR i Odnośniki (BARDZO WAŻNE):** Często między nazwą a wynikiem pojawia się losowa cyfra (odnośnik do stopki), np. "IgE całkowite 2 < 15.7".
           - REGUŁA: Ignoruj samotne cyfry stojące przed właściwym wynikiem. Właściwa wartość to "15.7".   
        6. **Duplikaty nazw:**
           - Używaj listy obiektów. Jeśli nazwa się powtarza (np. Neutrofile % i Neutrofile ilość), stwórz dwa osobne obiekty.
        7. **Błędy OCR dla NRBC:**
           - Parametr "NRBC #" jest często mylony przez OCR z "NRBC$" lub "NRBCH". Traktuj te warianty jako "NRBC #".
        8. **Łączenie stron:**
           - Ignoruj podział na strony. Traktuj tekst jako całość.
        9. **Scalanie sekcji:** Jeśli widzisz nagłówek badania (np. "Morfologia krwi") na jednej stronie, a potem kontynuację na drugiej (często z dopiskiem "kontynuacja"), traktuj to jako JEDNO i to samo badanie.
        10. **Ekstrakcja kompletna:** Nie pomijaj ŻADNEJ linii z wynikiem. Przeczytaj każdą linię pod nagłówkiem sekcji.
        11. **Format Daty:** Data badania ("date_examination") musi być w ścisłym formacie "YYYY-MM-DD" (np. "2023-05-12"). Jeśli w tekście widnieje godzina (np. "2023-11-15 09:21"), usuń ją i zwróć tylko datę.
        12. **Zakresy referencyjne (Normy):** Często po wyniku i jednostce występują dwie liczby oznaczające zakres (min i max) w 4. i 5. kolumnie, np. "Leukocyty 5,53 tys/ul 4,00 10,00". W tym przypadku range_min=4.00, range_max=10.00. Wyodrębnij te wartości. Jeśli norma jest jednostronna (np. "< 5"), wpisz odpowiednio (min=null, max=5).
            **KOREKTA BŁĘDÓW OCR:** Często w OCR znikają przecinki w normach (np. "360" zamiast "36,0"). Jeśli zakresy są nielogicznie wysokie w porównaniu do wyniku (np. wynik 42, a norma 360-470), to błąd OCR. Wstaw przecinek, aby dopasować rząd wielkości (zmień 360 na 36.0).

        ZASADY EKSTRAKCJI:
        - "name": Nazwa parametru (string).
        - "value": Wartość liczbową (float). Ignoruj znaki "<" i ">". Jeśli wynik jest tekstem (np. "ujemny", "przejrzysty") lub zakresem, POMIŃ ten parametr.
        - "unit": Jednostka (string).
        - "range_min": Dolna granica normy (float lub null).
        - "range_max": Górna granica normy (float lub null).
        - "flag": Flaga (string "H", "L" lub null).
        
        SZCZEGÓLNA ZASADA OBSŁUGI PAR BADAŃ (Same Names, Different Units):
        Niektóre parametry (zwłaszcza: "Niedojrzałe granulocyty IG", "NRBC", "Neutrofile", "Limfocyty", "Monocyty") występują dwukrotnie:
        1. Jako odsetek (jednostka: %).
        2. Jako liczba bezwzględna (jednostka: tys/µl, G/l, #).
        
        PROBLEM:
        Często w tekście oba te badania mają IDENTYCZNĄ lub bardzo podobną nazwę (np. "Niedojrzałe granulocyty IG").
        
        ROZKAZ DLA CIEBIE:
        1. Zapisz oba w liście wyników jako osobne obiekty.
        2. Upewnij się, że pole "unit" (jednostka) jest poprawnie wypełnione dla każdego z nich ("%" vs "tys/ul").
        3. Nie modyfikuj sztucznie nazwy ("name") dopiskami w nawiasach - aplikacja rozróżni je po jednostce.
        """

    def analyze_text(self, text):
        """
        Main function analyzing using Gemini.
        """
        if not text:
            return None

        try:
            print(f"   [AI] Attempting analysis using: GEMINI...")
            raw_json = self._query_gemini(text)
            return self._process_response(raw_json)
        except Exception as e:
            print(f"⚠️ Gemini analysis error: {e}")
            return None

    def _query_gemini(self, text):
        if not self.gemini_client:
            raise Exception("Gemini client is not configured.")
        
        model_name = 'gemini-2.0-flash-lite'
        print(f"   [AI] Sending request to model: {model_name}...")
        
        response = self.gemini_client.models.generate_content(
            model=model_name,
            contents=f"{self.system_prompt}\n{text}",
            config={
                'response_mime_type': 'application/json',
                'response_schema': MEDICAL_REPORT_SCHEMA,
                'temperature': 0.0,
            }
        )
        
        if not response.candidates:
            feedback = getattr(response, 'prompt_feedback', 'No details.')
            raise Exception(f"Response blocked (no candidates). Reason: {feedback}")
        
        candidate = response.candidates[0]
        if candidate.finish_reason != 'STOP':
            raise Exception(f"Response generation interrupted. Reason: '{candidate.finish_reason}'. Safety ratings: {candidate.safety_ratings}")

        return response.text

    def _process_response(self, raw_text):
        """Cleans markdown and returns parsed JSON object."""
        print(f"--- LLM returned an object ---")
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        
        # FIX: Fix missing backslashes for unicode (e.g. "u0142" -> "\u0142")
        # If we see "u" followed by 4 hex digits and NO backslash before it, we add it.
        # This fixes errors generated by some versions of libraries/models.
        clean_json = re.sub(r'(?<!\\)u([0-9a-fA-F]{4})', r'\\u\1', clean_json)

        if not clean_json:
            raise json.JSONDecodeError("LLM returned empty or malformed JSON", "", 0)
        
        data = json.loads(clean_json)
        return data
