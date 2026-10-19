# Lance Mue en local : API Django, worker Huey et front Vite (Ctrl+C pour tout arrêter).
# Usage : .\dev.ps1            -> lancement
#         .\dev.ps1 install    -> installation des dépendances
#         .\dev.ps1 test       -> tests
param([string]$cmd = "dev")

$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
$manage = Join-Path $root "backend\manage.py"

switch ($cmd) {
    "install" {
        python -m venv (Join-Path $root "backend\.venv")
        & $py -m pip install -r (Join-Path $root "backend\requirements.txt")
        Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
        & $py $manage migrate
        if (-not (Test-Path (Join-Path $root ".env"))) { Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env") }
    }
    "test" {
        Push-Location (Join-Path $root "backend"); & $py -m pytest -q; Pop-Location
        Push-Location (Join-Path $root "frontend"); npm run typecheck; Pop-Location
    }
    default {
        & $py $manage migrate --no-input | Out-Null
        $procs = @(
            Start-Process $py -ArgumentList "`"$manage`" runserver 127.0.0.1:8040" -NoNewWindow -PassThru
            Start-Process $py -ArgumentList "`"$manage`" run_huey -w 1 -k thread" -NoNewWindow -PassThru
            Start-Process "npm.cmd" -ArgumentList "run dev" -WorkingDirectory (Join-Path $root "frontend") -NoNewWindow -PassThru
        )
        Write-Host "Mue : http://localhost:5173  (API : http://127.0.0.1:8040/api)" -ForegroundColor Green
        try { Wait-Process -Id ($procs | ForEach-Object Id) }
        finally { $procs | Where-Object { -not $_.HasExited } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } }
    }
}
