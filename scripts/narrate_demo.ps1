param([string]$OutputDirectory = 'output/demo-production')
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path -Parent $PSScriptRoot
$demoOut = [System.IO.Path]::GetFullPath((Join-Path $demoRoot $OutputDirectory))
New-Item -ItemType Directory -Force -Path $demoOut | Out-Null
Add-Type -AssemblyName System.Speech
$demoVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$demoVoice.SelectVoice('Microsoft Zira Desktop')
$demoVoice.Rate = 1
try {
    $demoScenes = Get-Content -Raw -LiteralPath (Join-Path $demoRoot 'docs/submission-final/narration.json') | ConvertFrom-Json
    foreach ($demoScene in $demoScenes) {
        $demoVoice.SetOutputToWaveFile((Join-Path $demoOut ($demoScene.id + '.wav')))
        $demoVoice.Speak($demoScene.text)
        $demoVoice.SetOutputToNull()
    }
} finally { $demoVoice.Dispose() }
Write-Output 'Created local synthetic narration; no external speech service used.'
