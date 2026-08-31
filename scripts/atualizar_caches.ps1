param(
    [int]$Ano,
    [switch]$Consolidado,
    [switch]$TodosOsAnos,
    [int]$AnoFinal = (Get-Date).Year,
    [int]$TimeoutMinutos = 15
)

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$Gerador = Join-Path $Raiz 'backend/gerar_cache.py'
$selecoes = @($PSBoundParameters.ContainsKey('Ano'), $Consolidado.IsPresent, $TodosOsAnos.IsPresent) | Where-Object { $_ }
if ($selecoes.Count -ne 1) {
    throw 'Informe exatamente uma opção: -Ano, -Consolidado ou -TodosOsAnos.'
}

$argumentos = @($Gerador, '--timeout-minutos', $TimeoutMinutos)
if ($PSBoundParameters.ContainsKey('Ano')) {
    $argumentos += @('--ano', $Ano)
} elseif ($Consolidado) {
    $argumentos += '--consolidado'
} else {
    $argumentos += @('--todos-os-anos', '--ano-final', $AnoFinal)
}

& python @argumentos
if ($LASTEXITCODE -ne 0) { throw "A geração dos caches terminou com código $LASTEXITCODE." }

$backend = Join-Path $Raiz 'backend/dados_gerados'
$frontend = Join-Path $Raiz 'frontend/radar-front/public/dados'
$divergencias = @()
Get-ChildItem -LiteralPath $backend -Filter 'cache_*.json' | ForEach-Object {
    $publico = Join-Path $frontend $_.Name
    try {
        $null = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
        if (-not (Test-Path -LiteralPath $publico) -or
            (Get-FileHash -LiteralPath $_.FullName).Hash -ne (Get-FileHash -LiteralPath $publico).Hash) {
            $divergencias += $_.Name
        }
    } catch {
        $divergencias += $_.Name
    }
}
if ($divergencias.Count) { throw "Caches inválidos ou divergentes: $($divergencias -join ', ')" }
Write-Host 'Caches gerados, validados e sincronizados com o frontend.'
