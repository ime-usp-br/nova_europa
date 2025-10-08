<?php

namespace App\Providers;

use App\Services\ReplicadoService;
use Illuminate\Support\ServiceProvider;

/**
 * Service provider for ReplicadoService.
 *
 * Registers the ReplicadoService as a singleton in the container,
 * allowing for dependency injection throughout the application.
 */
class ReplicadoServiceProvider extends ServiceProvider
{
    /**
     * Register services.
     */
    public function register(): void
    {
        $this->app->singleton(ReplicadoService::class, function ($app) {
            return new ReplicadoService;
        });
    }

    /**
     * Bootstrap services.
     */
    public function boot(): void
    {
        //
    }
}
