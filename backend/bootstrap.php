<?php
declare(strict_types=1);

function data_dir(): string {
    $dir = getenv('MUSEDOUBLE_DATA_DIR') ?: dirname(__DIR__, 2) . '/musedouble-private';
    if (!is_dir($dir) && !mkdir($dir, 0700, true) && !is_dir($dir)) throw new RuntimeException('Cannot create private storage.');
    $real = str_replace('\\', '/', realpath($dir));
    $web = str_replace('\\', '/', realpath(dirname(__DIR__)));
    if (strtolower($real) === strtolower($web) || strpos(strtolower($real), strtolower($web) . '/') === 0) throw new RuntimeException('Storage must be outside the public directory.');
    return $dir;
}
function db(): PDO {
    static $db;
    if (!$db) {
        $db = new PDO('sqlite:' . data_dir() . '/musedouble.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
        $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=10000; PRAGMA journal_mode=WAL;');
    }
    return $db;
}
function query(string $sql, array $params = []): PDOStatement { $s = db()->prepare($sql); $s->execute($params); return $s; }
function setting(string $name, $default = null) { $s = query('SELECT value FROM settings WHERE name=?', [$name])->fetchColumn(); return $s === false ? $default : json_decode($s, true, 512, JSON_THROW_ON_ERROR); }
function put_setting(string $name, $value): void { query('INSERT INTO settings(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value', [$name, json_encode($value, JSON_THROW_ON_ERROR)]); }
function fail(string $message, int $status = 400): void { throw new ApiError($message, $status); }
class ApiError extends RuntimeException {}
function json_response($data, int $status = 200): void { http_response_code($status); header('Content-Type: application/json; charset=utf-8'); echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR); exit; }
function request_data(): array {
    if (stripos($_SERVER['CONTENT_TYPE'] ?? '', 'application/json') === 0) {
        $raw = file_get_contents('php://input', false, null, 0, 1048577);
        if (strlen($raw) > 1048576) fail('Request is too large.', 413);
        try { $data = json_decode($raw, true, 64, JSON_THROW_ON_ERROR); } catch (JsonException $e) { fail('Invalid JSON.'); }
        if (!is_array($data)) fail('Expected a JSON object.');
        return $data;
    }
    return $_POST;
}
function begin_session(): void {
    header('X-Content-Type-Options: nosniff'); header('Referrer-Policy: same-origin'); header('Cache-Control: no-store');
    if (!is_dir(data_dir() . '/sessions')) mkdir(data_dir() . '/sessions', 0700, true);
    ini_set('session.use_strict_mode', '1'); ini_set('session.use_only_cookies', '1');
    session_save_path(data_dir() . '/sessions'); session_name('musedouble_session');
    session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off', 'httponly' => true, 'samesite' => 'Lax']);
    session_start();
    if (!isset($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32));
    if (isset($_SESSION['last_seen']) && time() - $_SESSION['last_seen'] > 28800) { unset($_SESSION['user_id']); session_regenerate_id(true); }
    $_SESSION['last_seen'] = time();
}
function csrf(): void { if (!hash_equals($_SESSION['csrf'] ?? '', $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) fail('Your session expired. Reload and try again.', 419); }
function current_user(): ?array {
    if (empty($_SESSION['user_id'])) return null;
    return query('SELECT id,username,email,name,role,can_generate,active FROM users WHERE id=? AND active=1', [$_SESSION['user_id']])->fetch() ?: null;
}
function require_user(bool $admin = false): array {
    $u = current_user(); if (!$u) fail('Please log in.', 401);
    if ($admin && $u['role'] !== 'admin') fail('Administrator access required.', 403);
    return $u;
}
function generation_user(): array { $u = require_user(); if (!$u['can_generate'] && $u['role'] !== 'admin') fail('Your studio access is pending administrator approval.', 403); return $u; }
function text_field(array $d, string $key, int $max, bool $required = false): string {
    if (isset($d[$key]) && !is_string($d[$key])) fail('Invalid ' . $key . '.');
    $s = trim($d[$key] ?? ''); if (mb_strlen($s) > $max || ($required && $s === '')) fail('Invalid ' . $key . '.'); return $s;
}
function int_field($v, int $min, int $max, string $label): int {
    if (filter_var($v, FILTER_VALIDATE_INT) === false || (int)$v < $min || (int)$v > $max) fail('Invalid ' . $label . '.'); return (int)$v;
}
function float_field($v, float $min, float $max, string $label): float { if (!is_numeric($v) || !is_finite((float)$v) || (float)$v < $min || (float)$v > $max) fail('Invalid ' . $label . '.'); return (float)$v; }
function private_write(string $path, string $content): void {
    $temp = $path . '.' . bin2hex(random_bytes(8)) . '.tmp';
    if (file_put_contents($temp, $content, LOCK_EX) === false) throw new RuntimeException('Cannot save private file.');
    chmod($temp, 0600); if (!rename($temp, $path)) { unlink($temp); throw new RuntimeException('Cannot commit private file.'); }
}
