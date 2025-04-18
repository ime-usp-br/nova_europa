<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Livewire\Volt\Volt;
use Tests\TestCase;

class AuthenticationTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_screen_can_be_rendered(): void
    {
        // Teste original do Breeze para garantir que a rota local exista
        $response = $this->get('/login/local');

        $response
            ->assertOk()
            ->assertSeeVolt('pages.auth.login');
    }

    public function users_can_authenticate_using_the_local_login_screen(): void
    {
        // Este teste atende ao Critério de Aceite 3 da Issue #31
        $user = User::factory()->create();

        // Testa o componente Livewire/Volt diretamente
        $component = Volt::test('pages.auth.login')
            ->set('form.email', $user->email)
            ->set('form.password', 'password'); // Usa a senha padrão da factory

        // Chama a ação de login dentro do componente
        $component->call('login');

        // Verifica se não há erros de validação
        $component
            ->assertHasNoErrors()
            // Verifica se foi redirecionado para o dashboard
            ->assertRedirect(route('dashboard', absolute: false));

        // Verifica se o usuário está autenticado
        $this->assertAuthenticated();
    }
    
    public function users_can_not_authenticate_with_invalid_password_on_local_login(): void
    {
        $user = User::factory()->create();

        $component = Volt::test('pages.auth.login')
            ->set('form.email', $user->email)
            ->set('form.password', 'wrong-password');

        $component->call('login');

        // Verifica se há erro no campo de email (auth.failed é associado ao email geralmente)
        // E/OU no campo de senha, dependendo da implementação exata da validação no LoginForm
        $component->assertHasErrors(['form.email' => trans('auth.failed')])
            ->set('form.password', '') // Limpa para a próxima asserção
            ->call('login')
            ->assertHasErrors(['form.password' => 'required']); // Verifica erro de validação da senha também

        $component->assertNoRedirect(); // Garante que não houve redirecionamento

        $this->assertGuest(); // Garante que o usuário não foi autenticado
    }

    public function test_navigation_menu_can_be_rendered(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user);

        $response = $this->get('/dashboard');

        $response
            ->assertOk()
            ->assertSeeVolt('layout.navigation');
    }

    public function test_users_can_logout(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user);

        $component = Volt::test('layout.navigation');

        $component->call('logout');

        $component
            ->assertHasNoErrors()
            ->assertRedirect('/');

        $this->assertGuest();
    }
}