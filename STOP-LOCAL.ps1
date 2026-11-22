$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$runtimeDir = Join-Path $projectRoot 'storage/runtime'
$redisPidPath = Join-Path $runtimeDir 'redis.pid'
if (Test-Path -LiteralPath $redisPidPath) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & wsl.exe -d Ubuntu-22.04 --exec bash -lc 'D=$HOME/musedouble-redis; REDISCLI_AUTH=$(grep ^requirepass $D/redis.conf | cut -d" " -f2) $D/bin/redis-cli -p 6380 shutdown' 2>&1 | Out-Null
    $ErrorActionPreference = $previousPreference
    $redisProc = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int](Get-Content -LiteralPath $redisPidPath)) -ErrorAction SilentlyContinue
    if ($redisProc -and $redisProc.CommandLine -like '*musedouble-redis*') { Stop-Process -Id $redisProc.ProcessId -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $redisPidPath
    Write-Host 'redis detenido.'
}
foreach ($name in @('api','objects','worker','web')) {
    $pidPath = Join-Path $runtimeDir ($name + '.pid')
    if (-not (Test-Path -LiteralPath $pidPath)) { continue }
    $servicePid = [int](Get-Content -LiteralPath $pidPath)
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$servicePid"
    if ($proc -and (($proc.ExecutablePath -and $proc.ExecutablePath.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase)) -or ($name -eq 'web' -and $proc.CommandLine -like '*node_modules/next/dist/bin/next *--hostname 127.0.0.1 --port 3001*'))) {
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$servicePid" | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $servicePid -ErrorAction SilentlyContinue
        Write-Host ($name + ' detenido.')
    } elseif ($proc) {
        throw ('El PID registrado para '+$name+' pertenece a otro proceso. No se detuvo.')
    }
    Remove-Item -LiteralPath $pidPath
}
Write-Host 'PostgreSQL local permanece activo; ningún servicio instalado del sistema fue detenido.'
