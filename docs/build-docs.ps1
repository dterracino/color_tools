# Build Color Tools documentation using Sphinx
# This script builds comprehensive API documentation from docstrings

param(
    [switch]$Clean,
    [switch]$Open,
    [string]$Builder = "html"
)

# Set error handling
$ErrorActionPreference = "Stop"

# Get script location
$DocsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SphinxDir = Join-Path $DocsRoot "sphinx"
$BuildDir = Join-Path $SphinxDir "_build"
$HtmlDir = Join-Path $BuildDir "html"

Write-Host "🎨 Building Color Tools API Documentation..." -ForegroundColor Cyan

# Clean build directory if requested
if ($Clean) {
    Write-Host "🧹 Cleaning build directory..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) {
        Remove-Item $BuildDir -Recurse -Force
    }
}

# Ensure we're in the project root
$ProjectRoot = Split-Path -Parent $DocsRoot
Set-Location $ProjectRoot

# Check if Sphinx is installed
try {
    & python -c "import sphinx" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Sphinx not found"
    }
} catch {
    Write-Host "❌ Sphinx not installed. Installing..." -ForegroundColor Red
    & pip install sphinx sphinx-rtd-theme myst-parser sphinx-autodoc-typehints
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install Sphinx" -ForegroundColor Red
        exit 1
    }
}

# Build documentation
Write-Host "📚 Building $Builder documentation..." -ForegroundColor Green
Set-Location $SphinxDir
& python -m sphinx -b $Builder . "_build/$Builder" --keep-going

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Documentation build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Documentation built successfully!" -ForegroundColor Green
Write-Host "📁 Output: $HtmlDir" -ForegroundColor Cyan

# Open in browser if requested
if ($Open -and $Builder -eq "html") {
    $IndexFile = Join-Path $HtmlDir "index.html"
    if (Test-Path $IndexFile) {
        Write-Host "🌐 Opening documentation in browser..." -ForegroundColor Cyan
        Start-Process $IndexFile
    }
}

# Return to project root
Set-Location $ProjectRoot

Write-Host "🎉 Done! To view the docs:" -ForegroundColor Green
Write-Host "   Open: $HtmlDir\index.html" -ForegroundColor White