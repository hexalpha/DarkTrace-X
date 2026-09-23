param([string]$OutputDirectory = (Join-Path $PSScriptRoot '..\backups'))
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$target = [IO.Path]::GetFullPath((Join-Path $OutputDirectory $stamp))
New-Item -ItemType Directory -Force -Path $target | Out-Null
function Check-Docker { if ($LASTEXITCODE -ne 0) { throw 'Docker backup operation failed' } }
Push-Location $root
try {
    $remote = "/tmp/darktrace-$stamp.dump"
    docker compose exec -T postgres sh -c "pg_dump -U `$POSTGRES_USER -d `$POSTGRES_DB --format=custom --file=$remote"
    Check-Docker
    $destination = Join-Path $target 'postgres.dump'
    $copyPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    docker compose cp "postgres:$remote" $destination 2>$null | Out-Null
    $ErrorActionPreference = $copyPreference
    Check-Docker
    docker compose exec -T postgres rm -- $remote
    Check-Docker
    $repo = '{"type":"fs","settings":{"location":"/backups"}}'
    docker compose exec -T -e DARKTRACE_ES_PATH=/_snapshot/darktracex-backup elasticsearch sh /usr/local/bin/dtx-es-request *> $null
    if ($LASTEXITCODE -ne 0) {
        $repo | docker compose exec -T -e DARKTRACE_ES_PATH=/_snapshot/darktracex-backup elasticsearch sh /usr/local/bin/dtx-es-request -X PUT -H 'Content-Type: application/json' --data-binary '@-'
        Check-Docker
    }
    $snapshot = docker compose exec -T -e "DARKTRACE_ES_PATH=/_snapshot/darktracex-backup/${stamp}?wait_for_completion=true" elasticsearch sh /usr/local/bin/dtx-es-request -X PUT -H 'Content-Type: application/json' -d '{"include_global_state":false}'
    Check-Docker
    if (($snapshot | ConvertFrom-Json).snapshot.state -ne 'SUCCESS') { throw 'Snapshot did not succeed' }
    $snapshot | Set-Content -LiteralPath (Join-Path $target 'elasticsearch-snapshot.json') -Encoding utf8
    Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $target 'postgres.dump') | Select-Object Algorithm,Hash | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'checksum.json')
    Write-Output "Backup created: $target"
} finally { Pop-Location }
