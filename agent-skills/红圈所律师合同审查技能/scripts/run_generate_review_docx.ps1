[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Instructions,
    [Parameter(Mandatory = $true)][string]$Output,
    [string]$CleanOutput,
    [string]$Author,
    [ValidateSet("comment", "revision", "revision_comment")][string]$DefaultMode,
    [string]$Date
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "internal_generate_review_docx.ps1"
$scriptContent = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
$scriptBlock = [scriptblock]::Create($scriptContent)

$invokeArgs = @{
    Source = $Source
    Instructions = $Instructions
    Output = $Output
    InternalScriptRoot = $PSScriptRoot
}

if ($PSBoundParameters.ContainsKey("CleanOutput")) { $invokeArgs["CleanOutput"] = $CleanOutput }
if ($PSBoundParameters.ContainsKey("Author")) { $invokeArgs["Author"] = $Author }
if ($PSBoundParameters.ContainsKey("DefaultMode")) { $invokeArgs["DefaultMode"] = $DefaultMode }
if ($PSBoundParameters.ContainsKey("Date")) { $invokeArgs["Date"] = $Date }

& $scriptBlock @invokeArgs
