# Script for deploying the AI Engine service on Google Cloud Run
# Usage:
#   .\deploy_ai.ps1              -> Deploy existing image in Cloud Run
#   .\deploy_ai.ps1 -Build       -> Build image with Cloud Build first, then deploy
#   .\deploy_ai.ps1 -Build -Tag v2
param(
    [switch]$Build,
    [string]$Tag = "test4"
)

$PROJECT_ID = "gen-lang-client-0852605338"
$REGION = "europe-central2"
$IMAGE_TAG = $Tag
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/morfolog/ai-engine:$IMAGE_TAG"
$SERVICE_NAME = "morfolog-ai"

# 1. Optional build step using Cloud Build
if ($Build) {
    Write-Host "Building image $IMAGE_URI from ./engine-python..." -ForegroundColor Cyan
    gcloud builds submit --tag $IMAGE_URI ./engine-python
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed. Aborting deployment." -ForegroundColor Red
        exit 1
    }
}

# 2. Deploy to Cloud Run
Write-Host "Deploying service $SERVICE_NAME from image $IMAGE_URI..." -ForegroundColor Green

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --port 8080 `
    --memory 512Mi `
    --timeout 300 `
    --clear-secrets `
    --allow-unauthenticated

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment completed successfully!" -ForegroundColor Green
} else {
    Write-Host "An error occurred during deployment." -ForegroundColor Red
}
