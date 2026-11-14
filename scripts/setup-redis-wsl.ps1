# Instala Redis (solo el núcleo) dentro de WSL, sin sudo ni cambios del sistema.
# Descarga el código oficial, verifica su SHA-256 contra el repositorio oficial de
# hashes de Redis, compila en ~/musedouble-redis, genera una contraseña propia y
# escribe MUSE_REDIS_URL en .env sin mostrarla. Es idempotente.
param([string]$Distro = 'Ubuntu-22.04', [string]$Version = '8.10.3', [int]$Port = 6380)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$envFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Falta .env. Ejecuta primero scripts/setup_local.py.' }

$bash = @'
set -e
V="$1"; PORT="$2"
D="$HOME/musedouble-redis"
mkdir -p "$D/src" "$D/data" "$D/bin"
if [ ! -x "$D/bin/redis-server" ] || ! "$D/bin/redis-server" --version | grep -q "v=$V "; then
  cd "$D/src"
  curl -fsSL -o "redis-$V.tar.gz" "https://download.redis.io/releases/redis-$V.tar.gz"
  curl -fsSL -o hashes.txt https://raw.githubusercontent.com/redis/redis-hashes/master/README
  expected=$(grep -E "redis-$V\.tar\.gz" hashes.txt | awk '{print $4}')
  actual=$(sha256sum "redis-$V.tar.gz" | awk '{print $1}')
  if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then echo "HASH_MISMATCH" >&2; exit 1; fi
  rm -rf "redis-$V"; tar xzf "redis-$V.tar.gz"
  # Núcleo solamente: los módulos opcionales no se usan y exigen Python y Rust.
  make -C "redis-$V/src" -j4 > "$D/build-core.log" 2>&1
  cp "redis-$V/src/redis-server" "redis-$V/src/redis-cli" "$D/bin/"
fi
if [ ! -f "$D/redis.conf" ]; then
  PW=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  umask 077
  cat > "$D/redis.conf" <<CONF
bind 127.0.0.1 -::1
port $PORT
protected-mode yes
requirepass $PW
daemonize no
dir $D/data
pidfile $D/redis.pid
logfile $D/redis.log
appendonly yes
maxmemory 256mb
maxmemory-policy noeviction
CONF
fi
grep '^requirepass ' "$D/redis.conf" | cut -d' ' -f2
'@
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ('setup-redis-' + [guid]::NewGuid().ToString('N') + '.sh')
try {
    # Unix line endings: bash rejects CRLF.
    [System.IO.File]::WriteAllText($temp, ($bash -replace "`r`n", "`n"), (New-Object System.Text.UTF8Encoding($false)))
    $wslPath = (& wsl.exe -d $Distro -- wslpath -a ($temp -replace '\\', '/')).Trim()
    $secret = (& wsl.exe -d $Distro -- bash $wslPath $Version $Port | Select-Object -Last 1).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $secret) { throw 'No se pudo preparar Redis en WSL.' }
} finally { Remove-Item -LiteralPath $temp -ErrorAction SilentlyContinue }

$line = "MUSE_REDIS_URL=redis://:$secret@127.0.0.1:$Port/0"
$lines = @(Get-Content -LiteralPath $envFile | Where-Object { $_ -notmatch '^MUSE_REDIS_URL=' }) + $line
[System.IO.File]::WriteAllText($envFile, (($lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Redis $Version listo en WSL ($Distro), puerto $Port. MUSE_REDIS_URL guardado en .env."
