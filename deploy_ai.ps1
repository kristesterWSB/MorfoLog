# Script for deploying the AI Engine service on Google Cloud Run
#build_image command 
# gcloud builds submit --tag europe-central2-docker.pkg.dev gen-lang-client-0852605338/morfolog/ai-engine:test4 ./engine-python
$PROJECT_ID = "gen-lang-client-0852605338"
$REGION = "europe-central2"
$IMAGE_TAG = "test4"
$IMAGE_URI = "europe-central2-docker.pkg.dev/$PROJECT_ID/morfolog/ai-engine:$IMAGE_TAG"
$SERVICE_NAME = "morfolog-ai"

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
