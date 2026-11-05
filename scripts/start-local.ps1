param([int]$BackendPort=8000,[int]$FrontendPort=5173)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath=Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install backend dependencies first; see README.md.' }
$backendProcess=Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port',"$BackendPort") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try {
    $env:VITE_BACKEND_PROXY="http://127.0.0.1:$BackendPort"
    Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    pnpm dev --port $FrontendPort --strictPort
} finally {
    if (-not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    Set-Location -LiteralPath $projectRoot
}
