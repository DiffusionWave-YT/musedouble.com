<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require dirname(__DIR__) . '/backend/bootstrap.php';
$file = $argv[1] ?? ''; $limit = isset($argv[2]) ? (int)$argv[2] : PHP_INT_MAX;
$data = json_decode(file_get_contents($file), true, 512, JSON_THROW_ON_ERROR); $count = 0;
foreach ($data['presets'] ?? $data as $row) {
    if ($count >= $limit) break;
    $name = trim($row['name'] ?? ''); if ($name === '') continue;
    $loras = $row['loras'] ?? [['lora' => $row['lora'] ?? '', 'strength' => $row['strength'] ?? 1]];
    $items = [];
    foreach (array_slice($loras, 0, 6) as $l) { $path = str_replace('\\', '/', $l['lora'] ?? $l['name'] ?? ''); if ($path === '') continue; if (strpos($path, '/') === false) $path = 'zib/' . $path; $items[] = ['name' => $path, 'strength' => (float)($l['strength'] ?? 1)]; }
    $id = 'fansla-' . substr(hash('sha256', $name), 0, 16);
    query('INSERT OR IGNORE INTO models(id,name,character_prompt,eye_prompt,loras,active) VALUES(?,?,?,?,?,1)', [$id, $name, $row['characterPrompt'] ?? $row['character_prompt'] ?? '', $row['eyePrompt'] ?? $row['eye_prompt'] ?? '', json_encode($items)]); $count++;
}
echo "Imported $count model profiles.\n";
