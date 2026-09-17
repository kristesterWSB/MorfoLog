import glob
import os
import time
import json
import re
from analyzer import MedicalAnalyzer  # Import new class
from ocr_cleaner import PrivacyGuard, USER_PROFILE
from google_vision_ocr import GoogleVisionOCR

# --- CONFIGURATION ---
SAVE_JSON_ENABLED = True  # Set to False to disable saving JSON files
USE_GOOGLE_VISION = True  # ALWAYS TRUE - Tesseract removed
GCP_KEY_PATH = "gcp_key.json"  # Path to Google Cloud key (relative to engine-python)


def process_single_file(file_content, vision_ocr_client, analyzer_instance, patient_context=None, original_filename=None):
    """
    Processes a single file: OCR -> Anonymization -> AI Analysis.
    Returns raw JSON with results (not flattened).
    Accepts bytes or file path.
    """
    page_texts = []
    
    # Determine if input is file path or bytes
    is_bytes = isinstance(file_content, bytes)
    # Use provided filename for logs, fallback to generic
    file_identifier = original_filename if (is_bytes and original_filename) else ("uploaded_file" if is_bytes else os.path.basename(file_content))

    # Step 1: Perform OCR (Vision only)
    if vision_ocr_client:
        print(f"Processing Google Vision for: {file_identifier}...")
        # Modified to accept bytes if available
        if is_bytes:
             page_texts = vision_ocr_client.extract_text_from_bytes(file_content)
        else:
             page_texts = vision_ocr_client.extract_text(file_content)
        
        # Manual save of raw result (for Vision)
        # Modified: Always save OCR results for debugging, even for bytes input
        if page_texts:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr_results")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename for bytes input if needed
            base_name = os.path.splitext(os.path.basename(file_identifier))[0]
            if is_bytes and file_identifier == "uploaded_file":
                # Use timestamp for unique filename
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = f"upload_{timestamp}"
            
            txt_filename = base_name + ".txt"
            txt_path = os.path.join(output_dir, txt_filename)
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n\n--- PAGE BREAK ---\n\n".join(page_texts))
                print(f"✅ [Vision] Saved raw OCR to: {txt_path}")
            except Exception as e:
                print(f"⚠️ OCR save error: {e}")
    else:
        print("Error: Missing Google Vision OCR client. Tesseract was removed.")
        return None

    if not page_texts:
        return None

    # Step 2: Use PrivacyGuard to anonymize text
    print(f"--- Anonymizing result for: {file_identifier} ---")
    
    # Profile construction based on patient context (if available)
    # Convert Pydantic model to dict if needed, or access attributes directly
    # Assuming patient_context is Pydantic model
    
    current_profile = USER_PROFILE.copy()
    if patient_context:
        # Check if it's pydantic model or dict
        first_name = getattr(patient_context, 'first_name', None) or patient_context.get('first_name')
        last_name = getattr(patient_context, 'last_name', None) or patient_context.get('last_name')
        dob_fragment = getattr(patient_context, 'dob_fragment', None) or patient_context.get('dob_fragment')
        address = getattr(patient_context, 'address', None) or patient_context.get('address')

        current_profile.update({
            "name": first_name,
            "lastname": last_name,
            "dob_fragment": dob_fragment,
            "address": address
        })
        print(f"Using provided patient context.") # REMOVED PII

    guard = PrivacyGuard(current_profile)
    anonymized_text = guard.anonymize(page_texts)
    
    # Save cleaned (anonymized) text for debugging
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaned_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename logic repeated
    base_name = os.path.splitext(os.path.basename(file_identifier))[0]
    if is_bytes and file_identifier == "uploaded_file":
         import datetime
         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
         base_name = f"upload_{timestamp}"

    txt_filename = base_name + "_cleaned.txt"
    txt_path = os.path.join(output_dir, txt_filename)
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(anonymized_text)
        print(f"✅ Saved anonymized text to: {txt_path}")
    except Exception as e:
        print(f"⚠️ Error saving cleaned_results: {e}")

    # Step 3: Medical Analysis by LLM
    print(f"--- LLM Analysis for: {file_identifier} ---")
    analysis_result = analyzer_instance.analyze_text(anonymized_text)
    
    # Processing the result
    if analysis_result:
        # Save JSON with results (always enabled for debugging)
        if SAVE_JSON_ENABLED:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json_results")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename logic repeated (should refactor, but keeping inline for now)
            base_name = os.path.splitext(os.path.basename(file_identifier))[0]
            if is_bytes and file_identifier == "uploaded_file":
                 import datetime
                 # Reuse timestamp if possible or generate new one (might differ slightly from OCR if heavy load)
                 # Better to pass filename from server.py, but for now unique enough
                 timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                 base_name = f"upload_{timestamp}"

            json_filename = base_name + ".json"
            json_path = os.path.join(output_dir, json_filename)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(analysis_result, f, indent=4, ensure_ascii=False)
                print(f"✅ Saved JSON result to: {json_path}")
            except Exception as e:
                print(f"⚠️ Error saving JSON: {e}")

        # Flattening results to a table (optional, depending on needs)
        # return flat_result if flat_result else analysis_result
        return analysis_result # Returning full JSON as expected by the server
    
    return None

def main():
    print("Scanning folder for PDF files...")
    # Changed path to uploads directory in project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    uploads_dir = os.path.join(project_root, "uploads")
    
    # Ensure uploads directory exists
    if not os.path.exists(uploads_dir):
        print(f"Directory {uploads_dir} does not exist. Creating it...")
        os.makedirs(uploads_dir)
        
    files = glob.glob(os.path.join(uploads_dir, "*.pdf"))

    print(f"Found files: {len(files)}")

    # Initialize OCR (if Google Vision is selected)
    vision_ocr = None
    if USE_GOOGLE_VISION:
        # GCP key path relative to engine-python directory
        key_path = os.path.abspath(os.path.join(current_dir, GCP_KEY_PATH))
        
        # Check if key file exists
        if not os.path.exists(key_path):
            print(f"ERROR: GCP key file not found at path: {key_path}")
            print("Make sure gcp_key.json is in the engine-python directory.")
            return

        vision_ocr = GoogleVisionOCR(key_path, poppler_path=r'C:\poppler-25.12.0\Library\bin')

    # Initialize analyzer
    analyzer = MedicalAnalyzer()

    all_results = []

    for file in files:
        data = process_single_file(file, vision_ocr, analyzer)
        
        if data:
            all_results.append(data)
        else:
            print(f"Failed to retrieve data from file: {os.path.basename(file)}")

        # For text, limits are looser, short delay is enough
        time.sleep(2)

    # Step 4: Display results (JSON)
    if not all_results:
        print("No data to analyze.")
        return

    print("\n--- ANALYSIS RESULTS (JSON) ---")
    print(json.dumps(all_results, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()