# Kill process using port 8000
Write-Host "Finding process using port 8000..." -ForegroundColor Yellow

$connections = netstat -ano | Select-String ":8000"

if ($connections) {
    Write-Host "Found connections on port 8000:" -ForegroundColor Green
    $connections | ForEach-Object {
        Write-Host $_
        
        # Extract PID (last column)
        $line = $_.ToString().Trim()
        $parts = $line -split '\s+'
        $pid = $parts[-1]
        
        if ($pid -match '^\d+$') {
            Write-Host "Killing process $pid..." -ForegroundColor Red
            try {
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Host "✓ Process $pid killed successfully" -ForegroundColor Green
            } catch {
                Write-Host "✗ Failed to kill process $pid : $_" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "✓ No process found using port 8000" -ForegroundColor Green
}

Write-Host "`nYou can now run: python main.py" -ForegroundColor Cyan
