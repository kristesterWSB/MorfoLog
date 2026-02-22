# --- KONFIGURACJA ---
# Zmień te wartości na swoje!
$PROJECT_ID = "gen-lang-client-0852605338"  # <--- WPISZ TUTAJ SWÓJ PROJECT ID Z GCP
$REGION = "europe-central2"              # Warszawa
$DB_PASSWORD = "daunting-adamant-among-penal" # <--- ZMIEŃ NA SILNE HASŁO
$INSTANCE_NAME = "morfolog-db-prod"
$REPO_NAME = "morfolog"

# --- ZMIENNE AUTOMATYCZNE ---
$BACKEND_IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/backend:latest"
$AI_IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/ai-engine:latest"

Write-Host "--- ROZPOCZYNAM WDROŻENIE MORFOLOG DO GCP ($PROJECT_ID) ---" -ForegroundColor Green

# 1. Ustawienie projektu
Write-Host "1. Konfiguracja gcloud..." -ForegroundColor Cyan
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# 2. Włączenie usług (API)
Write-Host "2. Włączanie wymaganych API (może potrwać kilka minut)..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com sql-component.googleapis.com

# 3. Utworzenie repozytorium na obrazy (Artifact Registry)
Write-Host "3. Tworzenie repozytorium Artifact Registry..." -ForegroundColor Cyan
# Sprawdź czy istnieje, jeśli nie to utwórz
if (!(gcloud artifacts repositories list --location=$REGION --filter="name:$REPO_NAME" --format="value(name)")) {
    gcloud artifacts repositories create $REPO_NAME --repository-format=docker --location=$REGION --description="Repozytorium MorfoLog"
} else {
    Write-Host "Repozytorium już istnieje." -ForegroundColor Yellow
}
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# 4. Budowanie i wypychanie obrazów (Cloud Build - szybciej niż lokalnie)
Write-Host "4. Budowanie obrazów w chmurze (Cloud Build)..." -ForegroundColor Cyan
# Backend
Write-Host "   -> Budowanie Backend..."
gcloud builds submit --tag $BACKEND_IMAGE ./backend-dotnet
# AI Engine
Write-Host "   -> Budowanie AI Engine..."
gcloud builds submit --tag $AI_IMAGE ./engine-python

# 5. Baza danych (Cloud SQL)
Write-Host "5. Tworzenie instancji Cloud SQL (PostgreSQL)... to zajmie ok. 5-10 minut..." -ForegroundColor Cyan
if (!(gcloud sql instances list --filter="name:$INSTANCE_NAME" --format="value(name)")) {
    # Dodano --edition=ENTERPRISE, co jest wymagane dla db-f1-micro w nowszych wersjach API
    gcloud sql instances create $INSTANCE_NAME --database-version=POSTGRES_16 --tier=db-f1-micro --edition=ENTERPRISE --region=$REGION --root-password=$DB_PASSWORD
} else {
    Write-Host "Instancja bazy danych już istnieje." -ForegroundColor Yellow
}

# Utworzenie bazy danych i użytkownika
Write-Host "   -> Konfiguracja bazy danych i użytkownika..."
gcloud sql databases create morfolog --instance=$INSTANCE_NAME --quiet 2>$null
gcloud sql users create postgres --instance=$INSTANCE_NAME --password=$DB_PASSWORD --quiet 2>$null

# Pobranie Connection Name (np. project:region:instance)
$INSTANCE_CONNECTION_NAME = gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)"
Write-Host "   -> Connection Name: $INSTANCE_CONNECTION_NAME" -ForegroundColor Green

# 6. Sekrety (Secret Manager)
Write-Host "6. Tworzenie sekretów..." -ForegroundColor Cyan

# a) DB Connection String (Format dla Cloud Run z Unix Socket)
$DB_CONN_STR = "Host=/cloudsql/$INSTANCE_CONNECTION_NAME;Database=morfolog;Username=postgres;Password=$DB_PASSWORD"
if (!(gcloud secrets list --filter="name:DB_CONNECTION_STRING" --format="value(name)")) {
    gcloud secrets create DB_CONNECTION_STRING --replication-policy="automatic"
}
echo $DB_CONN_STR | gcloud secrets versions add DB_CONNECTION_STRING --data-file=-

# c) Nadanie uprawnień dla Cloud Run do czytania sekretów
Write-Host "   -> Nadawanie uprawnień do sekretów..."
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$SERVICE_ACCOUNT = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor" --condition=None --quiet

# b) GCP Key dla AI - POMINIĘTO (Używamy ADC - Application Default Credentials)
# Kod w Pythonie automatycznie wykryje środowisko Cloud Run i użyje tożsamości konta serwisowego.

# 7. Wdrożenie AI Engine (Cloud Run)
Write-Host "7. Wdrażanie AI Engine (Cloud Run)..." -ForegroundColor Cyan
gcloud run deploy morfolog-ai `
    --image $AI_IMAGE `
    --region $REGION `
    --port 8000 `
    --memory 1Gi `
    --allow-unauthenticated

# Pobranie URL serwisu AI
$AI_SERVICE_URL = gcloud run services describe morfolog-ai --region $REGION --format="value(status.url)"
Write-Host "   -> AI Engine URL: $AI_SERVICE_URL" -ForegroundColor Green

# 8. Wdrożenie Backend (Cloud Run)
Write-Host "8. Wdrażanie Backend .NET (Cloud Run)..." -ForegroundColor Cyan
gcloud run deploy morfolog-backend `
    --image $BACKEND_IMAGE `
    --region $REGION `
    --port 8080 `
    --memory 512Mi `
    --set-secrets="DB_CONNECTION_STRING=DB_CONNECTION_STRING:latest" `
    --set-env-vars "AiServiceUrl=$AI_SERVICE_URL,ASPNETCORE_ENVIRONMENT=Production" `
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME `
    --allow-unauthenticated

# Pobranie URL Backendu
$BACKEND_URL = gcloud run services describe morfolog-backend --region $REGION --format="value(status.url)"

Write-Host "`n---------------------------------------------------" -ForegroundColor Green
Write-Host "WDROŻENIE ZAKOŃCZONE SUKCESEM!" -ForegroundColor Green
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Yellow
Write-Host "AI Engine URL: $AI_SERVICE_URL" -ForegroundColor Yellow
Write-Host "Baza danych: $INSTANCE_CONNECTION_NAME" -ForegroundColor Yellow
Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "Następne kroki:"
Write-Host "1. Zaktualizuj URL w Frontendzie (Vite) na: $BACKEND_URL"
Write-Host "2. Zbuduj frontend: npm run build"
Write-Host "3. Wdróż frontend na Firebase: firebase deploy"
