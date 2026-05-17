# PowerShell script to restore full requirements after Streamlit deployment

Write-Host "Restoring full requirements.txt..." -ForegroundColor Green

# Restore original requirements
if (Test-Path "requirements-full.txt") {
    Write-Host "Restoring requirements-full.txt to requirements.txt" -ForegroundColor Yellow
    Copy-Item "requirements-full.txt" "requirements.txt" -Force
    Write-Host "Full requirements restored!" -ForegroundColor Green
} else {
    Write-Host "ERROR: requirements-full.txt backup not found!" -ForegroundColor Red
    Write-Host "You may need to manually restore your requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nDone! Your local requirements.txt has been restored." -ForegroundColor Green
