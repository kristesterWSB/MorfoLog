import os
import json
import re
import typing_extensions as typing
from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Ładujemy zmienne środowiskowe
load_dotenv()

# --- DEFINICJE SCHEMATÓW DANYCH (Structured Output) ---
# Poprawiony schemat zgodny z wymaganiami biblioteki google-genai (Pydantic validation)
# Typy muszą być wielkimi literami (STRING, NUMBER, etc.)
# Pole nullable definiujemy przez "nullable": True (jeśli wspierane) lub po prostu typ STRING.

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
        self.xai_key = os.getenv("XAI_API_KEY")

        # Inicjalizacja klienta Gemini (google-genai)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        else:
            self.gemini_client = None
            print("⚠️ Brak klucza GEMINI_API_KEY")

        # Inicjalizacja klienta xAI (przez bibliotekę OpenAI)
        if self.xai_key:
            self.xai_client = OpenAI(
                api_key=self.xai_key,
                base_url="https://api.x.ai/v1"
            )
        else:
            self.xai_client = None
            print("⚠️ Brak klucza XAI_API_KEY")

        # Wspólny System Prompt (bez instrukcji JSON, bo używamy Structured Output)
        self.system_prompt = r"""
        Jesteś ekspertem medycznym AI. Twoim celem jest bezbłędna konwersja surowego OCR na ustrukturyzowane dane.

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

    def analyze_text(self, text, provider='gemini'):
        """
        Główna funkcja analizująca.
        provider: 'gemini' lub 'xai'.
        Automatycznie przełącza się na drugiego dostawcę w przypadku błędu.
        """
        if not text:
            return None

        primary_func = self._query_gemini if provider == 'gemini' else self._query_xai
        fallback_func = self._query_xai if provider == 'gemini' else self._query_gemini
        fallback_name = 'xAI' if provider == 'gemini' else 'Gemini'

        try:
            print(f"   [AI] Próba analizy przez: {provider.upper()}...")
            raw_json = primary_func(text)
            return self._process_response(raw_json)
        except Exception as e:
            print(f"⚠️ Błąd dostawcy {provider.upper()}: {e}")
            print(f"🔄 Przełączanie na: {fallback_name}...")

            try:
                raw_json = fallback_func(text)
                return self._process_response(raw_json)
            except Exception as e2:
                print(f"❌ Błąd zapasowego dostawcy {fallback_name}: {e2}")
                return None

    def _query_gemini(self, text):
        if not self.gemini_client:
            raise Exception("Klient Gemini nie jest skonfigurowany.")
        
        model_name = 'gemini-2.0-flash-lite'
        print(f"   [AI] Wysyłanie zapytania do modelu: {model_name}...")
        
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
            feedback = getattr(response, 'prompt_feedback', 'Brak szczegółów.')
            raise Exception(f"Odpowiedź zablokowana (brak kandydatów). Powód: {feedback}")
        
        candidate = response.candidates[0]
        if candidate.finish_reason != 'STOP':
            raise Exception(f"Generowanie odpowiedzi przerwane. Powód: '{candidate.finish_reason}'. Safety ratings: {candidate.safety_ratings}")

        return response.text

    def _query_xai(self, text):
        if not self.xai_client:
            raise Exception("Klient xAI nie jest skonfigurowany.")

        # Dla xAI musimy dodać instrukcję JSON, bo usunęliśmy ją z głównego promptu
        xai_prompt = self.system_prompt + "\n\nOUTPUT FORMAT: JSON matching {meta: {date_examination: str}, examinations: [{examination_name: str, code_icd: str, results: [{name: str, value: float, unit: str, range_min: float|null, range_max: float|null, flag: str|null}]}]}"

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": xai_prompt},
            {"role": "user", "content": text},
        ]

        response = self.xai_client.chat.completions.create(
            model="grok-beta",
            messages=messages
        )
        return response.choices[0].message.content

    def _process_response(self, raw_text):
        """Czyści markdown i zwraca sparsowany obiekt JSON."""
        print(f"--- LLM returned an object ---")
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        if not clean_json:
            raise json.JSONDecodeError("LLM returned empty or malformed JSON", "", 0)
        
        data = json.loads(clean_json)
        return data
