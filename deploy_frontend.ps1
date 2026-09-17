# Script for building and deploying the frontend to Firebase and updating the backend
# Make sure you have firebase-tools installed: npm install -g firebase-tools
# Make sure you are logged in: firebase login
# Make sure you have initialized the project: cd frontend-react; firebase init hosting

$FrontendPath = "frontend-react"
$BackendServiceName = "morfolog-backend"
$Region = "europe-central2"

Write-Host "--- Starting Frontend deployment ---" -ForegroundColor Cyan

# 1. Check if .env.production exists and has the correct backend URL
if (-not (Test-Path "$FrontendPath\.env.production")) {
    Write-Host "Error: Missing .env.production file! Run the configuration script." -ForegroundColor Red
    exit 1
}

# 2. Building React application
Write-Host "2. Building React application..." -ForegroundColor Cyan
Push-Location $FrontendPath
npm install
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Application build error." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3. Deployment to Firebase
Write-Host "3. Deploying to Firebase..." -ForegroundColor Cyan
# We use --json to easily extract the URL, but firebase deploy doesn't always return clean JSON to stdout
# So we'll just run it and ask the user to check the URL, or try to find it.
firebase deploy --only hosting

if ($LASTEXITCODE -ne 0) {
    Write-Host "Firebase deployment error. Make sure you ran 'firebase init' in the frontend-react folder." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host "`n---------------------------------------------------" -ForegroundColor Green
Write-Host "Frontend deployed!" -ForegroundColor Green
Write-Host "Now you need to update the backend to accept connections from the new domain." -ForegroundColor Yellow
Write-Host "Enter the URL (Hosting URL) from the log above below (e.g. https://your-project.web.app):"
$FrontendUrl = Read-Host "Frontend URL"

if (-not [string]::IsNullOrWhiteSpace($FrontendUrl)) {
    Write-Host "Updating CORS configuration in the backend ($BackendServiceName)..." -ForegroundColor Cyan
    # Updating the environment variable AllowedCorsOrigins__0
    gcloud run services update $BackendServiceName `
        --region $Region `
        --update-env-vars "AllowedCorsOrigins__0=$FrontendUrl"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Backend updated! CORS should work." -ForegroundColor Green
    } else {
        Write-Host "Backend update error." -ForegroundColor Red
    }
} else {
    Write-Host "Skipped backend update." -ForegroundColor Yellow
}
