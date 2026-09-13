$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$conda = "C:\Users\Admin\miniconda3\Scripts\conda.exe"
if (-not (Test-Path -LiteralPath $conda)) {
    throw "Conda not found: $conda"
}

& $conda run -n yolo python run_server.py
