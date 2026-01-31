# Medical Lab Results Analyzer

This project automates the digitization, analysis, and visualization of medical laboratory results from PDF files. It uses OCR to read documents, AI (Gemini/xAI) to structure the data, and Matplotlib to generate trend charts for health parameters over time.

## Features

*   **OCR Processing:** Converts PDF medical reports into text using Tesseract and Poppler.
*   **Privacy Guard:** Anonymizes sensitive personal data (Name, PESEL, Address) before sending text to external APIs.
*   **AI Extraction:** Uses Google Gemini (or xAI Grok as fallback) to parse unstructured text into structured JSON data.
*   **Trend Visualization:** Generates graphs for specific health parameters (e.g., TSH, Glucose, Cholesterol) to track changes over time.
*   **Data Flattening:** Converts complex JSON structures into Pandas DataFrames for easy analysis.

## Prerequisites

Before running the Python script, you must install the following system tools:

### 1. Tesseract OCR
Download and install Tesseract OCR for Windows.
*   **Download:** [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
*   **Note:** Remember the installation path (default: `C:\Program Files\Tesseract-OCR\tesseract.exe`).

### 2. Poppler
Poppler is required by `pdf2image` to convert PDF pages into images.
*   **Download:** Poppler for Windows
*   **Installation:** Extract the archive to a permanent location (e.g., `C:\poppler-25.12.0\`).
*   **Note:** You will need the path to the `bin` folder (e.g., `C:\poppler-25.12.0\Library\bin`).

## Installation

1.  **Clone the repository** (or download the files).
2.  **Create a virtual environment** (optional but recommended):
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

### 1. Environment Variables (.env)
Create a `.env` file in the root directory (`C:/MorfoLog/.env`) and add your API keys and personal details for anonymization:

```ini
# AI Provider Keys
GEMINI_API_KEY=your_google_gemini_key
XAI_API_KEY=your_xai_grok_key

# User Profile (For Anonymization)
USER_NAME=Jan
USER_LASTNAME=Kowalski
USER_PESEL=90010112345
USER_ADDRESS=Ul. Przykładowa 1, 00-001 Warszawa
```

### 2. System Paths
Open `ocr_cleaner.py` and update the configuration section at the top to match your installation paths for Poppler and Tesseract:

```python
# ocr_cleaner.py

# --- CONFIGURATION ---
POPPLER_PATH = r'C:\path\to\poppler\Library\bin'
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Usage

1.  Place your medical result PDF files in the project root folder (`C:/MorfoLog/`).
2.  Run the main script:

    ```bash
    python main.py
    ```

3.  **The script will:**
    *   Scan for `*.pdf` files.
    *   Perform OCR and save raw text to `ocr_results/`.
    *   Anonymize the text and save it to `cleaned_results/`.
    *   Send the text to AI to extract data.
    *   Save the structured data to `json_results/`.
    *   Display a summary table in the console.
    *   Generate and display charts for detected parameters.

## Project Structure

*   `main.py`: The entry point. Orchestrates the workflow, processes data with Pandas, and draws plots.
*   `analyzer.py`: Handles communication with AI APIs (Gemini/xAI) and defines the data schema.
*   `ocr_cleaner.py`: Handles PDF conversion, OCR, and text anonymization logic.
*   `requirements.txt`: List of Python libraries required.

## Troubleshooting

*   **"Poppler not found":** Ensure `POPPLER_PATH` in `ocr_cleaner.py` points correctly to the `bin` folder containing `pdftoppm.exe`.
*   **"Tesseract not found":** Ensure `TESSERACT_CMD` points to the `tesseract.exe` executable.
*   **Empty Charts:** The script currently filters for numeric values. Text-based results (e.g., "negative") are ignored for plotting.