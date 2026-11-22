# MorfoLog — Local Development Guide

This guide explains how to run the full MorfoLog stack on your local machine, either **from source** or with **Docker Compose**.

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  frontend-react │────▶│  backend-dotnet  │────▶│  engine-python  │
│  (Vite :5173)   │     │  (.NET 9 :8080)  │     │  (FastAPI :8000) │
└─────────────────┘     └───────┬──────────┘     └─────────────────┘
                                │
                        ┌───────▼──────────┐
                        │   PostgreSQL DB  │
                        │    (:5432)       │
                        └──────────────────┘
```

| Service | Local port | Docker Compose port |
|---------|-----------|---------------------|
| Frontend (Vite) | 5173 | — *(run outside Docker)* |
| Backend (.NET) | 8080 | 8080 |
| AI Engine (Python) | 8000 | 8088 → 8000 |
| PostgreSQL | 5432 | 5432 |

---

## Option 1 — Docker Compose (recommended)

This runs the **database**, **backend**, and **AI engine** in containers.  
The frontend runs on the host (Vite dev server) and talks to the backend at `localhost:8080`.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Node.js ≥ 18](https://nodejs.org/) (for the frontend).

### Steps

**1. Configure environment variables**

Create / verify the root `.env` file (`c:\MorfoLog\.env`):

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=admin
POSTGRES_DB=morfolog
GEMINI_API_KEY=your_gemini_api_key
```

Create / verify `engine-python/.env`:

```ini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-3.5-flash-lite
```

> [!NOTE]
> The `GEMINI_MODEL_NAME` variable lets you switch AI models without rebuilding images.

**2. Start the services**

```powershell
cd c:\MorfoLog
docker compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **AI Engine** on `localhost:8088` (mapped to container port 8000)
- **Backend .NET** on `localhost:8080`

Wait until you see the backend log confirming it's listening.

**3. Start the frontend**

In a separate terminal:

```powershell
cd c:\MorfoLog\frontend-react
npm install          # first time only
npm run dev
```

Vite starts on [http://localhost:5173](http://localhost:5173).  
It calls the backend at `http://localhost:8080` (configured in `frontend-react/.env.development`).

**4. Stop everything**

```powershell
# In the docker compose terminal:
Ctrl+C
docker compose down          # stops & removes containers
docker compose down -v       # also deletes the database volume (clean slate)
```

---

## Option 2 — Run from Source (no Docker)

Useful for debugging with breakpoints. Each service runs in its own terminal.

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| PostgreSQL | 16+ | [postgresql.org](https://www.postgresql.org/download/) |
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| .NET SDK | 9.0 | [dotnet.microsoft.com](https://dotnet.microsoft.com/download/dotnet/9.0) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Poppler | — | [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) (extract to `C:\poppler-25.12.0\`) |

### 1. Database (PostgreSQL)

Make sure PostgreSQL is running locally with:
- **User:** `postgres`
- **Password:** `admin`
- **Database:** `morfolog`

```sql
-- Create the database if it doesn't exist:
CREATE DATABASE morfolog;
```

### 2. AI Engine (Python) — Terminal 1

```powershell
cd c:\MorfoLog\engine-python

# Create venv (first time)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

The FastAPI server starts on `http://localhost:8000`.

> [!IMPORTANT]
> Make sure `engine-python/.env` contains a valid `GEMINI_API_KEY`.

### 3. Backend (.NET) — Terminal 2

```powershell
cd c:\MorfoLog\backend-dotnet

dotnet run
```

The .NET API starts on `http://localhost:8080`.

It reads `appsettings.Development.json` which points to:
- **Database:** `localhost:5432` (PostgreSQL)
- **AI Service:** `http://localhost:8088`

> [!WARNING]
> When running from source (not Docker), the AI Engine listens on port **8000**, but `appsettings.Development.json` references port **8088** (the Docker Compose mapped port). You may need to update `AiServiceUrl` to `http://localhost:8000` in `appsettings.Development.json` if running fully outside Docker.

### 4. Frontend (React) — Terminal 3

```powershell
cd c:\MorfoLog\frontend-react

npm install          # first time only
npm run dev
```

Opens on [http://localhost:5173](http://localhost:5173) → calls backend at `http://localhost:8080`.

---

## Environment Variable Reference

### Root `.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | — |
| `POSTGRES_DB` | Database name | `morfolog` |
| `GEMINI_API_KEY` | Google Gemini API key | — |

### `engine-python/.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `GEMINI_MODEL_NAME` | Gemini model to use | `gemini-3.5-flash-lite` |

### `frontend-react/.env.development`

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8080` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` on port 5432 | Make sure PostgreSQL is running (or `docker compose up db`) |
| AI Engine returns 500 | Check that `GEMINI_API_KEY` is set in `engine-python/.env` |
| Frontend shows network error | Verify backend is running on port 8080 and `VITE_API_URL` matches |
| `Poppler not found` (source mode) | Install Poppler and check path in `ocr_cleaner.py` |
| Docker build fails on engine-python | Make sure `gcp_key.json` exists in `engine-python/` (or create a placeholder) |
