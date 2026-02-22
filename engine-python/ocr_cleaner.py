from pdf2image import convert_from_path
import os
import glob
import re

# --- DOMYŚLNY PROFIL UŻYTKOWNIKA ---
# Dane są teraz przekazywane dynamicznie w kontekście każdego żądania (zamiast z .env)
USER_PROFILE = {
    "name": None,
    "lastname": None,
    "pesel": None,
    "address": None
}

def anonymize_pesel_by_dob(text: str, dob_fragment: str) -> str:
    """
    Anonimizuje PESEL w tekście na podstawie fragmentu daty urodzenia (RRMMDD).
    Wyszukuje ciąg 11 cyfr zaczynający się od dob_fragment i zamienia ostatnie 5 cyfr na XXXXX.
    """
    if not dob_fragment or not re.match(r'^\d{6}$', dob_fragment):
        return text

    # Szukamy ciągu 11 cyfr, który zaczyna się od dob_fragment
    # \b zapewnia, że nie łapiemy środka dłuższego ciągu
    pattern = r'\b(' + re.escape(dob_fragment) + r')\d{5}\b'
    
    # Zamieniamy cały PESEL na [REDACTED_PESEL]
    return re.sub(pattern, '[REDACTED_PESEL]', text)

class PrivacyGuard:
    """
    Klasa do anonimizacji danych osobowych z surowego tekstu OCR, używająca precyzyjnego zastępowania słów.
    """
    def __init__(self, user_profile: dict):
        self.profile = user_profile

        # Wartości do bezpośredniego, precyzyjnego zastąpienia
        self.direct_values = [
            self.profile.get("name"),
            self.profile.get("lastname"),
            self.profile.get("pesel"),
        ]
        
        # Podziel adres na części, aby usunąć np. samą nazwę ulicy, numer, miasto, kod
        address = self.profile.get("address", "")
        if address:
            # Rozbijamy adres na słowa, usuwając znaki interpunkcyjne
            # np. "CEGLANA 63/76, 40-514 KATOWICE" -> ["CEGLANA", "63", "76", "40", "514", "KATOWICE"]
            address_parts = re.split(r'[\s,/.-]+', address)
            # Filtrujemy: usuwamy puste i bardzo krótkie (np. 1-znakowe) części, chyba że to cyfry
            self.direct_values.extend([part for part in address_parts if len(part) > 1])

        # Usuń puste wpisy (None) i ewentualne duplikaty, sortuj od najdłuższych (żeby nie zamieniać podciągów)
        self.direct_values = [str(v) for v in self.direct_values if v]
        self.direct_values = list(set(self.direct_values))
        # Sortowanie malejąco po długości jest ważne, aby np. "Katowice" usunąć przed "Kat" (gdyby istniało)
        self.direct_values.sort(key=len, reverse=True)

    def anonymize(self, page_texts: list[str]) -> str:
        """Działa wieloetapowo, precyzyjnie zastępując słowa i czyszcząc szum tylko na ostatniej stronie."""
        
        processed_pages = []
        num_pages = len(page_texts)

        for i, page_text in enumerate(page_texts):
            is_last_page = (i == num_pages - 1)
            anonymized_text = page_text
            
            # Etap 1: Bezpośrednie zastąpienie precyzyjnych danych (Imię, Nazwisko, PESEL, fragmenty adresu)
            for value in self.direct_values:
                # Dla bardzo krótkich słów (np. nr domu "1") używamy ścisłych granic słowa \b
                # Dla dłuższych (np. ulica "Ceglana") pozwalamy na dopasowanie nawet jeśli OCR coś dokleił, 
                # ale nadal staramy się unikać zastępowania wewnątrz innych słów (np. "Kat" w "Katapulta").
                # Użyjmy podejścia: \bWord\b jest bezpieczne.
                # Jeśli anonimizacja nie działa, to znaczy że OCR zwrócił np. "CEGLANA," (z przecinkiem) i \b to łapie.
                # Ale jeśli OCR zwrócił "CEGLANAKATOWICE" (sklejone), to \b nie zadziała.
                
                if len(value) > 3:
                    # Dla długich słów, próbujemy być bardziej agresywni, ale z ostrożnością
                    pattern = re.escape(value)
                else:
                    pattern = r'\b' + re.escape(value) + r'\b'
                
                anonymized_text = re.sub(pattern, '[REDACTED]', anonymized_text, flags=re.IGNORECASE)

            # Etap 1.5: Anonimizacja PESELu na podstawie fragmentu daty urodzenia (jeśli dostępny)
            dob_fragment = self.profile.get("dob_fragment")
            if dob_fragment:
                anonymized_text = anonymize_pesel_by_dob(anonymized_text, dob_fragment)

            # Etap 2: Czyszczenie za pomocą dodatkowych, ogólnych reguł Regex
            # Usuń każdy pozostały 11-cyfrowy ciąg (potencjalny PESEL)
            anonymized_text = re.sub(r'\b\d{11}\b', '[REDACTED_PESEL]', anonymized_text)
            
            # Usuń kody pocztowe (np. 40-514)
            anonymized_text = re.sub(r'\b\d{2}-\d{3}\b', '[REDACTED_ZIP]', anonymized_text)
            
            # Zastąp słowa-klucze ról (np. "Pacjent:"), a nie całe linie
            anonymized_text = re.sub(r'\b(Pacjent|Odbiorca|Lekarz)\b\s*:?', '[REDACTED_ROLE_INFO]', anonymized_text, flags=re.IGNORECASE)

            # Anonimizuj datę urodzenia - obsługuje "Data ur", "Data urodzenia", "Data urodz." itp.
            anonymized_text = re.sub(r'\bData\s+(?:ur\.?|urod[a-z]*)\s*[:\s]*\d{4}-\d{2}-\d{2}', '[REDACTED_DOB]', anonymized_text, flags=re.IGNORECASE)

            lines = anonymized_text.split('\n')
            current_page_processed_lines = lines

            # Etap 3: Usuwanie linii z metadanymi - TYLKO DLA OSTATNIEJ STRONY
            if is_last_page:
                noise_patterns = [
                    r'przyjęcia prób',
                    r'Data wykonania',
                    r'Data/godz\. wydania',
                    r'DIAGNOSTYKA S\.A\.',
                    r'KREW ŻYLNA',
                    r'Strona:? \d+ z \d+'
                ]
                noise_regex = re.compile('|'.join(noise_patterns), re.IGNORECASE)
                current_page_processed_lines = [line for line in current_page_processed_lines if not noise_regex.search(line)]

            processed_pages.append("\n".join(current_page_processed_lines))

        return "\n".join(processed_pages)

