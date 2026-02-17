from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
from main import process_single_file, GCP_KEY_PATH, USE_GOOGLE_VISION
from google_vision_ocr import GoogleVisionOCR
from analyzer import MedicalAnalyzer

app = FastAPI(title="Morfolog Analysis Service")

class PatientContext(BaseModel):
    first_name: str
    last_name: str
    dob_fragment: str
    address: Optional[str] = None

# Updated request model
class AnalyzeRequest(BaseModel):
    file_path: str
    patient_context: PatientContext

# Global services
vision_ocr = None
analyzer = None

@app.on_event("startup")
async def startup_event():
    global vision_ocr, analyzer
    
    # Init paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Init OCR
    if USE_GOOGLE_VISION:
        key_path = os.path.abspath(os.path.join(current_dir, GCP_KEY_PATH))
        if os.path.exists(key_path):
            print(f"Inicjalizacja Google Vision z kluczem: {key_path}")
            vision_ocr = GoogleVisionOCR(key_path, poppler_path=r'C:\poppler-25.12.0\Library\bin')
        else:
            print(f"BŁĄD: Nie znaleziono klucza GCP: {key_path}")
    
    # Init Analyzer
    print("Inicjalizacja MedicalAnalyzer...")
    analyzer = MedicalAnalyzer()

@app.post("/analyze")
async def analyze_file(request: AnalyzeRequest):
    results = []
    path = request.file_path
    
    if not os.path.exists(path):
        return {"results": [{"file": path, "status": "error", "data": {"error": "File not found"}}]}
    
    try:
        # Pass patient context to processing logic if needed
        # For now, we just pass the file path as before, but in future use context
        print(f"Processing {path} for patient {request.patient_context.first_name} {request.patient_context.last_name}")
        
        # Determine which OCR to use
        ocr_engine = vision_ocr if vision_ocr else None
        
        # Process file
        result_data = process_single_file(path, ocr_engine, analyzer, patient_context=request.patient_context)
        
        results.append({
            "file": path,
            "status": "success",
            "data": result_data
        })
        
    except Exception as e:
        print(f"Error processing {path}: {str(e)}")
        results.append({
            "file": path,
            "status": "error",
            "data": {"error": str(e)}
        })
    
    return {"results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
