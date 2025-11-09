# publish.ps1 - Build and publish color_tools to PyPI
# This script handles the complete build and upload process

param(
    [switch]$TestPyPI,
    [switch]$SkipTests,
    [switch]$SkipClean
)

# Color output helpers
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Warning { param($msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }

# Exit on error
$ErrorActionPreference = "Stop"

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Color Tools - PyPI Publishing Script ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Clean previous builds
if (-not $SkipClean) {
    Write-Step "Cleaning previous build artifacts"
    if (Test-Path ".\clean.ps1") {
        & .\clean.ps1
    } else {
        Write-Warning "clean.ps1 not found, skipping clean step"
    }
} else {
    Write-Warning "Skipping clean step (--SkipClean)"
}

# Step 2: Run tests
if (-not $SkipTests) {
    Write-Step "Running unit tests"
    try {
        $testOutput = python -m unittest discover -s tests -p "test_*.py" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All tests passed"
        } else {
            Write-Error "Tests failed!"
            Write-Host $testOutput
            exit 1
        }
    } catch {
        Write-Error "Failed to run tests: $_"
        exit 1
    }
} else {
    Write-Warning "Skipping tests (--SkipTests)"
}

# Step 3: Verify version number
Write-Step "Verifying version number"
try {
    $version = python -c "from color_tools import __version__; print(__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Version: $version"
        
        # Confirm with user
        $confirm = Read-Host "`nPublish version $version to PyPI? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Warning "Publish cancelled by user"
            exit 0
        }
    } else {
        Write-Error "Failed to get version number"
        exit 1
    }
} catch {
    Write-Error "Failed to verify version: $_"
    exit 1
}

# Step 4: Build package
Write-Step "Building distribution packages"
try {
    python -m build
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Build completed successfully"
        
        # Show what was built
        if (Test-Path "dist") {
            Write-Host "`nBuilt packages:" -ForegroundColor Yellow
            Get-ChildItem dist -Filter "*$version*" | ForEach-Object {
                Write-Host "  - $($_.Name)" -ForegroundColor White
            }
        }
    } else {
        Write-Error "Build failed!"
        exit 1
    }
} catch {
    Write-Error "Failed to build package: $_"
    exit 1
}

# Step 5: Upload to PyPI
Write-Step "Uploading to PyPI"

if ($TestPyPI) {
    Write-Warning "Uploading to TestPyPI (test.pypi.org)"
    $repository = "--repository testpypi"
} else {
    Write-Host "Uploading to PyPI (pypi.org)" -ForegroundColor Yellow
    $repository = ""
}

try {
    if ($repository) {
        python -m twine upload $repository dist/*$version*
    } else {
        python -m twine upload dist/*$version*
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Upload completed successfully!"
        
        Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "║       Publication Successful! 🎉       ║" -ForegroundColor Green
        Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Green
        
        if ($TestPyPI) {
            Write-Host "Install with: pip install --index-url https://test.pypi.org/simple/ color-match-tools" -ForegroundColor Cyan
        } else {
            Write-Host "Install with: pip install color-match-tools" -ForegroundColor Cyan
        }
        Write-Host "Version: $version`n" -ForegroundColor Cyan
    } else {
        Write-Error "Upload failed!"
        exit 1
    }
} catch {
    Write-Error "Failed to upload: $_"
    exit 1
}

# Optional: Clean up after successful publish
$cleanAfter = Read-Host "`nClean up build artifacts? (y/N)"
if ($cleanAfter -eq 'y' -or $cleanAfter -eq 'Y') {
    Write-Step "Cleaning build artifacts"
    & .\clean.ps1
}

Write-Host "`nDone! ✨`n" -ForegroundColor Green
