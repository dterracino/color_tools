#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Find the nearest filaments to a given color.

.DESCRIPTION
    Searches the filament database for the closest matching filaments to a specified color.
    Uses the CIEDE2000 distance metric by default for perceptually accurate results.

.PARAMETER Hex
    Hex color code (e.g., "#7f0b00" or "7f0b00")

.PARAMETER Count
    Number of nearest filaments to return (default: 5, max: 50)

.PARAMETER Maker
    Filter by filament maker (e.g., "Bambu Lab", "Polymaker")
    Supports synonyms (e.g., "Bambu" works for "Bambu Lab")

.PARAMETER Type
    Filter by filament type (e.g., "PLA", "PETG", "TPU")

.PARAMETER Metric
    Distance metric to use (default: de2000)
    Options: euclidean, de76, de94, de2000, cmc

.EXAMPLE
    .\find-nearest-filament.ps1 -Hex "#7f0b00"
    Find the 5 nearest filaments to dark red

.EXAMPLE
    .\find-nearest-filament.ps1 -Hex "#7f0b00" -Count 10 -Maker "Bambu Lab"
    Find the 10 nearest Bambu Lab filaments to dark red

.EXAMPLE
    .\find-nearest-filament.ps1 -Hex "FF0000" -Type "PLA" -Count 3
    Find the 3 nearest PLA filaments to pure red
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Hex,
    
    [Parameter(Mandatory=$false)]
    [int]$Count = 5,
    
    [Parameter(Mandatory=$false)]
    [string]$Maker,
    
    [Parameter(Mandatory=$false)]
    [string]$Type,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("euclidean", "de76", "de94", "de2000", "cmc")]
    [string]$Metric = "de2000"
)

# Build the command
$cmd = "python -m color_tools filament --nearest --hex `"$Hex`" --count $Count --metric $Metric"

if ($Maker) {
    $cmd += " --maker `"$Maker`""
}

if ($Type) {
    $cmd += " --type `"$Type`""
}

# Execute the command
Write-Host "Searching for nearest filaments to $Hex..." -ForegroundColor Cyan
Invoke-Expression $cmd
