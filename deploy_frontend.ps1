# Skrypt do budowania i wdrażania frontendu na Firebase oraz aktualizacji backendu
# Upewnij się, że masz zainstalowane firebase-tools: npm install -g firebase-tools
# Upewnij się, że jesteś zalogowany: firebase login
# Upewnij się, że zainicjowałeś projekt: cd frontend-react; firebase init hosting

$FrontendPath = "frontend-react"
$BackendServiceName = "morfolog-backend"
$Region = "europe-central2"

Write-Host "--- Rozpoczynam wdrażanie Frontend ---" -ForegroundColor Cyan

# 1. Sprawdź czy .env.production istnieje i ma poprawny URL backendu
if (-not (Test-Path "$FrontendPath\.env.production")) {
    Write-Host "Błąd: Brak pliku .env.production! Uruchom skrypt konfiguracji." -ForegroundColor Red
    exit 1
}

# 2. Budowanie aplikacji React
Write-Host "2. Budowanie aplikacji React..." -ForegroundColor Cyan
Push-Location $FrontendPath
npm install
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Błąd budowania aplikacji." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3. Wdrożenie do Firebase
Write-Host "3. Wdrażanie do Firebase..." -ForegroundColor Cyan
# Używamy --json aby łatwiej wyciągnąć URL, ale firebase deploy nie zawsze zwraca czysty JSON na stdout
# Więc po prostu uruchomimy i poprosimy użytkownika o sprawdzenie URL, albo spróbujemy go znaleźć.
firebase deploy --only hosting

if ($LASTEXITCODE -ne 0) {
    Write-Host "Błąd wdrożenia do Firebase. Upewnij się, że wykonałeś 'firebase init' w folderze frontend-react." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host "`n---------------------------------------------------" -ForegroundColor Green
Write-Host "Frontend wdrożony!" -ForegroundColor Green
Write-Host "Teraz musisz zaktualizować backend, aby akceptował połączenia z nowej domeny." -ForegroundColor Yellow
Write-Host "Wpisz poniżej adres URL (Hosting URL) z powyższego logu (np. https://twoj-projekt.web.app):"
$FrontendUrl = Read-Host "URL Frontendu"

if (-not [string]::IsNullOrWhiteSpace($FrontendUrl)) {
    Write-Host "Aktualizuję konfigurację CORS w backendzie ($BackendServiceName)..." -ForegroundColor Cyan
    # Aktualizujemy zmienną środowiskową AllowedCorsOrigins__0
    gcloud run services update $BackendServiceName `
        --region $Region `
        --update-env-vars "AllowedCorsOrigins__0=$FrontendUrl"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Backend zaktualizowany! CORS powinien działać." -ForegroundColor Green
    } else {
        Write-Host "Błąd aktualizacji backendu." -ForegroundColor Red
    }
} else {
    Write-Host "Pominięto aktualizację backendu." -ForegroundColor Yellow
}
