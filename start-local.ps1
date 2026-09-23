param([switch]$RestartApi)
$ErrorActionPreference = 'Stop'
if ($RestartApi) {
    $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $apiProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        $expectedRuntime = Join-Path $PSScriptRoot 'apps\api\.venv313'
        if ($apiProcess.CommandLine.Contains($expectedRuntime) -and $apiProcess.CommandLine.Contains('uvicorn app.main:app')) {
            Stop-Process -Id $apiProcess.ProcessId
            Wait-Process -Id $apiProcess.ProcessId -Timeout 15 -ErrorAction SilentlyContinue
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) { break }
                Start-Sleep -Milliseconds 200
            }
        } else {
            throw 'Port 8000 belongs to a different process; no process was stopped.'
        }
    }
}
Push-Location (Join-Path $PSScriptRoot 'apps/api')
try {
    & '.\.venv313\Scripts\python.exe' -m scripts.local_runtime
} finally {
    Pop-Location
}
