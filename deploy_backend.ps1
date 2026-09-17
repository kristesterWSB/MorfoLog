# Script for deploying the .NET Backend service on Google Cloud Run
#
# Example command to build the image (run before deployment if you have code changes):
# gcloud builds submit --tag europe-central2-docker.pkg.dev/gen-lang-client-0852605338/morfolog/backend:latest ./backend-dotnet

$PROJECT_ID = "gen-lang-client-0852605338"
$REGION = "europe-central2"
$IMAGE_TAG = "test-dotnet2" 
$REPO_NAME = "morfolog"
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/backend:$IMAGE_TAG"
$SERVICE_NAME = "morfolog-backend"
$DB_INSTANCE_NAME = "morfolog-db-prod"

Write-Host "Fetching configuration..." -ForegroundColor Cyan

# 1. Get AI service URL (needed for environment variable)
$AI_SERVICE_URL = gcloud run services describe morfolog-ai --region $REGION --format="value(status.url)"
if (-not $AI_SERVICE_URL) {
    Write-Host "Warning: morfolog-ai service not found. Make sure it is deployed." -ForegroundColor Yellow
    $AI_SERVICE_URL = "http://localhost:8000" # Fallback, although it won't work in the cloud
} else {
    Write-Host " -> Detected AI Service URL: $AI_SERVICE_URL"
}

# 2. Get Database Connection Name (needed for Cloud SQL connection)
$INSTANCE_CONNECTION_NAME = gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)"
if (-not $INSTANCE_CONNECTION_NAME) {
    Write-Host "Error: Cloud SQL instance named $DB_INSTANCE_NAME not found" -ForegroundColor Red
    exit 1
}
Write-Host " -> Detected SQL Connection: $INSTANCE_CONNECTION_NAME"

Write-Host "---------------------------------------------------"
Write-Host "Deploying service $SERVICE_NAME..." -ForegroundColor Green
Write-Host "Image: $IMAGE_URI"
Write-Host "---------------------------------------------------"

# 3. Deployment to Cloud Run
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --port 8080 `
    --memory 512Mi `
    --set-secrets="DB_CONNECTION_STRING=DB_CONNECTION_STRING:latest" `
    --set-env-vars "AiServiceUrl=$AI_SERVICE_URL,ASPNETCORE_ENVIRONMENT=Production" `
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME `
    --allow-unauthenticated

if ($LASTEXITCODE -eq 0) {
    $BACKEND_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"
    Write-Host "`nSUCCESS! Service available at:" -ForegroundColor Green
    Write-Host $BACKEND_URL -ForegroundColor Yellow
} else {
    Write-Host "`nAn error occurred during deployment." -ForegroundColor Red
}
