<?php

namespace Tests\Feature;

// use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ExampleTest extends TestCase
{
    /**
     * A basic test example.
     */
    public function test_the_application_redirects_to_login_for_unauthenticated_users(): void
    {
        $response = $this->get('/');

        $response->assertRedirect(route('login.local'));
    }
}
