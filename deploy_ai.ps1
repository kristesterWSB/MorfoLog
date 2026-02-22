# Skrypt do wdrażania usługi AI Engine na Google Cloud Run
#build_image command 
# gcloud builds submit --tag europe-central2-docker.pkg.dev gen-lang-client-0852605338/morfolog/ai-engine:test4 ./engine-python
$PROJECT_ID = "gen-lang-client-0852605338"
$REGION = "europe-central2"
$IMAGE_TAG = "test4"
$IMAGE_URI = "europe-central2-docker.pkg.dev/$PROJECT_ID/morfolog/ai-engine:$IMAGE_TAG"
$SERVICE_NAME = "morfolog-ai"

Write-Host "Wdrażanie usługi $SERVICE_NAME z obrazu $IMAGE_URI..." -ForegroundColor Green

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --port 8080 `
    --memory 512Mi `
    --timeout 300 `
    --clear-secrets `
    --allow-unauthenticated

if ($LASTEXITCODE -eq 0) {
    Write-Host "Wdrożenie zakończone sukcesem!" -ForegroundColor Green
} else {
    Write-Host "Wystąpił błąd podczas wdrażania." -ForegroundColor Red
}
