param(
    [ValidateSet('iniciar', 'status', 'validar')]
    [string]$Acao = 'iniciar'
)

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$PastaExecucao = Join-Path $Raiz '.run'

function Testar-Porta([int]$Porta) {
    $cliente = [System.Net.Sockets.TcpClient]::new()
    try {
        $resultado = $cliente.BeginConnect('127.0.0.1', $Porta, $null, $null)
        if (-not $resultado.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $cliente.EndConnect($resultado)
        return $true
    } catch {
        return $false
    } finally {
        $cliente.Dispose()
    }
}

function Exibir-Status {
    foreach ($servico in @(
        @{ Nome = 'PostgreSQL'; Porta = 5433 },
        @{ Nome = 'API'; Porta = 8000 },
        @{ Nome = 'Frontend'; Porta = 5173 }
    )) {
        $estado = if (Testar-Porta $servico.Porta) { 'ativo' } else { 'inativo' }
        Write-Host ("{0,-12} porta {1}: {2}" -f $servico.Nome, $servico.Porta, $estado)
    }
}

function Validar-Sistema {
    $falhas = @()
    foreach ($url in @('http://127.0.0.1:8000/', 'http://127.0.0.1:8000/docs', 'http://127.0.0.1:5173/')) {
        try {
            $resposta = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
            Write-Host "$url -> HTTP $($resposta.StatusCode)"
        } catch {
            $falhas += "$url -> $($_.Exception.Message)"
        }
    }
    if ($falhas.Count) { throw ($falhas -join [Environment]::NewLine) }
}

if ($Acao -eq 'status') { Exibir-Status; exit 0 }
if ($Acao -eq 'validar') { Validar-Sistema; exit 0 }

New-Item -ItemType Directory -Path $PastaExecucao -Force | Out-Null

if (-not (Testar-Porta 5433)) {
    $pgCtl = 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe'
    $pgData = 'C:\Program Files\PostgreSQL\18\data'
    if (-not (Test-Path -LiteralPath $pgCtl)) { throw "pg_ctl não encontrado em $pgCtl" }
    $iniciado = $false
    for ($tentativaPg = 1; $tentativaPg -le 3; $tentativaPg++) {
        & $pgCtl start -D $pgData -l (Join-Path $PastaExecucao 'postgresql.log') -w
        if ($LASTEXITCODE -eq 0 -or (Testar-Porta 5433)) {
            $iniciado = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $iniciado) { throw 'Não foi possível iniciar o PostgreSQL após três tentativas.' }
}

if (-not (Testar-Porta 8000)) {
    $api = Start-Process -FilePath 'python' `
        -ArgumentList @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory (Join-Path $Raiz 'backend') `
        -RedirectStandardOutput (Join-Path $PastaExecucao 'api.out.log') `
        -RedirectStandardError (Join-Path $PastaExecucao 'api.err.log') `
        -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath (Join-Path $PastaExecucao 'api.pid') -Value $api.Id
}

if (-not (Testar-Porta 5173)) {
    $frontend = Start-Process -FilePath 'npm.cmd' `
        -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173') `
        -WorkingDirectory (Join-Path $Raiz 'frontend/radar-front') `
        -RedirectStandardOutput (Join-Path $PastaExecucao 'frontend.out.log') `
        -RedirectStandardError (Join-Path $PastaExecucao 'frontend.err.log') `
        -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath (Join-Path $PastaExecucao 'frontend.pid') -Value $frontend.Id
}

for ($tentativa = 1; $tentativa -le 30; $tentativa++) {
    if ((Testar-Porta 8000) -and (Testar-Porta 5173)) { break }
    Start-Sleep -Seconds 1
}

Exibir-Status
Validar-Sistema
Write-Host 'Radar Goiano disponível em http://127.0.0.1:5173/'
