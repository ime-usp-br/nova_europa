<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Spatie\Permission\Models\Role;
use Spatie\Permission\PermissionRegistrar;

class RoleSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * Creates the default roles for the application.
     */
    public function run(): void
    {
        // Reset cached roles and permissions
        app()[PermissionRegistrar::class]->forgetCachedPermissions();

        // Create roles for local authentication
        Role::firstOrCreate(['name' => 'usp_user', 'guard_name' => 'web']);
        Role::firstOrCreate(['name' => 'external_user', 'guard_name' => 'web']);

        // Add other roles if needed, for example:
        // Role::firstOrCreate(['name' => 'admin', 'guard_name' => 'web']);
    }
}
