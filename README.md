# MorfoLog

MorfoLog is an AI-powered medical lab results analyzer and tracking application. It allows users to upload PDF scans or images of their medical test results (e.g., blood morphology), automatically extracts the data using OCR and AI, and visualizes the results over time to help track health trends.

## Project Architecture

The repository is organized into three main microservices/components:

- **`frontend-react/`**  
  A single-page application built with React, Vite, and TypeScript. Provides the user interface for uploading documents, managing profiles, and viewing historical health data trends via interactive charts.  
  *Deployment: Firebase Hosting*

- **`backend-dotnet/`**  
  A .NET 9 Web API serving as the main application gateway. It handles user requests, manages document storage and metadata in a PostgreSQL database (via Entity Framework Core), and orchestrates calls to the AI Engine for data extraction.  
  *Deployment: Google Cloud Run*

- **`engine-python/`**  
  A Python-based AI service that performs Optical Character Recognition (OCR) using Google Cloud Vision and structures the raw text into a predefined JSON schema using Google Gemini (GenAI). It also includes a PII cleaner (PrivacyGuard) to anonymize patient data before AI processing.  
  *Deployment: Google Cloud Run*

## Deployment

The repository includes PowerShell scripts for automated deployment to Google Cloud and Firebase:
- `deploy_ai.ps1`: Deploys the Python AI engine.
- `deploy_backend.ps1`: Deploys the .NET Web API.
- `deploy_frontend.ps1`: Deploys the React frontend and updates backend CORS settings.

## Development Guidelines

- **Language Policy**: All code, variables, functions, and inline comments **must be written in English**.
- **Commit Messages**: All commit messages must be in English.
- Please refer to `.github/CODE_COMMENTS.md` and `.github/copilot-instructions.md` for specific rules regarding AI-generated code.
