import os
import json
import re
from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Ładujemy zmienne środowiskowe
load_dotenv()


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

        # Wspólny System Prompt
        self.system_prompt = """
        Jesteś precyzyjnym analitykiem danych laboratoryjnych. Twoim zadaniem jest konwersja surowego tekstu OCR na format JSON, radząc sobie z szumem i duplikatami.

        GŁÓWNE PROBLEMY DO ROZWIĄZANIA:
        1. **Szum OCR i Odnośniki (BARDZO WAŻNE):** Często między nazwą a wynikiem pojawia się losowa cyfra (odnośnik do stopki), np. "IgE całkowite 2 < 15.7".
           - REGUŁA: Ignoruj samotne cyfry stojące przed właściwym wynikiem. Właściwa wartość to "15.7".
        2. **Znaki mniejszości/większości:**
           - Jeśli wynik zawiera "<" lub ">" (np. "< 15.7"), usuń ten znak z wartości liczbowej "v", aby można było robić wykresy.
           - Przenieś znak "<" lub ">" do pola "o" (operator).
        3. **Duplikaty nazw:**
           - Używaj listy obiektów. Jeśli nazwa się powtarza (np. Neutrofile % i Neutrofile ilość), stwórz dwa osobne obiekty.
        4. **Łączenie stron:**
           - Ignoruj podział na strony. Traktuj tekst jako całość.
        5. **Scalanie sekcji:** Jeśli widzisz nagłówek badania (np. "Morfologia krwi") na jednej stronie, a potem kontynuację na drugiej (często z dopiskiem "kontynuacja"), traktuj to jako JEDNO i to samo badanie.
        6. **Ekstrakcja kompletna:** Nie pomijaj ŻADNEJ linii z wynikiem. Przeczytaj każdą linię pod nagłówkiem sekcji.
        
        Twoja odpowiedź musi być poprawnym JSON, bez komentarzy czy bloków kodu.
        STRUKTURA JSON (ŚCISŁA):
        {
          "data_badania": "YYYY-MM-DD",
          "badania": [
            {
              "nazwa_sekcji": "Morfologia krwi (ICD-9: C55)",
              "wyniki": [
                {"n": "Nazwa Parametru", "v": Wartość, "u": "Jednostka", "o": "Operator"},
                ...
              ]
            }
          ]
        }
        
        ZASADY EKSTRAKCJI PÓL:
        - "n": Nazwa parametru (string).
        - "v": CZYSTA Wartość (float/int) lub string (dla wyników opisowych).
               UWAGA: Tutaj musi trafić sama liczba, bez znaku "<" i bez cyfry-odnośnika (np. "2").
        - "u": Jednostka (string) lub null.
        - "o": Operator (string). Wpisz tutaj "<" lub ">", jeśli wystąpił przy wyniku. Jeśli brak - null.
        
        PRZYKŁADY TRUDNYCH LINII (Pattern Recognition):
        - Wejście: "IgE całkowite (ICD-9: L89) 2 < 15.7 IU/ml"
          -> Wyjście: {"n": "IgE całkowite", "v": 15.7, "u": "IU/ml", "o": "<"}
          (Zauważ: Cyfra '2' została zignorowana, znak '<' trafił do pola 'o', a 'v' to czysta liczba).
        
        - Wejście: "Glukoza 5 87,9 mg/dl"
          -> Wyjście: {"n": "Glukoza", "v": 87.9, "u": "mg/dl", "o": null}
          (Zauważ: Cyfra '5' została zignorowana).
        
        TEKST DO ANALIZY:
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

        response = self.gemini_client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=f"{self.system_prompt}\n\nTEKST DO ANALIZY:\n{text}"
        )
        # Bardziej szczegółowe sprawdzanie odpowiedzi
        if not response.candidates:
            # Przypadek 1: Całkowita blokada, brak kandydatów
            feedback = getattr(response, 'prompt_feedback', 'Brak szczegółów.')
            raise Exception(f"Odpowiedź zablokowana (brak kandydatów). Powód: {feedback}")
        
        candidate = response.candidates[0]
        if candidate.finish_reason != 'STOP':
            # Przypadek 2: Kandydat istnieje, ale zakończył się z powodu innego niż 'STOP' (np. 'SAFETY')
            raise Exception(f"Generowanie odpowiedzi przerwane. Powód: '{candidate.finish_reason}'. Safety ratings: {candidate.safety_ratings}")

        return response.text

    def _query_xai(self, text):
        if not self.xai_client:
            raise Exception("Klient xAI nie jest skonfigurowany.")

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text},
        ]

        response = self.xai_client.chat.completions.create(
            model="grok-beta",
            messages=messages
        )
        return response.choices[0].message.content

    def _process_response(self, raw_text):
        """Czyści markdown i zwraca sparsowany obiekt JSON."""
        # Logowanie surowej odpowiedzi, aby ułatwić diagnozę problemu
        print(f"--- SUROWA ODPOWIEDŹ Z API ---\n{raw_text}\n-----------------------------")
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        # Dodatkowe zabezpieczenie przed pustą odpowiedzią
        if not clean_json:
            raise json.JSONDecodeError("Otrzymano pustą odpowiedź z API po oczyszczeniu.", "", 0)
        
        data = json.loads(clean_json)
        return data
