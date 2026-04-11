# Skrypt do wdrażania usługi Backend .NET na Google Cloud Run
#
# Przykładowe polecenie do zbudowania obrazu (uruchom przed wdrożeniem jeśli masz zmiany w kodzie):
# gcloud builds submit --tag europe-central2-docker.pkg.dev/gen-lang-client-0852605338/morfolog/backend:latest ./backend-dotnet

$PROJECT_ID = "gen-lang-client-0852605338"
$REGION = "europe-central2"
$IMAGE_TAG = "supabase2" 
$REPO_NAME = "morfolog"
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/backend:$IMAGE_TAG"
$SERVICE_NAME = "morfolog-backend"

Write-Host "Pobieranie konfiguracji..." -ForegroundColor Cyan

# 1. Pobierz URL usługi AI (potrzebny do zmiennej środowiskowej)
$AI_SERVICE_URL = gcloud run services describe morfolog-ai --region $REGION --format="value(status.url)"
if (-not $AI_SERVICE_URL) {
    Write-Host "Ostrzeżenie: Nie znaleziono usługi morfolog-ai. Upewnij się, że jest wdrożona." -ForegroundColor Yellow
    $AI_SERVICE_URL = "http://localhost:8000" # Fallback, choć w chmurze nie zadziała
} else {
    Write-Host " -> Wykryto AI Service URL: $AI_SERVICE_URL"
}

Write-Host "---------------------------------------------------"
Write-Host "Wdrażanie usługi $SERVICE_NAME..." -ForegroundColor Green
Write-Host "Obraz: $IMAGE_URI"
Write-Host "---------------------------------------------------"

# 3. Wdrożenie do Cloud Run
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --port 8080 `
    --memory 512Mi `
    --set-secrets="DB_CONNECTION_STRING=DB_CONNECTION_STRING:latest" `
    --set-env-vars "AiServiceUrl=$AI_SERVICE_URL,ASPNETCORE_ENVIRONMENT=Production" `
    --allow-unauthenticated

if ($LASTEXITCODE -eq 0) {
    $BACKEND_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"
    Write-Host "`nSUKCES! Usługa dostępna pod adresem:" -ForegroundColor Green
    Write-Host $BACKEND_URL -ForegroundColor Yellow
} else {
    Write-Host "`nWystąpił błąd podczas wdrażania." -ForegroundColor Red
}
