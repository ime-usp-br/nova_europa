<?php

namespace Tests\Unit\Framework;

use Illuminate\Auth\Middleware\Authenticate;
use Illuminate\Auth\Middleware\EnsureEmailIsVerified;
use Illuminate\Auth\Middleware\RedirectIfAuthenticated;
use Illuminate\Contracts\Http\Kernel as HttpKernelContract;
use Illuminate\Routing\Middleware\ValidateSignature;
use Tests\TestCase;

class MiddlewareAliasTest extends TestCase
{
    protected array $routeMiddleware;

    protected function setUp(): void
    {
        parent::setUp();
        $kernel = $this->app->make(HttpKernelContract::class);
        $this->routeMiddleware = $kernel->getRouteMiddleware();
    }

    public function test_auth_middleware_alias_is_available_and_correctly_mapped(): void
    {
        $this->assertArrayHasKey('auth', $this->routeMiddleware, "The 'auth' middleware alias is not registered.");
        $this->assertEquals(
            Authenticate::class,
            $this->routeMiddleware['auth'],
            "The 'auth' middleware alias does not map to the correct class."
        );
    }

    public function test_guest_middleware_alias_is_available_and_correctly_mapped(): void
    {
        $this->assertArrayHasKey('guest', $this->routeMiddleware, "The 'guest' middleware alias is not registered.");
        $this->assertEquals(
            RedirectIfAuthenticated::class,
            $this->routeMiddleware['guest'],
            "The 'guest' middleware alias does not map to the correct class."
        );
    }

    public function test_verified_middleware_alias_is_available_and_correctly_mapped(): void
    {
        $this->assertArrayHasKey('verified', $this->routeMiddleware, "The 'verified' middleware alias is not registered.");
        $this->assertEquals(
            EnsureEmailIsVerified::class,
            $this->routeMiddleware['verified'],
            "The 'verified' middleware alias does not map to the correct class."
        );
    }

    public function test_signed_middleware_alias_is_available_and_correctly_mapped(): void
    {
        $this->assertArrayHasKey('signed', $this->routeMiddleware, "The 'signed' middleware alias is not registered.");
        $this->assertEquals(
            ValidateSignature::class,
            $this->routeMiddleware['signed'],
            "The 'signed' middleware alias does not map to the correct class."
        );
    }
}
