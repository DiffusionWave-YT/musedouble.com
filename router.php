<?php
declare(strict_types=1);
// Local PHP server only. Production must use the documented Nginx allowlist.
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));
if (strpos($path, '..') !== false || strpos($path, "\0") !== false) { http_response_code(404); exit; }
if ($path === '/api.php') { require __DIR__ . '/api.php'; return true; }
if (in_array($path, ['/control-musedouble', '/control-musedouble/'], true)) { require __DIR__ . '/control-musedouble/index.php'; return true; }
if ($path === '/' || $path === '/index.php') { require __DIR__ . '/index.php'; return true; }
if ($path === '/index.html' || preg_match('~^/(?:[a-z0-9_-]+\.(?:css|js)|assets/[a-zA-Z0-9_./-]+\.(?:png|jpe?g|webp|svg))$~', $path)) {
    if (is_file(__DIR__ . $path)) return false;
}
http_response_code(404); echo 'Not found';
