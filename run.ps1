# Stheno - Development Launcher

$ErrorActionPreference = "Stop"

# Di chuyển đến thư mục chứa file PS1
Set-Location $PSScriptRoot

# Kiểm tra virtual environment
if (!(Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: python -m venv .venv"
    exit 1
}

# Kích hoạt virtual environment
. .\.venv\Scripts\Activate.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "       PROJECT STHENO" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Chạy ứng dụng
python -m src.main