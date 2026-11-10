param([switch]$Setup)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (!$pythonCommand) { throw 'Install Python 3.11+ and add it to PATH.' }
    & $pythonCommand.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        & $pythonCommand.Source -m virtualenv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Install Python with venv support, or run: python -m pip install virtualenv' }
    }
    $Setup = $true
}
if ($Setup) {
    & $pythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
Write-Host 'Estoque Local: http://127.0.0.1:8765'
& $pythonPath run.py
