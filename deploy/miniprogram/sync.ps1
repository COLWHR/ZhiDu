param(
  [string]$Host = "150.158.166.38",
  [string]$User = "ubuntu",
  [string]$RemotePath = "/opt/zido/miniprogram",
  [string]$LocalPath = "C:\Users\陈昊天\Desktop\ZhiDo V1.1.2\miniprogram"
)

$ErrorActionPreference = "Stop"

Write-Host "This script assumes you can reach the remote SSH server from this machine."
Write-Host "It will upload the local miniprogram folder to $User@$Host:$RemotePath"

if (-not (Test-Path $LocalPath)) {
  throw "Local path not found: $LocalPath"
}

Write-Host "Suggested manual command if your environment supports SCP:"
Write-Host "scp -r `"$LocalPath`" ${User}@${Host}:$RemotePath"

Write-Host ""
Write-Host "If you prefer an interactive SSH session, create the remote directory first:"
Write-Host "mkdir -p $RemotePath"

