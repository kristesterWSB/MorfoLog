import unittest
import json
import os
import sys

class TestJsonComparison(unittest.TestCase):
    
    def setUp(self):
        """Path configuration before the test."""
        # Project base path (C:/MorfoLog/engine-python)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # FILENAME FOR TEST (Adjust if your file is named differently)
        # We assume main.py processed 'sample_ocr.pdf' and saved 'sample_ocr.json'
        self.filename = "wyniki-31_12_25_morfologia.json"
        
        # Path to the generated file (by main.py)
        self.generated_path = os.path.join(self.project_root, "json_results", self.filename)
        
        # Path to the expected file (reference)
        self.expected_path = os.path.join(self.project_root, "tests", "test_data", "expected-31_12_25_morfologia.json")
        
        # Setting to see full diff in console in case of error
        self.maxDiff = None

    def test_compare_generated_vs_expected(self):
        """Compares generated JSON with expected reference."""
        
        # 1. Check if files exist
        if not os.path.exists(self.generated_path):
            self.fail(f"Generated file not found: {self.generated_path}.\n"
                      f"Run main.py first to generate results.")
            
        if not os.path.exists(self.expected_path):
            self.fail(f"Reference file not found: {self.expected_path}")

        # 2. Load both files
        with open(self.generated_path, 'r', encoding='utf-8') as f:
            generated_data = json.load(f)
            
        with open(self.expected_path, 'r', encoding='utf-8') as f:
            expected_data = json.load(f)

        # 3. Recursive comparison (shows error only in specific place)
        print(f"\n[TEST] Comparing JSON structure for: {self.filename}")
        errors = []
        self._collect_json_errors(generated_data, expected_data, errors=errors)
        
        if errors:
            self.fail(f"\n❌ TEST FAILED. Found {len(errors)} errors:\n" + "\n".join(errors))
            
        print(f"✅ Test OK: File {self.filename} matches reference.")

    def _collect_json_errors(self, received, expected, errors, path="root"):
        """
        Recursively compares JSON and collects all errors into `errors` list.
        """
        # 1. Type checking (with tolerance for int vs float)
        if type(received) is not type(expected):
            if not (isinstance(received, (int, float)) and isinstance(expected, (int, float))):
                errors.append(f"Error in '{path}': Type mismatch. Received: {type(received).__name__}, Expected: {type(expected).__name__}")
                return

        # 2. Dictionaries
        if isinstance(received, dict):
            # Check keys
            rec_keys = set(received.keys())
            exp_keys = set(expected.keys())
            
            if rec_keys != exp_keys:
                missing = exp_keys - rec_keys
                extra = rec_keys - exp_keys
                msg = f"Error in '{path}': Keys mismatch."
                if missing: msg += f"\n  Missing: {missing}"
                if extra: msg += f"\n  Extra: {extra}"
                errors.append(msg)
            
            # Recursion
            # We iterate only over common keys to avoid errors when key is missing
            common_keys = rec_keys.intersection(exp_keys)
            for key in common_keys:
                self._collect_json_errors(received[key], expected[key], errors, path=f"{path}.{key}")

        # 3. Lists
        elif isinstance(received, list):
            if len(received) != len(expected):
                errors.append(f"Error in '{path}': Different list length. Received: {len(received)}, Expected: {len(expected)}")
            
            for i, (r_item, e_item) in enumerate(zip(received, expected)):
                # We add context (e.g. examination name) to easily find error in list
                context = ""
                if isinstance(r_item, dict):
                    # List of keys that can serve as object identifiers
                    for id_key in ['name', 'examination_name', 'id', 'key', 'Date']:
                        if id_key in r_item:
                            context = f" <{id_key}={r_item[id_key]}>"
                            break
                
                self._collect_json_errors(r_item, e_item, errors, path=f"{path}[{i}]{context}")

        # 4. Simple values
        else:
            if received != expected:
                errors.append(f"❌ VALUE ERROR in: {path}\n   Received:  {received!r}\n   Expected: {expected!r}")

    def normalize_json(self, data):
        """
        Optional helper method. If tests fail due to minor differences
        (e.g. 5.0 vs 5), you can use this function to normalize before comparison.
        Not used in main test for now.
        """
        return json.loads(json.dumps(data, sort_keys=True))

if __name__ == '__main__':
    unittest.main()