$ErrorActionPreference = "Stop"
$baseDir = "C:\Users\Administrator\.gemini\antigravity\scratch\tw3-voiceover\tool\piper"
$modelDir = Join-Path $baseDir "models"

if (!(Test-Path $baseDir)) {
    New-Item -ItemType Directory -Force -Path $baseDir | Out-Null
}
if (!(Test-Path $modelDir)) {
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
}

$zipPath = Join-Path $baseDir "piper.zip"

Write-Output "1. Downloading Piper Windows Binary (22MB)..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$client = New-Object System.Net.WebClient
$client.DownloadFile("https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip", $zipPath)

Write-Output "2. Extracting Piper..."
Expand-Archive -Path $zipPath -DestinationPath $baseDir -Force
Remove-Item -Path $zipPath -Force

Write-Output "3. Downloading Vietnamese Model JSON (5KB)..."
$client.DownloadFile("https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json", (Join-Path $modelDir "vi_VN-vais1000-medium.onnx.json"))

Write-Output "4. Downloading Vietnamese Model Weights (63MB)..."
$client.DownloadFile("https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx", (Join-Path $modelDir "vi_VN-vais1000-medium.onnx"))

Write-Output "Download and setup complete!"
