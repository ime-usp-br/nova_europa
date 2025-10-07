<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Spatie\Permission\Models\Role;
use Spatie\Permission\PermissionRegistrar;

/**
 * Seeder para criar o usuário administrador inicial do Filament.
 */
class FilamentAdminSeeder extends Seeder
{
    /**
     * Executa o seeder para o banco de dados.
     *
     * Cria um usuário administrador padrão com a role 'Admin' para acesso ao painel Filament.
     */
    public function run(): void
    {
        // Reset cached roles and permissions
        app()[PermissionRegistrar::class]->forgetCachedPermissions();

        // Ensure Admin role exists
        $adminRole = Role::firstOrCreate(['name' => 'Admin', 'guard_name' => 'web']);

        // Create admin user
        $admin = User::firstOrCreate(
            ['email' => 'admin@usp.br'],
            [
                'name' => 'Administrador',
                'email_verified_at' => now(),
                'password' => bcrypt('password'), // Change this in production!
            ]
        );

        // Assign Admin role
        if (! $admin->hasRole('Admin')) {
            $admin->assignRole($adminRole);
        }

        $this->command->info('Admin user created: admin@usp.br / password');
    }
}
