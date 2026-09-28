<?php
declare(strict_types=1);

// Public shell. Authenticated data is loaded through api.php.
header('Content-Type: text/html; charset=UTF-8');
readfile(__DIR__ . '/index.html');
