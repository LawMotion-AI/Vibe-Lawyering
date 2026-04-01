[CmdletBinding()]
param(
    [string]$SourcePattern,
    [string]$SourcePath,
    [string]$InstructionsPattern,
    [string]$InstructionsPath,
    [string]$WorkspaceRoot,
    [string]$SourceTempName = "source.docx",
    [string]$InstructionsTempName = "instructions.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-AsciiFileName([string]$Name, [string]$ExpectedExtension) {
    if ([string]::IsNullOrWhiteSpace($Name)) { throw "Temporary file name cannot be empty." }
    if ($Name -notmatch '^[\x20-\x7E]+$') { throw "Temporary file name must be ASCII: $Name" }
    $actualExtension = [System.IO.Path]::GetExtension($Name).ToLowerInvariant()
    if ($actualExtension -ne $ExpectedExtension) {
        throw "Temporary file name must use extension ${ExpectedExtension}: $Name"
    }
}

function Resolve-SingleFile([string]$Pattern) {
    $items = @(Get-ChildItem -Path $Pattern -File)
    if ($items.Count -eq 0) { throw "No file matched pattern: $Pattern" }
    if ($items.Count -gt 1) {
        $matched = ($items | ForEach-Object { $_.FullName }) -join "; "
        throw "Pattern matched multiple files, narrow the wildcard: $Pattern -> $matched"
    }
    $items[0]
}

function Resolve-InputFile([AllowNull()][string]$LiteralPath, [AllowNull()][string]$Pattern, [string]$Label, [bool]$Required) {
    $hasLiteralPath = -not [string]::IsNullOrWhiteSpace($LiteralPath)
    $hasPattern = -not [string]::IsNullOrWhiteSpace($Pattern)

    if ($hasLiteralPath -and $hasPattern) {
        throw "$Label accepts either a literal path or a wildcard pattern, not both."
    }
    if (-not $hasLiteralPath -and -not $hasPattern) {
        if ($Required) { throw "$Label is required." }
        return $null
    }
    if ($hasLiteralPath) {
        if (-not (Test-Path -LiteralPath $LiteralPath -PathType Leaf)) { throw "$Label does not exist: $LiteralPath" }
        return Get-Item -LiteralPath $LiteralPath
    }
    Resolve-SingleFile -Pattern $Pattern
}

function Copy-InputFile([System.IO.FileInfo]$Item, [AllowNull()][string]$LiteralPath, [AllowNull()][string]$Pattern, [string]$Destination) {
    if (-not [string]::IsNullOrWhiteSpace($LiteralPath)) {
        Copy-Item -LiteralPath $LiteralPath -Destination $Destination -Force
        return
    }
    Copy-Item -Path $Pattern -Destination $Destination -Force
}

Ensure-AsciiFileName -Name $SourceTempName -ExpectedExtension ".docx"
Ensure-AsciiFileName -Name $InstructionsTempName -ExpectedExtension ".json"

$sourceItem = Resolve-InputFile -LiteralPath $SourcePath -Pattern $SourcePattern -Label "Source" -Required $true
$instructionsItem = Resolve-InputFile -LiteralPath $InstructionsPath -Pattern $InstructionsPattern -Label "Instructions" -Required $false

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("review-stage-" + [guid]::NewGuid().ToString("N"))
}

$workspace = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$inputDir = Join-Path $workspace "input"
$outputDir = Join-Path $workspace "output"
[System.IO.Directory]::CreateDirectory($inputDir) | Out-Null
[System.IO.Directory]::CreateDirectory($outputDir) | Out-Null

$stagedSource = Join-Path $inputDir $SourceTempName
Copy-InputFile -Item $sourceItem -LiteralPath $SourcePath -Pattern $SourcePattern -Destination $stagedSource

$stagedInstructions = $null
if ($null -ne $instructionsItem) {
    $stagedInstructions = Join-Path $inputDir $InstructionsTempName
    Copy-InputFile -Item $instructionsItem -LiteralPath $InstructionsPath -Pattern $InstructionsPattern -Destination $stagedInstructions
}

$sourceStem = [System.IO.Path]::GetFileNameWithoutExtension($sourceItem.Name)
$originalOutputDir = Join-Path $sourceItem.DirectoryName ($sourceStem + "-Output")

[pscustomobject]@{
    source_original        = $sourceItem.FullName
    instructions_original  = if ($null -eq $instructionsItem) { $null } else { $instructionsItem.FullName }
    workspace_root         = $workspace
    staged_source          = $stagedSource
    staged_instructions    = $stagedInstructions
    staged_reviewed_docx   = Join-Path $outputDir "reviewed.docx"
    staged_clean_docx      = Join-Path $outputDir "clean.docx"
    original_output_dir    = $originalOutputDir
    original_reviewed_docx = Join-Path $originalOutputDir ($sourceStem + "-reviewed.docx")
    original_clean_docx    = Join-Path $originalOutputDir ($sourceStem + "-clean.docx")
} | ConvertTo-Json -Depth 4
