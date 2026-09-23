param(
    [Parameter(Mandatory=$true)][string]$BackupDirectory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9_]{0,50}$')][string]$Database,
    [switch]$ReplaceExisting,
    [switch]$RestoreElasticsearch,
    [ValidatePattern('^[a-z][a-z0-9_]{0,30}$')][string]$IndexPrefix = 'restored_'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
$dump = Join-Path $backup 'postgres.dump'
if (-not (Test-Path -LiteralPath $dump)) { throw 'postgres.dump is missing' }
$checksum = Get-Content -Raw -LiteralPath (Join-Path $backup 'checksum.json') | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $dump -Algorithm SHA256).Hash -ne $checksum.Hash) { throw 'Backup checksum mismatch' }
function Check-Docker { if ($LASTEXITCODE -ne 0) { throw 'Docker restore operation failed' } }
Push-Location $root
try {
    if (-not $ReplaceExisting) {
        docker compose exec -T postgres sh -c "createdb -U `$POSTGRES_USER $Database"
        Check-Docker
    }
    $remote = '/tmp/darktrace-restore-' + [guid]::NewGuid().ToString('N') + '.dump'
    docker compose cp $dump "postgres:$remote"
    Check-Docker
    $restoreOptions = @('--exit-on-error', '--no-owner', '--single-transaction')
    if ($ReplaceExisting) { $restoreOptions += @('--clean', '--if-exists') }
    docker compose exec -T postgres sh -c "pg_restore -U `$POSTGRES_USER -d $Database $($restoreOptions -join ' ') $remote"
    Check-Docker
    docker compose exec -T postgres rm -- $remote
    Check-Docker
    if ($RestoreElasticsearch) {
        $snapshot = (Get-Content -Raw -LiteralPath (Join-Path $backup 'elasticsearch-snapshot.json') | ConvertFrom-Json).snapshot.snapshot
        if ($snapshot -notmatch '^[0-9-]+$') { throw 'Invalid snapshot identifier' }
        $body = @{indices='darktracex-*';include_global_state=$false;rename_pattern='(.+)';rename_replacement=($IndexPrefix + '$1')} | ConvertTo-Json -Compress
        $body | docker compose exec -T -e "DARKTRACE_ES_PATH=/_snapshot/darktracex-backup/$snapshot/_restore?wait_for_completion=true" elasticsearch sh /usr/local/bin/dtx-es-request -X POST -H 'Content-Type: application/json' --data-binary '@-'
        Check-Docker
    }
    Write-Output "Restored database: $Database. Verify row counts and queries before switching application writers."
} finally { Pop-Location }
