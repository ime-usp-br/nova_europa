<?php

return [
    'host' => env('REPLICADO_HOST'),
    'port' => env('REPLICADO_PORT'),
    'database' => env('REPLICADO_DATABASE', 'replicado'),
    'username' => env('REPLICADO_USERNAME'),
    'password' => env('REPLICADO_PASSWORD'),
    'codundclg' => env('REPLICADO_CODUNDCLG'),
    'pathlog' => env('REPLICADO_PATHLOG', '/tmp/replicado.log'),
    'sybase' => env('REPLICADO_SYBASE', true),
    'usar_cache' => env('REPLICADO_USAR_CACHE', false),
    'debug' => env('REPLICADO_DEBUG', false),
    'debug_level' => env('REPLICADO_DEBUG_LEVEL', 0),
];
