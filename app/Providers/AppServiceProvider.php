<?php

namespace App\Providers;

use App\Models\Bloco;
use App\Models\BlocoDisciplina;
use App\Models\Permission;
use App\Models\Role;
use App\Models\Trilha;
use App\Models\TrilhaDisciplina;
use App\Models\TrilhaRegra;
use App\Models\User;
use App\Observers\PermissionObserver;
use App\Observers\RoleObserver;
use App\Policies\AuditPolicy;
use App\Policies\BlocoDisciplinaPolicy;
use App\Policies\BlocoPolicy;
use App\Policies\PermissionPolicy;
use App\Policies\RolePolicy;
use App\Policies\TrilhaDisciplinaPolicy;
use App\Policies\TrilhaPolicy;
use App\Policies\TrilhaRegraPolicy;
use App\Policies\UserPolicy;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\ServiceProvider;
use Illuminate\Validation\Rules\Password;
use OwenIt\Auditing\Models\Audit;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Force HTTPS URLs in production (when behind reverse proxy)
        if ($this->app->environment('production')) {
            \Illuminate\Support\Facades\URL::forceScheme('https');
        }

        Password::defaults(function () {
            $rule = Password::min(8);

            return $rule->letters()
                ->mixedCase()
                ->numbers()
                ->symbols();
        });

        // Register policies for Filament
        Gate::policy(User::class, UserPolicy::class);
        Gate::policy(Role::class, RolePolicy::class);
        Gate::policy(Permission::class, PermissionPolicy::class);
        Gate::policy(Audit::class, AuditPolicy::class);
        Gate::policy(Bloco::class, BlocoPolicy::class);
        Gate::policy(BlocoDisciplina::class, BlocoDisciplinaPolicy::class);
        Gate::policy(Trilha::class, TrilhaPolicy::class);
        Gate::policy(TrilhaRegra::class, TrilhaRegraPolicy::class);
        Gate::policy(TrilhaDisciplina::class, TrilhaDisciplinaPolicy::class);

        // Register observers for auditing Spatie models
        Role::observe(RoleObserver::class);
        Permission::observe(PermissionObserver::class);
    }
}
