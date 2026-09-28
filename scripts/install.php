<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require dirname(__DIR__) . '/backend/bootstrap.php';
require dirname(__DIR__) . '/backend/schema.php';
require dirname(__DIR__) . '/backend/workflow.php';
install_schema();
$password = getenv('MUSEDOUBLE_ADMIN_PASSWORD');
if (!query('SELECT id FROM users WHERE username=?', ['jhon'])->fetchColumn()) {
    if (!$password || strlen($password) < 10) throw new RuntimeException('Set MUSEDOUBLE_ADMIN_PASSWORD before installing the first administrator.');
    query("INSERT INTO users(username,name,password,role,can_generate,created_at) VALUES(?,?,?,'admin',1,?)", ['jhon', 'Jhon', password_hash($password, PASSWORD_DEFAULT), time()]);
}
$source = $argv[1] ?? null;
if ($source) foreach (['generate' => 'IMG_GEN_API.json', 'reference' => 'IMG_REFERENCE_GEN_API.json'] as $mode => $filename) { workflow_save($mode, file_get_contents(rtrim($source, '/\\') . '/' . $filename)); echo "Installed workflow: $mode\n"; }
echo 'Installation ready. Private data: ' . data_dir() . PHP_EOL;
