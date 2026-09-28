<?php
declare(strict_types=1);

function comfy_url(string $url): string {
    $url = rtrim(trim($url), '/'); $p = parse_url($url);
    if (!$p || !in_array($p['scheme'] ?? '', ['http', 'https'], true) || !preg_match('/^[a-z0-9._-]+$/i', $p['host'] ?? '') || isset($p['user']) || isset($p['pass']) || isset($p['query']) || isset($p['fragment']) || preg_match('/[\s\x00-\x1f]/', $url)) fail('Enter a valid ComfyUI HTTP or HTTPS URL.');
    return $url;
}
function comfy_request(array $server, string $path, $body = null, bool $binary = false, int $limit = 33554432) {
    $ch = curl_init(comfy_url($server['url']) . $path); $headers = [];
    if (!empty($server['token'])) $headers[] = 'Authorization: Bearer ' . $server['token'];
    if (is_array($body) && !isset($body['image'])) { $body = json_encode($body, JSON_THROW_ON_ERROR); $headers[] = 'Content-Type: application/json'; }
    $result = '';
    curl_setopt_array($ch, [CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => 90, CURLOPT_FOLLOWLOCATION => false, CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2, CURLOPT_HTTPHEADER => $headers, CURLOPT_WRITEFUNCTION => static function ($ch, $chunk) use (&$result, $limit) { if (strlen($result) + strlen($chunk) > $limit) return 0; $result .= $chunk; return strlen($chunk); }]);
    if ($body !== null) { curl_setopt($ch, CURLOPT_POST, true); curl_setopt($ch, CURLOPT_POSTFIELDS, $body); }
    $ok = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_RESPONSE_CODE); $error = curl_errno($ch); curl_close($ch);
    if ($ok === false) fail('Could not reach ComfyUI (connection error ' . $error . '). Check the server URL and certificate.', 502);
    if ($code < 200 || $code >= 300) {
        $detail = json_decode($result, true); $type = $detail['error']['type'] ?? '';
        fail('ComfyUI returned HTTP ' . $code . ($type ? ' (' . preg_replace('/[^a-zA-Z0-9_ -]/', '', (string)$type) . ')' : '') . '. Check the workflow and installed models.', 502);
    }
    if ($binary) return $result;
    try { $json = json_decode($result, true, 512, JSON_THROW_ON_ERROR); } catch (JsonException $e) { fail('The configured server did not return a ComfyUI response.', 502); }
    if (!is_array($json)) fail('Invalid ComfyUI response.', 502); return $json;
}
function reference_upload(array $server): string {
    $f = $_FILES['reference'] ?? null;
    if (!$f || ($f['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name'])) fail('Upload a reference image.');
    if ($f['size'] > 20 * 1024 * 1024 || $f['size'] < 1) fail('Reference images must be at most 20 MB.');
    $mime = (new finfo(FILEINFO_MIME_TYPE))->file($f['tmp_name']); $extensions = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'];
    $size = @getimagesize($f['tmp_name']);
    if (!isset($extensions[$mime]) || !$size || $size[0] * $size[1] > 40000000) fail('Use a valid JPG, PNG or WebP image, up to 40 megapixels.');
    $name = 'musedouble-' . bin2hex(random_bytes(16)) . '.' . $extensions[$mime];
    $result = comfy_request($server, '/upload/image', ['image' => new CURLFile($f['tmp_name'], $mime, $name), 'type' => 'input', 'overwrite' => 'false']);
    if (empty($result['name'])) fail('ComfyUI did not accept the reference image.', 502);
    return (!empty($result['subfolder']) ? trim($result['subfolder'], '/') . '/' : '') . $result['name'];
}
function poll_job(array $job): array {
    if (!in_array($job['status'], ['queued', 'running'], true) || !$job['prompt_id']) return $job;
    $history = comfy_request(json_decode($job['server'], true), '/history/' . rawurlencode($job['prompt_id']));
    $entry = $history[$job['prompt_id']] ?? null;
    if (!$entry) {
        if (time() - $job['created_at'] > 86400) { query("UPDATE jobs SET status='failed',error=? WHERE id=?", ['The job was not found after 24 hours. Check ComfyUI history.', $job['id']]); }
        return query('SELECT * FROM jobs WHERE id=?', [$job['id']])->fetch();
    }
    if (($entry['status']['status_str'] ?? '') === 'error') {
        query("UPDATE jobs SET status='failed',error=? WHERE id=?", ['ComfyUI could not execute this workflow. Check the GPU server logs and installed nodes/models.', $job['id']]);
    } elseif (!empty($entry['status']['completed'])) {
        $wf = json_decode(file_get_contents(data_dir() . '/jobs/' . $job['id'] . '.json'), true);
        $outputId = array_key_first(nodes_named($wf, 'FINAL_IMAGE'));
        $images = $entry['outputs'][(string)$outputId]['images'] ?? [];
        if (!$images) { query("UPDATE jobs SET status='failed',error=? WHERE id=?", ['The workflow completed without images in FINAL_IMAGE.', $job['id']]); }
        else {
            $lock = fopen(data_dir() . '/jobs/' . $job['id'] . '.lock', 'c');
            if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) { if ($lock) fclose($lock); return $job; }
            try {
                foreach ($images as $i => $image) {
                    if (query('SELECT id FROM media WHERE job_id=? AND output_index=?', [$job['id'], $i])->fetchColumn()) continue;
                    if (empty($image['filename']) || !in_array($image['type'] ?? 'output', ['output', 'temp'], true)) fail('Invalid ComfyUI output.', 502);
                    $bytes = comfy_request(json_decode($job['server'], true), '/view?' . http_build_query(['filename' => $image['filename'], 'subfolder' => $image['subfolder'] ?? '', 'type' => $image['type'] ?? 'output']), null, true);
                    $mime = (new finfo(FILEINFO_MIME_TYPE))->buffer($bytes); $ext = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'][$mime] ?? null;
                    if (!$ext) fail('ComfyUI returned an unsupported image.', 502);
                    $id = bin2hex(random_bytes(16)); $name = $id . '.' . $ext;
                    private_write(data_dir() . '/results/' . $name, $bytes);
                    query('INSERT INTO media(id,job_id,user_id,output_index,filename,mime,created_at) VALUES(?,?,?,?,?,?,?)', [$id, $job['id'], $job['user_id'], $i, $name, $mime, time()]);
                }
                query("UPDATE jobs SET status='completed',error=NULL WHERE id=?", [$job['id']]);
            } finally { flock($lock, LOCK_UN); fclose($lock); }
        }
    }
    return query('SELECT * FROM jobs WHERE id=?', [$job['id']])->fetch();
}
function job_public(array $job): array {
    $media = query('SELECT id FROM media WHERE job_id=? ORDER BY output_index', [$job['id']])->fetchAll();
    return ['id' => $job['id'], 'mode' => $job['mode'], 'status' => $job['status'], 'error' => $job['error'], 'model_name' => $job['model_name'], 'created_at' => $job['created_at'], 'options' => json_decode($job['options'], true), 'images' => array_map(static function ($m) { return ['id' => $m['id'], 'url' => '/api.php?action=media&id=' . $m['id']]; }, $media)];
}
