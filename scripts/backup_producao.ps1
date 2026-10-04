param(
    [string]$Destino = "backups/radar_goiano.dump"
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$arquivo = Join-Path $raiz $Destino
$pasta = Split-Path -Parent $arquivo
$pgDump = 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe'

if (-not (Test-Path -LiteralPath $pgDump)) {
    throw "pg_dump nao encontrado em $pgDump"
}

New-Item -ItemType Directory -Path $pasta -Force | Out-Null
& $pgDump --format=custom --compress=9 --no-owner --no-acl `
    --dbname=radar_goiano --host=127.0.0.1 --port=5433 --username=postgres `
    --file=$arquivo
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar backup (codigo $LASTEXITCODE)." }

$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $arquivo
Write-Host "Backup: $arquivo"
Write-Host "SHA-256: $($hash.Hash)"
