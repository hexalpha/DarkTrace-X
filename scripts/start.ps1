param([string]$EnvironmentFile = (Join-Path $PSScriptRoot '..\.runtime\deployment.env'), [switch]$Production)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environment = (Resolve-Path -LiteralPath $EnvironmentFile).Path
Push-Location $root
try {
    $files = @('-f', 'docker-compose.yml', '-f', 'docker-compose.elasticsearch-tls.yml')
    if ($Production) { $files += @('-f', 'docker-compose.tls.yml') }
    docker compose --env-file $environment @files up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Startup failed; inspect service health before using the application.' }
} finally { Pop-Location }
