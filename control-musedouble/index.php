<?php
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MuseDouble · Studio control</title><link rel="stylesheet" href="/admin.css"></head>
<body><div id="admin-app"><div class="loading">Opening your control room…</div></div><div id="admin-notice" role="status" aria-live="polite"></div><script src="/admin.js"></script></body></html>
