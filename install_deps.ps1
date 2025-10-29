# PowerShell installer for Windows
$req = "requirements.txt"
$venv = ".venv"

if (-not (Test-Path $req)) {
    Write-Error "requirements.txt not found in current folder."
    exit 1
}

python -m pip install --upgrade pip setuptools wheel

if (-not (Test-Path $venv)) {
    python -m venv $venv
}

$activate = Join-Path $venv "Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtualenv..."
    & $activate
} else {
    Write-Host "Virtualenv created. Activate manually: .\$venv\Scripts\Activate.ps1"
}

pip install --upgrade pip
pip install -r $req

Write-Host "Done. Activate venv and run: python bot_gui.py"
