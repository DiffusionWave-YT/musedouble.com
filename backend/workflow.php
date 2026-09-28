<?php
declare(strict_types=1);

function node_title(array $node): string { return trim((string)($node['_meta']['title'] ?? $node['title'] ?? '')); }
function nodes_named(array $wf, string $title): array { return array_filter($wf, static function ($n) use ($title) { return is_array($n) && node_title($n) === $title; }); }
function workflow_validate(array $wf, string $mode): array {
    if (!in_array($mode, ['generate', 'reference'], true)) fail('Unknown generation section.');
    if (!$wf || count($wf) > 2000) fail('Upload a ComfyUI workflow exported in API format.');
    foreach ($wf as $node) if (!is_array($node) || !isset($node['class_type'], $node['inputs']) || !is_string($node['class_type']) || !is_array($node['inputs'])) fail('Upload a ComfyUI workflow exported in API format.');
    $required = ['USER_PROMPT' => 'text', 'CHARACTER_PROMPT' => 'text', 'EYE_PROMPT' => 'text', 'SEED' => 'seed', 'BATCH_SIZE' => 'value'];
    if ($mode === 'reference') $required += ['LOAD_IMAGE' => 'image', 'REFERENCE_STRENGTH' => 'value'];
    elseif (nodes_named($wf, 'ASPECT_RATIOS')) $required['ASPECT_RATIOS'] = 'aspect_ratio';
    else $required += ['HORIZONTAL_RES' => 'value', 'VERTICAL_RES' => 'value'];
    foreach ($required as $title => $input) {
        $nodes = nodes_named($wf, $title); if (!$nodes) fail('Missing workflow node: ' . $title);
        foreach ($nodes as $node) if (!array_key_exists($input, $node['inputs'])) fail($title . ' must expose input ' . $input . '.');
    }
    $character = nodes_named($wf, 'SELECT_CHARACTER'); if (!$character) fail('Missing workflow node: SELECT_CHARACTER');
    foreach ($character as $node) for ($i = 1; $i <= 6; $i++) foreach (['name', 'strength'] as $field) if (!array_key_exists('lora_' . $i . '_' . $field, $node['inputs'])) fail('SELECT_CHARACTER must support six LoRA slots.');
    $outputs = nodes_named($wf, 'FINAL_IMAGE'); if (count($outputs) !== 1) fail('Exactly one FINAL_IMAGE output is required.');
    return ['mode' => $mode, 'nodes' => count($wf), 'titles' => array_keys($required), 'aspect_mode' => nodes_named($wf, 'ASPECT_RATIOS') ? 'label' : 'dimensions'];
}
function workflow_set(array &$wf, string $title, string $input, $value): void {
    if (strpos($title, 'FINAL_') === 0) throw new LogicException('Output nodes are read-only.');
    $matched = false;
    foreach ($wf as &$node) if (node_title($node) === $title) { if (!array_key_exists($input, $node['inputs'])) fail('Missing workflow input.'); $node['inputs'][$input] = $value; $matched = true; }
    unset($node); if (!$matched) fail('Missing workflow node: ' . $title);
}
function workflow_build(array $wf, string $mode, array $model, array $options, ?string $image = null): array {
    workflow_validate($wf, $mode); $outputsBefore = nodes_named($wf, 'FINAL_IMAGE');
    workflow_set($wf, 'USER_PROMPT', 'text', $options['prompt']);
    workflow_set($wf, 'CHARACTER_PROMPT', 'text', $model['character_prompt']);
    workflow_set($wf, 'EYE_PROMPT', 'text', $model['eye_prompt']);
    workflow_set($wf, 'SEED', 'seed', $options['seed']);
    workflow_set($wf, 'BATCH_SIZE', 'value', $options['batch']);
    $loras = is_string($model['loras']) ? json_decode($model['loras'], true, 32, JSON_THROW_ON_ERROR) : $model['loras'];
    for ($i = 1; $i <= 6; $i++) {
        workflow_set($wf, 'SELECT_CHARACTER', 'lora_' . $i . '_name', $loras[$i - 1]['name'] ?? 'None');
        workflow_set($wf, 'SELECT_CHARACTER', 'lora_' . $i . '_strength', $loras[$i - 1]['strength'] ?? 1);
    }
    // Keep internal connections and every other node exactly as uploaded.
    if ($mode === 'reference') { if (!$image) fail('A reference image is required.'); workflow_set($wf, 'LOAD_IMAGE', 'image', $image); workflow_set($wf, 'REFERENCE_STRENGTH', 'value', $options['strength']); }
    elseif (nodes_named($wf, 'ASPECT_RATIOS')) workflow_set($wf, 'ASPECT_RATIOS', 'aspect_ratio', $options['ratio']['label']);
    else { workflow_set($wf, 'HORIZONTAL_RES', 'value', $options['ratio']['width']); workflow_set($wf, 'VERTICAL_RES', 'value', $options['ratio']['height']); }
    if ($outputsBefore !== nodes_named($wf, 'FINAL_IMAGE')) throw new LogicException('Output node changed.');
    return $wf;
}
function workflow_load(string $mode): array {
    $row = query('SELECT * FROM workflows WHERE mode=?', [$mode])->fetch(); if (!$row) fail('This workflow has not been configured.', 409);
    $wf = json_decode(file_get_contents(data_dir() . '/workflows/' . $row['filename']), true, 512, JSON_THROW_ON_ERROR);
    workflow_validate($wf, $mode); return $wf;
}
function workflow_save(string $mode, string $raw): array {
    if (strlen($raw) > 2097152) fail('Workflow must be smaller than 2 MB.');
    try { $wf = json_decode($raw, true, 512, JSON_THROW_ON_ERROR); } catch (JsonException $e) { fail('Invalid workflow JSON.'); }
    if (!is_array($wf)) fail('Invalid workflow JSON.'); $meta = workflow_validate($wf, $mode);
    $filename = $mode . '-' . hash('sha256', $raw) . '.json';
    private_write(data_dir() . '/workflows/' . $filename, $raw);
    query('INSERT INTO workflows(mode,filename,updated_at,metadata) VALUES(?,?,?,?) ON CONFLICT(mode) DO UPDATE SET filename=excluded.filename,updated_at=excluded.updated_at,metadata=excluded.metadata', [$mode, $filename, time(), json_encode($meta)]);
    return $meta;
}
