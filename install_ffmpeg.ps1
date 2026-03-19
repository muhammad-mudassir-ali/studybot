$ErrorActionPreference = "Stop"

$url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$zipPath = "g:\ffmpeg.zip"
$extractDir = "g:\ffmpeg"
$ffmpegBin = "g:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"

Write-Host "Downloading FFmpeg from $url..."
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting FFmpeg to $extractDir..."
if (Test-Path $extractDir) {
    Remove-Item -Recurse -Force $extractDir
}
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

Write-Host "Updating User PATH..."
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notmatch [regex]::Escape($ffmpegBin)) {
    $newPath = $userPath + ";" + $ffmpegBin
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $ffmpegBin to User PATH."
} else {
    Write-Host "$ffmpegBin is already in User PATH."
}

Write-Host "Cleaning up $zipPath..."
Remove-Item -Force $zipPath

Write-Host "FFmpeg installation script complete."
