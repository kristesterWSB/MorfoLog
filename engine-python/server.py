import os
import uvicorn
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from main import process_single_file, GCP_KEY_PATH, USE_GOOGLE_VISION
from google_vision_ocr import GoogleVisionOCR
from analyzer import MedicalAnalyzer

app = FastAPI(title="Morfolog Analysis Service")

class PatientContext(BaseModel):
    first_name: str
    last_name: str
    dob_fragment: str
    address: Optional[str] = None

# Global services
vision_ocr = None
analyzer = None

@app.on_event("startup")
async def startup_event():
    global vision_ocr, analyzer
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Init OCR
    if USE_GOOGLE_VISION:
        key_path = os.path.abspath(os.path.join(current_dir, GCP_KEY_PATH))
        # Check if running in Linux/Docker (simple check)
        is_linux = os.name == 'posix'
        poppler_path = None if is_linux else r'C:\poppler-25.12.0\Library\bin'

        if os.path.exists(key_path):
            print(f"Inicjalizacja Google Vision z kluczem: {key_path}")
            vision_ocr = GoogleVisionOCR(key_path, poppler_path=poppler_path)
        else:
            print(f"BŁĄD: Nie znaleziono klucza GCP: {key_path}")
    
    print("Inicjalizacja MedicalAnalyzer...")
    analyzer = MedicalAnalyzer()

@app.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    patient_context: str = Form(...)
):
    filename = file.filename
    
    try:
        context_dict = {}
        try:
            context_dict = json.loads(patient_context)
        except (json.JSONDecodeError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in patient_context: {e}")

        print(f"Processing uploaded file {filename} for patient {context_dict.get('first_name')}")
        
        # Read file content into memory
        file_content = await file.read()
        
        # Determine which OCR to use
        ocr_engine = vision_ocr if vision_ocr else None
        
        # Process file bytes directly
        # Note: process_single_file needs to handle bytes now (we updated main.py previously)
        result_data = process_single_file(
            file_content, 
            ocr_engine, 
            analyzer, 
            patient_context=context_dict
        )
        
        results = []
        if result_data:
            results.append({
                "file": filename,
                "status": "success",
                "data": result_data
            })
        else:
             results.append({
                "file": filename,
                "status": "error",
                "data": {"error": "Processing returned no data"}
            })
            
        return {"results": results}

    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return {"results": [{
            "file": filename,
            "status": "error",
            "data": {"error": str(e)}
        }]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
