<?php

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request; // Added for Request type hint

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        // Removed specific api and apiPrefix as they are typically added by `php artisan install:api`
        // and AC3 does not require API routes. If they were pre-existing, they would remain.
        // Assuming a base setup or that API routes are handled elsewhere if needed.
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware) {
        // This is where other global middleware or aliases might be configured.
        // AC3 of Issue #26: Ensure unauthenticated users are redirected to the local login route.
        $middleware->redirectGuestsTo(function (Request $request) {
            // If the request expects JSON, return null to let the default JSON response handler work.
            // Otherwise, redirect to the local login route.
            if ($request->expectsJson()) {
                return null;
            }

            return route('login.local');
        });

        // AC5 of Issue #26: Ensure authenticated users trying to access guest routes are redirected to dashboard.
        $middleware->redirectUsersTo(fn (Request $request) => route('dashboard'));

        // Example of other common middleware configurations that might exist:
        // $middleware->validateCsrfTokens(except: [
        //     'stripe/*',
        // ]);
        // $middleware->alias([
        //     'admin' => \App\Http\Middleware\EnsureUserIsAdmin::class,
        // ]);
    })
    ->withExceptions(function (Exceptions $exceptions) {
        // This is where custom exception handling might be configured.
    })->create();
