from pdf2image import convert_from_path
import os
import glob
import re

# --- DEFAULT USER PROFILE ---
# Data is now passed dynamically in the context of each request (instead of from .env)
USER_PROFILE = {
    "name": None,
    "lastname": None,
    "pesel": None,
    "address": None
}

def anonymize_pesel_by_dob(text: str, dob_fragment: str) -> str:
    """
    Anonymizes PESEL in text based on a date of birth fragment (YYMMDD).
    Searches for an 11-digit sequence starting with dob_fragment and replaces the whole with [REDACTED_PESEL].
    """
    if not dob_fragment or not re.match(r'^\d{6}$', dob_fragment):
        return text

    # We search for an 11-digit sequence that starts with dob_fragment
    # \b ensures we don't catch the middle of a longer sequence
    pattern = r'\b(' + re.escape(dob_fragment) + r')\d{5}\b'
    
    # Replace the whole PESEL with [REDACTED_PESEL]
    return re.sub(pattern, '[REDACTED_PESEL]', text)

class PrivacyGuard:
    """
    Class for anonymizing personal data from raw OCR text, using precise word replacement.
    """
    def __init__(self, user_profile: dict):
        self.profile = user_profile

        # Values for direct, precise replacement
        self.direct_values = [
            self.profile.get("name"),
            self.profile.get("lastname"),
            self.profile.get("pesel"),
        ]
        
        # Split address into parts to remove e.g. street name, number, city, zip
        address = self.profile.get("address", "")
        if address:
            # We split the address into words, removing punctuation marks
            # e.g. "CEGLANA 63/76, 40-514 KATOWICE" -> ["CEGLANA", "63", "76", "40", "514", "KATOWICE"]
            address_parts = re.split(r'[\s,/.-]+', address)
            # We filter: remove empty and very short (e.g. 1-character) parts, unless they are digits
            self.direct_values.extend([part for part in address_parts if len(part) > 1])

        # Remove empty entries (None) and potential duplicates, sort from longest (so as not to replace substrings)
        self.direct_values = [str(v) for v in self.direct_values if v]
        self.direct_values = list(set(self.direct_values))
        # Sorting descending by length is important so that e.g. "Katowice" is removed before "Kat" (if it existed)
        self.direct_values.sort(key=len, reverse=True)

    def anonymize(self, page_texts: list[str]) -> str:
        """Operates in multiple stages, precisely replacing words and cleaning noise only on the last page."""
        
        processed_pages = []
        num_pages = len(page_texts)

        for i, page_text in enumerate(page_texts):
            is_last_page = (i == num_pages - 1)
            anonymized_text = page_text
            
            # Stage 1: Direct replacement of precise data (First name, Last name, PESEL, address fragments)
            for value in self.direct_values:
                # For very short words (e.g. house no. "1") we use strict word boundaries \b
                # For longer ones (e.g. street "Ceglana") we allow matching even if OCR appended something, 
                # but we still try to avoid replacing inside other words (e.g. "Cat" in "Catapult").
                # Let's use the approach: \bWord\b is safe.
                # If anonymization doesn't work, it means OCR returned e.g. "CEGLANA," (with comma) and \b catches it.
                # But if OCR returned "CEGLANAKATOWICE" (glued), then \b won't work.
                
                if len(value) > 3:
                    # For long words, we try to be more aggressive, but with caution
                    pattern = re.escape(value)
                else:
                    pattern = r'\b' + re.escape(value) + r'\b'
                
                anonymized_text = re.sub(pattern, '[REDACTED]', anonymized_text, flags=re.IGNORECASE)

            # Stage 1.5: PESEL anonymization based on date of birth fragment (if available)
            dob_fragment = self.profile.get("dob_fragment")
            if dob_fragment:
                anonymized_text = anonymize_pesel_by_dob(anonymized_text, dob_fragment)

            # Stage 2: Cleaning using additional, general Regex rules
            # Remove any remaining 11-digit sequence (potential PESEL)
            anonymized_text = re.sub(r'\b\d{11}\b', '[REDACTED_PESEL]', anonymized_text)
            
            # Remove zip codes (e.g. 40-514)
            anonymized_text = re.sub(r'\b\d{2}-\d{3}\b', '[REDACTED_ZIP]', anonymized_text)
            
            # Replace role keywords (e.g. "Pacjent:"), not entire lines
            anonymized_text = re.sub(r'\b(Pacjent|Odbiorca|Lekarz)\b\s*:?', '[REDACTED_ROLE_INFO]', anonymized_text, flags=re.IGNORECASE)

            # Anonymize date of birth - handles "Data ur", "Data urodzenia", "Data urodz." etc.
            anonymized_text = re.sub(r'\bData\s+(?:ur\.?|urod[a-z]*)\s*[:\s]*\d{4}-\d{2}-\d{2}', '[REDACTED_DOB]', anonymized_text, flags=re.IGNORECASE)

            lines = anonymized_text.split('\n')
            current_page_processed_lines = lines

            # Stage 3: Removing metadata lines - ONLY FOR THE LAST PAGE
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

