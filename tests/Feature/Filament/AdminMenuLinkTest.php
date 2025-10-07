<?php

namespace Tests\Feature\Filament;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Spatie\Permission\Models\Role;
use Tests\TestCase;

class AdminMenuLinkTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        // Create roles
        Role::create(['name' => 'Admin', 'guard_name' => 'web']);
        Role::create(['name' => 'usp_user', 'guard_name' => 'web']);
    }

    public function test_admin_user_sees_admin_panel_link_in_menu(): void
    {
        $admin = User::factory()->create();
        $admin->assignRole('Admin');

        $this->actingAs($admin);

        $response = $this->get('/dashboard');

        $response->assertOk();
        $response->assertSee('Painel Admin');
    }

    public function test_non_admin_user_does_not_see_admin_panel_link(): void
    {
        $user = User::factory()->create();
        $user->assignRole('usp_user');

        $this->actingAs($user);

        $response = $this->get('/dashboard');

        $response->assertOk();
        $response->assertDontSee('Painel Admin');
    }

    public function test_admin_can_navigate_to_panel_from_menu_link(): void
    {
        $admin = User::factory()->create();
        $admin->assignRole('Admin');

        $this->actingAs($admin);

        // Verify link exists in dashboard
        $dashboardResponse = $this->get('/dashboard');
        $dashboardResponse->assertSee('Painel Admin');

        // Verify admin can access panel
        $panelResponse = $this->get('/admin');
        $panelResponse->assertOk();
    }
}
