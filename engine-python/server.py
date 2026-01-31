from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import uvicorn
from main import process_single_file, GCP_KEY_PATH, USE_GOOGLE_VISION
from google_vision_ocr import GoogleVisionOCR
from analyzer import MedicalAnalyzer

app = FastAPI(title="Morfolog Analysis Service")

# Modele danych
class AnalyzeRequest(BaseModel):
    file_paths: List[str]  # Zmiana z pojedynczego stringa na listę stringów

# Zmienne globalne na instancje usług
vision_ocr = None
analyzer = None

@app.on_event("startup")
async def startup_event():
    global vision_ocr, analyzer
    
    # Inicjalizacja ścieżek
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Inicjalizacja OCR
    if USE_GOOGLE_VISION:
        key_path = os.path.abspath(os.path.join(current_dir, GCP_KEY_PATH))
        if os.path.exists(key_path):
            print(f"Inicjalizacja Google Vision z kluczem: {key_path}")
            vision_ocr = GoogleVisionOCR(key_path, poppler_path=r'C:\poppler-25.12.0\Library\bin')
        else:
            print(f"BŁĄD: Nie znaleziono klucza GCP: {key_path}")
    
    # Inicjalizacja Analyzera
    print("Inicjalizacja MedicalAnalyzer...")
    analyzer = MedicalAnalyzer()

@app.post("/analyze")
async def analyze_files(request: AnalyzeRequest):
    results = []
    errors = []

    for path in request.file_paths:
        if not os.path.exists(path):
            errors.append({"file": path, "error": "File not found"})
            continue
        
        try:
            # Używamy funkcji z main.py
            print(f"Przetwarzanie pliku: {path}")
            result = process_single_file(path, vision_ocr, analyzer)
            
            if result:
                results.append({
                    "file": path,
                    "status": "success",
                    "data": result
                })
            else:
                errors.append({"file": path, "error": "Analysis returned empty result"})
                
        except Exception as e:
            print(f"Błąd przy przetwarzaniu {path}: {str(e)}")
            errors.append({"file": path, "error": str(e)})

    # Zwracamy raport zbiorczy
    return {
        "processed_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
