import unittest
import json
import os
import sys

class TestJsonComparison(unittest.TestCase):
    
    def setUp(self):
        """Konfiguracja ścieżek przed testem."""
        # Ścieżka bazowa projektu (C:/MorfoLog/engine-python)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # NAZWA PLIKU DO TESTU (Dostosuj jeśli Twój plik nazywa się inaczej)
        # Zakładamy, że main.py przetworzył 'sample_ocr.pdf' i zapisał 'sample_ocr.json'
        self.filename = "wyniki-31_12_25_morfologia.json"
        
        # Ścieżka do wygenerowanego pliku (przez main.py)
        self.generated_path = os.path.join(self.project_root, "json_results", self.filename)
        
        # Ścieżka do oczekiwanego pliku (wzorzec)
        self.expected_path = os.path.join(self.project_root, "tests", "test_data", "expected-31_12_25_morfologia.json")
        
        # Ustawienie, aby widzieć pełną różnicę w konsoli w przypadku błędu
        self.maxDiff = None

    def test_compare_generated_vs_expected(self):
        """Porównuje wygenerowany JSON z oczekiwanym wzorcem."""
        
        # 1. Sprawdź czy pliki istnieją
        if not os.path.exists(self.generated_path):
            self.fail(f"Nie znaleziono wygenerowanego pliku: {self.generated_path}.\n"
                      f"Uruchom najpierw main.py, aby wygenerować wyniki.")
            
        if not os.path.exists(self.expected_path):
            self.fail(f"Nie znaleziono pliku wzorcowego: {self.expected_path}")

        # 2. Wczytaj oba pliki
        with open(self.generated_path, 'r', encoding='utf-8') as f:
            generated_data = json.load(f)
            
        with open(self.expected_path, 'r', encoding='utf-8') as f:
            expected_data = json.load(f)

        # 3. Porównanie rekurencyjne (pokazuje błąd tylko w konkretnym miejscu)
        print(f"\n[TEST] Porównywanie struktury JSON dla: {self.filename}")
        errors = []
        self._collect_json_errors(generated_data, expected_data, errors=errors)
        
        if errors:
            self.fail(f"\n❌ TEST FAILED. Znaleziono {len(errors)} błędów:\n" + "\n".join(errors))
            
        print(f"✅ Test OK: Plik {self.filename} jest zgodny z wzorcem.")

    def _collect_json_errors(self, received, expected, errors, path="root"):
        """
        Rekurencyjnie porównuje JSON i zbiera wszystkie błędy do listy `errors`.
        """
        # 1. Sprawdzenie typów (z tolerancją dla int vs float)
        if type(received) is not type(expected):
            if not (isinstance(received, (int, float)) and isinstance(expected, (int, float))):
                errors.append(f"Błąd w '{path}': Niezgodność typów. Otrzymano: {type(received).__name__}, Oczekiwano: {type(expected).__name__}")
                return

        # 2. Słowniki
        if isinstance(received, dict):
            # Sprawdź klucze
            rec_keys = set(received.keys())
            exp_keys = set(expected.keys())
            
            if rec_keys != exp_keys:
                missing = exp_keys - rec_keys
                extra = rec_keys - exp_keys
                msg = f"Błąd w '{path}': Niezgodność kluczy."
                if missing: msg += f"\n  Brakujące: {missing}"
                if extra: msg += f"\n  Nadmiarowe: {extra}"
                errors.append(msg)
            
            # Rekurencja
            # Iterujemy tylko po wspólnych kluczach, aby uniknąć błędów przy braku klucza
            common_keys = rec_keys.intersection(exp_keys)
            for key in common_keys:
                self._collect_json_errors(received[key], expected[key], errors, path=f"{path}.{key}")

        # 3. Listy
        elif isinstance(received, list):
            if len(received) != len(expected):
                errors.append(f"Błąd w '{path}': Różna długość listy. Otrzymano: {len(received)}, Oczekiwano: {len(expected)}")
            
            for i, (r_item, e_item) in enumerate(zip(received, expected)):
                # Dodajemy kontekst (np. nazwę badania), żeby łatwiej znaleźć błąd w liście
                context = ""
                if isinstance(r_item, dict):
                    # Lista kluczy, które mogą służyć jako identyfikatory obiektu
                    for id_key in ['name', 'examination_name', 'id', 'key', 'Date']:
                        if id_key in r_item:
                            context = f" <{id_key}={r_item[id_key]}>"
                            break
                
                self._collect_json_errors(r_item, e_item, errors, path=f"{path}[{i}]{context}")

        # 4. Wartości proste
        else:
            if received != expected:
                errors.append(f"❌ BŁĄD WARTOŚCI w: {path}\n   Otrzymano:  {received!r}\n   Oczekiwano: {expected!r}")

    def normalize_json(self, data):
        """
        Opcjonalna metoda pomocnicza. Jeśli testy będą oblewać przez drobne różnice 
        (np. 5.0 vs 5), można użyć tej funkcji do normalizacji przed porównaniem.
        Na razie nie jest używana w teście głównym.
        """
        return json.loads(json.dumps(data, sort_keys=True))

if __name__ == '__main__':
    unittest.main()