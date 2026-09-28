$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
php -d upload_max_filesize=22M -d post_max_size=25M -S 127.0.0.1:8087 router.php
