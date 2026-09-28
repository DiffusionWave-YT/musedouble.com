<?php
declare(strict_types=1);
require dirname(__DIR__) . '/backend/bootstrap.php';
require dirname(__DIR__) . '/backend/workflow.php';
function check(bool $ok, string $message): void { if (!$ok) throw new RuntimeException($message); }
$model = ['character_prompt' => 'An adult studio model in a white shirt.', 'eye_prompt' => 'Brown eyes.', 'loras' => [['name' => 'zib/test.safetensors', 'strength' => 0.7]]];
$options = ['prompt' => 'Editorial portrait in a white shirt.', 'seed' => 123, 'batch' => 2, 'ratio' => ['label' => '4:5', 'width' => 1024, 'height' => 1280], 'strength' => 0.65];
foreach (['generate', 'reference'] as $mode) {
    $source = $argv[1] ?? dirname(__DIR__) . '/workflows';
    $filename = $mode === 'generate' ? 'IMG_GEN_API.json' : 'IMG_REFERENCE_GEN_API.json';
    $wf = json_decode(file_get_contents(rtrim($source, '/\\') . '/' . $filename), true, 512, JSON_THROW_ON_ERROR);
    workflow_validate($wf, $mode);
    $changed = workflow_build($wf, $mode, $model, $options, $mode === 'reference' ? 'uploaded.png' : null);
    $allowed = ['USER_PROMPT','CHARACTER_PROMPT','EYE_PROMPT','SELECT_CHARACTER','SEED','BATCH_SIZE','ASPECT_RATIOS','HORIZONTAL_RES','VERTICAL_RES','LOAD_IMAGE','REFERENCE_STRENGTH'];
    foreach ($wf as $id => $node) {
        if ($node !== $changed[$id]) check(in_array(node_title($node), $allowed, true), 'Unexpected node changed');
        if (!in_array(node_title($node), $allowed, true)) check($node === $changed[$id], 'Non-editable node mutated');
    }
    check(nodes_named($wf, 'FINAL_IMAGE') === nodes_named($changed, 'FINAL_IMAGE'), 'Output must remain untouched');
    $select = reset($changed); foreach (nodes_named($changed, 'SELECT_CHARACTER') as $node) { check($node['inputs']['lora_1_name'] === 'zib/test.safetensors', 'LoRA not applied'); check($node['inputs']['lora_2_name'] === 'None', 'Unused LoRA not cleared'); }
    // Remap every graph identifier and link; the title-based contract must survive.
    $map = []; foreach (array_keys($wf) as $i => $id) $map[(string)$id] = 'node-' . ($i + 500);
    $remapped = []; foreach ($wf as $id => $node) { foreach ($node['inputs'] as &$input) if (is_array($input) && count($input) === 2 && isset($map[(string)($input[0] ?? '')])) $input[0] = $map[(string)$input[0]]; unset($input); $remapped[$map[(string)$id]] = $node; }
    $rebuilt = workflow_build($remapped, $mode, $model, $options, 'uploaded.png');
    foreach (nodes_named($rebuilt, 'USER_PROMPT') as $node) check($node['inputs']['text'] === $options['prompt'], 'Remapped graph failed');
    check(nodes_named($remapped, 'FINAL_IMAGE') === nodes_named($rebuilt, 'FINAL_IMAGE'), 'Remapped output changed');
    $bad = $wf; unset($bad[array_key_first(nodes_named($bad, 'SEED'))]);
    try { workflow_validate($bad, $mode); throw new RuntimeException('Missing seed was accepted'); } catch (ApiError $e) {}
    $bad = $wf; $outputs = nodes_named($wf, 'FINAL_IMAGE'); $bad['duplicate-output'] = reset($outputs);
    try { workflow_validate($bad, $mode); throw new RuntimeException('Duplicate output was accepted'); } catch (ApiError $e) {}
    echo "$mode: contract, graph remapping, output immutability and LoRA tests passed.\n";
}
