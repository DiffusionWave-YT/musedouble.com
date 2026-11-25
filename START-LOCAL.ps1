param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot 'storage/runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$localNodeDir = Join-Path $PSScriptRoot 'storage/tools/node'
if (-not $SkipInstall) {
    uv sync --locked --quiet
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias Python.' }
    uv run python scripts/setup_node.py
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar Node LTS local.' }
}
if (Test-Path -LiteralPath (Join-Path $localNodeDir 'node.exe')) {
    $env:Path = $localNodeDir + [IO.Path]::PathSeparator + $env:Path
}
if (-not $SkipInstall) {
    Push-Location web
    try { npm.cmd ci --no-fund --loglevel=error; if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias web.' } }
    finally { Pop-Location }
}
uv run python scripts/setup_local.py
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL local no está disponible.' }
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones.' }
uv run python scripts/grant_database.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los permisos.' }
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$launchers = @(
    @{name='redis'; exe=(Get-Command wsl.exe).Source; args='-d Ubuntu-22.04 -- bash -lc "exec $HOME/musedouble-redis/bin/redis-server $HOME/musedouble-redis/redis.conf"'; dir=$PSScriptRoot},
    @{name='api'; exe=$pythonExe; args='-m uvicorn app.main:application --host 127.0.0.1 --port 8010 --no-server-header --no-access-log'; dir=$PSScriptRoot},
    @{name='objects'; exe=$pythonExe; args='-m uvicorn workers.object_server:app --host 127.0.0.1 --port 9011 --no-server-header --no-access-log'; dir=$PSScriptRoot},
    @{name='worker'; exe=$pythonExe; args='-m arq workers.arq_worker.WorkerSettings'; dir=$PSScriptRoot},
    @{name='web'; exe=(Get-Command node).Source; args='node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3001'; dir=(Join-Path $PSScriptRoot 'web')}
)
foreach ($item in $launchers) {
    $pidPath = Join-Path $runtimeDir ($item.name + '.pid')
    if (Test-Path -LiteralPath $pidPath) {
        $servicePid = [int](Get-Content -LiteralPath $pidPath)
        if (Get-Process -Id $servicePid -ErrorAction SilentlyContinue) { Write-Host ($item.name + ' ya está iniciado.'); continue }
    }
    $process = Start-Process -FilePath $item.exe -ArgumentList $item.args -WorkingDirectory $item.dir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir ($item.name + '.log')) -RedirectStandardError (Join-Path $runtimeDir ($item.name + '.error.log'))
    Set-Content -LiteralPath $pidPath -Value $process.Id
    if ($item.name -eq 'redis') {
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and -not (Test-NetConnection 127.0.0.1 -Port 6380 -WarningAction SilentlyContinue -InformationLevel Quiet)) { Start-Sleep -Milliseconds 500 }
    }
}
Write-Host 'Estudio: http://127.0.0.1:3001'
$adminPath = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'web/.env.local') -ErrorAction SilentlyContinue | Where-Object { $_ -like 'NEXT_PUBLIC_ADMIN_PATH=*' } | Select-Object -First 1) -replace '^NEXT_PUBLIC_ADMIN_PATH=', ''
Write-Host ('Administrador: http://127.0.0.1:3001/' + $adminPath + '/')
