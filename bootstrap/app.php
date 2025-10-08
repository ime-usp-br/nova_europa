<?php

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

return Application::configure(basePath: dirname(__DIR__))
    ->withEvents(discover: [
        __DIR__.'/../app/Listeners',
    ])
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
        then: function () {
            // Load test routes only in local environment
            if (app()->environment('local')) {
                Route::middleware('web')
                    ->group(base_path('routes/web-test.php'));
            }
        },
    )
    ->withMiddleware(function (Middleware $middleware) {
        $middleware->redirectGuestsTo(function (Request $request) {
            if ($request->expectsJson()) {
                return null;
            }

            return route('login.local');
        });

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
