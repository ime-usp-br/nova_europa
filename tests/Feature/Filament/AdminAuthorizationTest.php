<?php

namespace Tests\Feature\Filament;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Spatie\Permission\Models\Role;
use Tests\TestCase;

class AdminAuthorizationTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        // Create roles
        Role::create(['name' => 'Admin', 'guard_name' => 'web']);
        Role::create(['name' => 'usp_user', 'guard_name' => 'web']);
    }

    public function test_admin_user_can_access_admin_panel(): void
    {
        $admin = User::factory()->create([
            'email' => 'admin@test.com',
        ]);
        $admin->assignRole('Admin');

        $this->actingAs($admin);

        $response = $this->get('/admin');

        $response->assertOk();
    }

    public function test_non_admin_user_cannot_access_admin_panel(): void
    {
        $user = User::factory()->create([
            'email' => 'user@test.com',
        ]);
        $user->assignRole('usp_user');

        $this->actingAs($user);

        $response = $this->get('/admin');

        $response->assertForbidden();
    }

    public function test_guest_is_redirected_to_login(): void
    {
        $response = $this->get('/admin');

        $response->assertRedirect('/admin/login');
    }

    public function test_user_with_admin_role_can_access_panel(): void
    {
        $admin = User::factory()->create();
        $admin->assignRole('Admin');

        $panel = filament()->getDefaultPanel();

        $this->assertTrue($admin->canAccessPanel($panel));
    }

    public function test_user_without_admin_role_cannot_access_panel(): void
    {
        $user = User::factory()->create();
        $user->assignRole('usp_user');

        $panel = filament()->getDefaultPanel();

        $this->assertFalse($user->canAccessPanel($panel));
    }
}
