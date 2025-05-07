<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Auth\Notifications\ResetPassword;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Notification;
use Illuminate\Support\Facades\Password; // Importa o facade Password
use Livewire\Volt\Volt;
use Tests\TestCase;

class PasswordResetTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Testa se a tela de solicitação de link de redefinição de senha pode ser renderizada.
     * Verifica se o componente Volt 'pages.auth.forgot-password' está presente e o status HTTP é 200.
     * Relacionado ao AC1 da Issue #22.
     */
    public function test_reset_password_link_screen_can_be_rendered(): void
    {
        $response = $this->get('/forgot-password');

        $response
            ->assertSeeVolt('pages.auth.forgot-password')
            ->assertStatus(200);
    }

    /**
     * Testa se um link de redefinição de senha pode ser solicitado com sucesso.
     * Cria um usuário, simula o envio do formulário no componente Volt e verifica
     * se a notificação ResetPassword foi enviada para o usuário correto.
     * Relacionado ao AC8 da Issue #22.
     */
    public function test_reset_password_link_can_be_requested(): void
    {
        Notification::fake();

        $user = User::factory()->create();

        Volt::test('pages.auth.forgot-password')
            ->set('email', $user->email)
            ->call('sendPasswordResetLink');

        Notification::assertSentTo($user, ResetPassword::class);
    }

    /**
     * Testa se a tela de redefinição de senha (com o token) pode ser renderizada.
     * Simula a solicitação do link, captura o token da notificação e faz um GET
     * para a rota de reset, verificando a renderização do componente Volt correto.
     * Relacionado ao AC2 da Issue #22.
     */
    public function test_reset_password_screen_can_be_rendered(): void
    {
        Notification::fake();

        $user = User::factory()->create();

        Volt::test('pages.auth.forgot-password')
            ->set('email', $user->email)
            ->call('sendPasswordResetLink');

        // Verifica se a notificação foi enviada e extrai o token para usar na próxima etapa
        Notification::assertSentTo($user, ResetPassword::class, function ($notification) {
            $response = $this->get('/reset-password/'.$notification->token);

            $response
                ->assertSeeVolt('pages.auth.reset-password')
                ->assertStatus(200);

            // Retorna true para indicar que a asserção dentro da closure passou
            return true;
        });
    }

    /**
     * Testa se a senha pode ser redefinida com sucesso usando um token válido.
     * Simula todo o fluxo: cria usuário, solicita link, obtém token,
     * preenche o formulário de reset e verifica o resultado.
     * Garante que o usuário é redirecionado para a rota 'login.local' e
     * que uma mensagem de status é definida na sessão.
     * Relacionado ao AC9 da Issue #22.
     */
    public function test_password_can_be_reset_with_valid_token(): void
    {
        Notification::fake();

        $user = User::factory()->create();

        // 1. Solicita o link de reset (como nos testes anteriores)
        Volt::test('pages.auth.forgot-password')
            ->set('email', $user->email)
            ->call('sendPasswordResetLink');

        // 2. Captura o token e simula a submissão do formulário de reset
        Notification::assertSentTo($user, ResetPassword::class, function ($notification) use ($user) {
            $component = Volt::test('pages.auth.reset-password', ['token' => $notification->token])
                ->set('email', $user->email)
                ->set('password', 'Password123!') // Define a nova senha
                ->set('password_confirmation', 'Password123!'); // Confirma a nova senha

            // Chama a ação de resetar a senha
            $component->call('resetPassword');

            // *** INÍCIO DA MODIFICAÇÃO - AC9 Issue #22 ***
            // Verifica se a sessão flash 'status' foi definida com a mensagem correta
            // Obtém a mensagem traduzida de lang/xx/passwords.php['reset']
            $component->assertSessionHas('status', __(Password::PASSWORD_RESET));

            // Verifica se o redirecionamento ocorreu para a rota 'login.local'
            $component->assertRedirect(route('login.local'));
            // *** FIM DA MODIFICAÇÃO - AC9 Issue #22 ***

            // Verifica se não houve erros de validação durante o processo
            $component->assertHasNoErrors();

            // Retorna true para indicar que as asserções dentro da closure passaram
            return true;
        });
    }
}
