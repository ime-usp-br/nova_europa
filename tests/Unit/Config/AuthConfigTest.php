<?php

namespace Tests\Unit\Config;

use Illuminate\Support\Facades\Config;
use Tests\TestCase;

class AuthConfigTest extends TestCase
{
    public function default_authentication_guard_is_web(): void
    {
        $this->assertEquals(
            'web',
            Config::get('auth.defaults.guard'),
            "The default authentication guard should be 'web'."
        );
    }

    public function web_guard_is_configured_correctly(): void
    {
        $this->assertEquals(
            'session',
            Config::get('auth.guards.web.driver'),
            "The 'web' guard driver should be 'session'."
        );

        $this->assertEquals(
            'users',
            Config::get('auth.guards.web.provider'),
            "The 'web' guard provider should be 'users'."
        );
    }
}
