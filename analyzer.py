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
        Jesteś ekspertem analitykiem medycznym.
        Z poniższego tekstu (surowe wyniki badań krwi po OCR) wyodrębnij datę pobrania oraz WSZYSTKIE widoczne wyniki badań laboratoryjnych.
        Nie ograniczaj się tylko do podstawowej morfologii. Wyciągnij wszystko co ma wynik liczbowy (np. MCV, MCH, MCHC, RDW, NEUT, LYMPH, MONO, Glukoza, Cholesterol, TSH, Żelazo, itp.).

        Wymagany format JSON (płaska struktura):
        {
            "Date": "YYYY-MM-DD",
            "Leukocyty": 6.5,
            "RBC": 4.8,
            "MCV": 85.0,
            "Cholesterol": 190,
            "TSH": 1.45
        }
        
        Zasady:
        1. Używaj pełnych nazw medycznych jako kluczy a gdy takiego nie ma to użyj skrótu (np. MCV, MCH)
        2. Jeśli brak skrótu, użyj nazwy badania z tekstu (np. "Glukoza").
        3. Wartości liczbowe podawaj jako float (kropka jako separator).
        4. Jeśli jakiejś wartości nie ma, nie dodawaj klucza do JSONa.
        5. Zwróć WYŁĄCZNIE czysty JSON.
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
            model='gemini-2.0-flash-lite',  # Szybki model zgodnie z wymaganiami
            contents=f"{self.system_prompt}\n\nTEKST DO ANALIZY:\n{text}"
        )
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
        """Czyści markdown i mapuje klucze JSON na format wymagany przez DataFrame."""
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        data = json.loads(clean_json)

        # Normalizacja klucza daty (AI może zwrócić 'date' lub 'Date')
        if 'date' in data:
            data['Date'] = data.pop('date')
            
        return data