<?php
declare(strict_types=1);
require __DIR__ . '/backend/bootstrap.php';
require __DIR__ . '/backend/workflow.php';
require __DIR__ . '/backend/comfy.php';
ini_set('display_errors', '0');
try {
    begin_session(); $action = $_GET['action'] ?? 'session';
    $getActions = ['session', 'catalog', 'jobs', 'job', 'media', 'admin_state'];
    if (!in_array($action, $getActions, true)) { if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail('Use POST.', 405); csrf(); }
    elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') fail('Use GET.', 405);
    $d = $_SERVER['REQUEST_METHOD'] === 'POST' ? request_data() : [];
    if ($action === 'session') json_response(['user' => current_user(), 'csrf' => $_SESSION['csrf']]);
    if ($action === 'login' || $action === 'register') {
        $ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown'; $identity = strtolower(text_field($d, $action === 'login' ? 'identity' : 'email', 254, true));
        query('DELETE FROM attempts WHERE created_at<?', [time() - 900]);
        if ((int)query('SELECT COUNT(*) FROM attempts WHERE ip=? OR identity=?', [$ip, $identity])->fetchColumn() >= 10) fail('Too many attempts. Try again in 15 minutes.', 429);
        query('INSERT INTO attempts(ip,identity,created_at) VALUES(?,?,?)', [$ip, $identity, time()]);
        $password = $d['password'] ?? ''; if (!is_string($password) || strlen($password) > 200) fail('Invalid password.');
        if ($action === 'register') {
            $name = text_field($d, 'name', 80, true);
            if (!filter_var($identity, FILTER_VALIDATE_EMAIL) || strlen($password) < 10) fail('Use a valid email and a password of at least 10 characters.');
            if (query('SELECT id FROM users WHERE email=? OR username=?', [$identity, $identity])->fetch()) fail('This account cannot be registered. Try logging in.', 409);
            query('INSERT INTO users(username,email,name,password,created_at) VALUES(?,?,?,?,?)', [$identity, $identity, $name, password_hash($password, PASSWORD_DEFAULT), time()]);
            $id = (int)db()->lastInsertId();
        } else {
            $row = query('SELECT * FROM users WHERE username=? OR email=?', [$identity, $identity])->fetch();
            $valid = password_verify($password, $row['password'] ?? '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.');
            if (!$row || !$valid || !$row['active']) fail('Incorrect login or password.', 401);
            if (!empty($d['admin']) && $row['role'] !== 'admin') fail('Administrator access required.', 403);
            $id = (int)$row['id']; query('DELETE FROM attempts WHERE identity=?', [$identity]);
        }
        session_regenerate_id(true); $_SESSION['user_id'] = $id; $_SESSION['csrf'] = bin2hex(random_bytes(32));
        json_response(['user' => current_user(), 'csrf' => $_SESSION['csrf']]);
    }
    if ($action === 'logout') { $_SESSION = []; session_regenerate_id(true); $_SESSION['csrf'] = bin2hex(random_bytes(32)); json_response(['csrf' => $_SESSION['csrf']]); }
    if ($action === 'catalog') {
        $u = require_user(); $settings = setting('generation');
        json_response(['models' => query('SELECT id,name FROM models WHERE active=1 ORDER BY name')->fetchAll(), 'settings' => $settings, 'can_generate' => (bool)$u['can_generate'] || $u['role'] === 'admin', 'configured' => (bool)setting('comfy', [])]);
    }
    if ($action === 'generate') {
        $u = generation_user(); $mode = text_field($d, 'mode', 20, true); $wf = workflow_load($mode);
        $server = setting('comfy'); if (!$server || empty($server['url'])) fail('ComfyUI is not configured.', 409);
        $model = query('SELECT * FROM models WHERE id=? AND active=1', [text_field($d, 'model_id', 80, true)])->fetch(); if (!$model) fail('Select an available model.');
        $settings = setting('generation'); $ratioLabel = text_field($d, 'ratio', 12); $ratio = null;
        foreach ($settings['ratios'] as $r) if ($r['label'] === $ratioLabel) $ratio = $r;
        if ($mode === 'generate' && !$ratio) fail('Choose an available aspect ratio.');
        $seed = $d['seed'] ?? ''; $seed = $seed === '' ? random_int(0, 2147483647) : int_field($seed, 0, 9007199254740991, 'seed');
        $options = ['prompt' => text_field($d, 'prompt', 8000, true), 'seed' => $seed, 'batch' => int_field($d['batch'] ?? 1, 1, $settings['max_batch'], 'quantity'), 'ratio' => $ratio, 'strength' => float_field($d['strength'] ?? 0.6, 0, 1, 'reference strength')];
        $requestKey = text_field($d, 'request_key', 100, true); if (!preg_match('/^[a-zA-Z0-9_-]{12,100}$/', $requestKey)) fail('Invalid request identifier.');
        // Claim the request before contacting the GPU, so retries never enqueue it twice.
        db()->exec('BEGIN IMMEDIATE');
        try {
            $existing = query('SELECT * FROM jobs WHERE user_id=? AND request_key=?', [$u['id'], $requestKey])->fetch();
            if ($existing) { db()->exec('COMMIT'); json_response(['job' => job_public($existing)]); }
            if ((int)query("SELECT COUNT(*) FROM jobs WHERE user_id=? AND status IN ('submitting','queued','running') AND created_at>?", [$u['id'], time() - 86400])->fetchColumn() >= 2) fail('Wait for your current generations to finish.', 429);
            $id = bin2hex(random_bytes(16));
            query("INSERT INTO jobs(id,user_id,mode,model_id,model_name,status,server,options,request_key,created_at) VALUES(?,?,?,?,?,'submitting',?,?,?,?)", [$id, $u['id'], $mode, $model['id'], $model['name'], json_encode($server), json_encode($options), $requestKey, time()]);
            db()->exec('COMMIT');
        } catch (Throwable $e) { db()->exec('ROLLBACK'); throw $e; }
        session_write_close();
        try {
            $image = $mode === 'reference' ? reference_upload($server) : null;
            $wf = workflow_build($wf, $mode, $model, $options, $image);
            private_write(data_dir() . '/jobs/' . $id . '.json', json_encode($wf, JSON_THROW_ON_ERROR));
            $answer = comfy_request($server, '/prompt', ['prompt' => (object)$wf, 'client_id' => 'musedouble-' . $id]);
            if (empty($answer['prompt_id'])) fail('ComfyUI did not return a job identifier.', 502);
            query("UPDATE jobs SET status='queued',prompt_id=? WHERE id=?", [$answer['prompt_id'], $id]);
        } catch (Throwable $e) {
            $message = $e instanceof ApiError ? $e->getMessage() : 'Could not submit the generation.';
            query("UPDATE jobs SET status='failed',error=? WHERE id=?", [$message, $id]); throw $e;
        }
        json_response(['job' => job_public(query('SELECT * FROM jobs WHERE id=?', [$id])->fetch())], 202);
    }
    if ($action === 'jobs' || $action === 'job') {
        $u = require_user(); session_write_close();
        if ($action === 'jobs') { $rows = query('SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 60', [$u['id']])->fetchAll(); json_response(['jobs' => array_map('job_public', $rows)]); }
        $job = query('SELECT * FROM jobs WHERE id=? AND user_id=?', [$_GET['id'] ?? '', $u['id']])->fetch(); if (!$job) fail('Job not found.', 404);
        json_response(['job' => job_public(poll_job($job))]);
    }
    if ($action === 'media') {
        $u = require_user(); $m = query('SELECT * FROM media WHERE id=? AND user_id=?', [$_GET['id'] ?? '', $u['id']])->fetch(); if (!$m) fail('Image not found.', 404);
        session_write_close(); $path = data_dir() . '/results/' . $m['filename'];
        if (!is_file($path)) fail('Image not found.', 404);
        header('Content-Type: ' . $m['mime']); header('Content-Length: ' . filesize($path)); header('Content-Disposition: ' . (isset($_GET['download']) ? 'attachment' : 'inline') . '; filename="' . $m['filename'] . '"'); readfile($path); exit;
    }
    if (strpos($action, 'admin_') === 0) {
        $admin = require_user(true);
        if ($action === 'admin_state') {
            $server = setting('comfy', []);
            $models = query('SELECT * FROM models ORDER BY name')->fetchAll(); foreach ($models as &$m) $m['loras'] = json_decode($m['loras'], true); unset($m);
            json_response(['server' => ['url' => $server['url'] ?? '', 'token_set' => !empty($server['token'])], 'settings' => setting('generation'), 'models' => $models, 'workflows' => query('SELECT mode,metadata,updated_at FROM workflows')->fetchAll(), 'users' => query('SELECT id,username,email,name,role,can_generate,active FROM users ORDER BY id')->fetchAll(), 'jobs' => query('SELECT id,mode,model_name,status,error,created_at FROM jobs ORDER BY created_at DESC LIMIT 20')->fetchAll()]);
        }
        if ($action === 'admin_server') {
            $server = setting('comfy', []); $server['url'] = comfy_url(text_field($d, 'url', 1000, true));
            if (!empty($d['clear_token'])) $server['token'] = '';
            elseif (!empty($d['token'])) { $token = text_field($d, 'token', 4096); if (preg_match('/[\r\n]/', $token)) fail('Invalid API token.'); $server['token'] = $token; }
            put_setting('comfy', $server); json_response(['ok' => true]);
        }
        if ($action === 'admin_test_server' || $action === 'admin_loras') {
            $server = setting('comfy'); if (!$server) fail('Save a server first.'); session_write_close();
            if ($action === 'admin_test_server') { comfy_request($server, '/system_stats'); json_response(['ok' => true, 'message' => 'ComfyUI is connected.']); }
            $info = comfy_request($server, '/object_info/DW_LoRAStackApplySimple'); $names = [];
            foreach ($info['DW_LoRAStackApplySimple']['input'] ?? [] as $inputs) if (isset($inputs['lora_1_name'][0]) && is_array($inputs['lora_1_name'][0])) $names = $inputs['lora_1_name'][0];
            json_response(['loras' => $names]);
        }
        if ($action === 'admin_workflow') {
            $f = $_FILES['workflow'] ?? null; if (!$f || $f['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name']) || $f['size'] > 2097152) fail('Upload an API JSON workflow, up to 2 MB.');
            $meta = workflow_save(text_field($d, 'mode', 20, true), file_get_contents($f['tmp_name'])); json_response(['ok' => true, 'metadata' => $meta]);
        }
        if ($action === 'admin_model') {
            $id = text_field($d, 'id', 80); if ($id === '') $id = bin2hex(random_bytes(8));
            if (!preg_match('/^[a-z0-9_-]{1,80}$/i', $id)) fail('Invalid model identifier.');
            $name = text_field($d, 'name', 100, true); $character = text_field($d, 'character_prompt', 8000); $eye = text_field($d, 'eye_prompt', 2000);
            $loras = $d['loras'] ?? []; if (!is_array($loras) || count($loras) > 6) fail('Use up to six LoRAs.');
            $validated = [];
            foreach ($loras as $lora) {
                if (!is_array($lora)) fail('Invalid LoRA.'); $l = text_field($lora, 'name', 500, true);
                if (!preg_match('/\.safetensors$/i', $l) || strpos($l, '..') !== false || preg_match('/[\x00-\x1f]/', $l)) fail('Use a relative .safetensors LoRA filename.');
                $validated[] = ['name' => str_replace('\\', '/', $l), 'strength' => float_field($lora['strength'] ?? 1, -2, 2, 'LoRA strength')];
            }
            query('INSERT INTO models(id,name,character_prompt,eye_prompt,loras,active) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,character_prompt=excluded.character_prompt,eye_prompt=excluded.eye_prompt,loras=excluded.loras,active=excluded.active', [$id, $name, $character, $eye, json_encode($validated), !empty($d['active']) ? 1 : 0]);
            json_response(['ok' => true, 'id' => $id]);
        }
        if ($action === 'admin_settings') {
            $max = int_field($d['max_batch'] ?? 2, 1, 2, 'maximum batch'); $ratios = $d['ratios'] ?? []; if (!is_array($ratios) || count($ratios) < 1 || count($ratios) > 12) fail('Add between one and twelve aspect ratios.');
            $valid = []; $labels = [];
            foreach ($ratios as $r) { $label = text_field($r, 'label', 12, true); if (!preg_match('/^[1-9][0-9]?:[1-9][0-9]?$/', $label) || in_array($label, $labels, true)) fail('Aspect ratios must be unique (for example 4:5).'); $labels[] = $label; $w = int_field($r['width'], 256, 4096, 'width'); $h = int_field($r['height'], 256, 4096, 'height'); if ($w % 8 || $h % 8) fail('Dimensions must be multiples of eight.'); $valid[] = ['label' => $label, 'width' => $w, 'height' => $h]; }
            put_setting('generation', ['max_batch' => $max, 'ratios' => $valid]); json_response(['ok' => true]);
        }
        if ($action === 'admin_user') {
            $id = int_field($d['id'] ?? 0, 1, PHP_INT_MAX, 'user'); $target = query('SELECT role FROM users WHERE id=?', [$id])->fetch(); if (!$target || $target['role'] === 'admin') fail('Only member access can be changed here.');
            query('UPDATE users SET can_generate=?,active=? WHERE id=?', [!empty($d['can_generate']) ? 1 : 0, !empty($d['active']) ? 1 : 0, $id]); json_response(['ok' => true]);
        }
        if ($action === 'admin_password') {
            $p = $d['password'] ?? ''; if (!is_string($p) || strlen($p) < 12 || strlen($p) > 200) fail('Use a password of 12–200 characters.');
            $hash = query('SELECT password FROM users WHERE id=?', [$admin['id']])->fetchColumn(); if (!password_verify($d['current_password'] ?? '', $hash)) fail('Current password is incorrect.', 403);
            query('UPDATE users SET password=? WHERE id=?', [password_hash($p, PASSWORD_DEFAULT), $admin['id']]); session_regenerate_id(true); json_response(['ok' => true]);
        }
    }
    fail('Unknown endpoint.', 404);
} catch (ApiError $e) { json_response(['error' => $e->getMessage()], $e->getCode() ?: 400); }
catch (Throwable $e) { error_log('MuseDouble backend failure: ' . get_class($e)); json_response(['error' => 'The server could not complete this request. Check the private installation and server logs.'], 500); }
