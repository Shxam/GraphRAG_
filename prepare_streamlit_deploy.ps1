# PowerShell script to prepare for Streamlit Cloud deployment

Write-Host "Preparing for Streamlit Cloud deployment..." -ForegroundColor Green

# Backup current requirements.txt
if (Test-Path "requirements.txt") {
    Write-Host "Backing up requirements.txt to requirements-full.txt" -ForegroundColor Yellow
    Copy-Item "requirements.txt" "requirements-full.txt" -Force
}

# Use minimal requirements for Streamlit
if (Test-Path "requirements-streamlit.txt") {
    Write-Host "Copying requirements-streamlit.txt to requirements.txt" -ForegroundColor Yellow
    Copy-Item "requirements-streamlit.txt" "requirements.txt" -Force
} else {
    Write-Host "ERROR: requirements-streamlit.txt not found!" -ForegroundColor Red
    exit 1
}

# Verify Python version file
if (Test-Path ".python-version") {
    $pythonVersion = Get-Content ".python-version"
    Write-Host "Python version set to: $pythonVersion" -ForegroundColor Cyan
} else {
    Write-Host "WARNING: .python-version file not found" -ForegroundColor Yellow
}

Write-Host "`nReady for Streamlit Cloud deployment!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Commit and push changes to GitHub" -ForegroundColor White
Write-Host "2. Go to https://share.streamlit.io" -ForegroundColor White
Write-Host "3. Deploy with main file: evaluation/dashboard.py" -ForegroundColor White
Write-Host "4. Set Python version: 3.11" -ForegroundColor White
Write-Host "`nAfter deployment, run restore_requirements.ps1 to restore full requirements" -ForegroundColor Yellow
