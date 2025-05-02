<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Auth\Events\Verified;
use Illuminate\Auth\Notifications\VerifyEmail as VerifyEmailNotification;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Event;
use Illuminate\Support\Facades\Notification;
use Illuminate\Support\Facades\URL;
use Livewire\Livewire;
use Tests\TestCase;

class EmailVerificationTest extends TestCase
{
    use RefreshDatabase;

    public function test_email_verification_screen_can_be_rendered(): void
    {
        $user = User::factory()->unverified()->create();

        $response = $this->actingAs($user)->get('/verify-email');

        // Verifica se o componente Volt 'pages.auth.verify-email' está sendo renderizado
        $response
            ->assertSeeLivewire('pages.auth.verify-email') // Use assertSeeLivewire para componentes Livewire/Volt
            ->assertStatus(200);
    }

    public function test_email_can_be_verified(): void
    {
        $user = User::factory()->unverified()->create();

        Event::fake();

        $verificationUrl = URL::temporarySignedRoute(
            'verification.verify',
            now()->addMinutes(60),
            ['id' => $user->id, 'hash' => sha1($user->email)] // Correção: Usar o email real do usuário para o hash
        );

        $response = $this->actingAs($user)->get($verificationUrl);

        Event::assertDispatched(Verified::class);
        $this->assertTrue($user->fresh()->hasVerifiedEmail());
        $response->assertRedirect(route('dashboard', absolute: false).'?verified=1');
    }

    public function test_email_is_not_verified_with_invalid_hash(): void
    {
        $user = User::factory()->unverified()->create();

        $verificationUrl = URL::temporarySignedRoute(
            'verification.verify',
            now()->addMinutes(60),
            ['id' => $user->id, 'hash' => sha1('wrong-email')] // Hash inválido
        );

        $this->actingAs($user)->get($verificationUrl);

        $this->assertFalse($user->fresh()->hasVerifiedEmail());
    }

    // Teste para AC5 e AC6 (parte do reenvio e exibição de mensagem)
    public function test_verification_link_can_be_resent_and_status_is_shown(): void
    {
        $user = User::factory()->unverified()->create();

        // Mock para evitar envio real de email
        Notification::fake();

        // Monta o componente Livewire/Volt e atua como o usuário não verificado
        $response = Livewire::actingAs($user)
            ->test('pages.auth.verify-email') // Referencia o componente Volt pelo nome da view
            ->call('sendVerification'); // Chama a ação de reenviar

        // Verifica se a notificação de verificação foi enviada para o usuário correto
        Notification::assertSentTo(
            $user,
            VerifyEmailNotification::class
        );

        // AC6: Verifica se a mensagem de status (agora renderizada pelo componente) está presente na resposta do Livewire
        // A chave de tradução é resolvida para o idioma padrão (en) durante o teste.
        $response->assertSeeHtml(__('A new verification link has been sent to the email address you provided during registration.'));
    }

    // Novo teste de cenário: usuário já verificado tentando reenviar
    public function test_resend_redirects_if_already_verified(): void
    {
        // Cria um usuário já verificado (estado padrão da factory)
        $user = User::factory()->create();

        Notification::fake();

        Livewire::actingAs($user)
            ->test('pages.auth.verify-email')
            ->call('sendVerification')
            // Verifica se foi redirecionado para o dashboard
            // O assertRedirect do Livewire verifica o próximo request após a ação
            ->assertRedirect(route('dashboard', absolute: false));

        // Garante que nenhuma notificação foi enviada
        Notification::assertNothingSent();
        // Garante que a mensagem de status não foi definida
        $this->assertNull(session('status'));
    }
}
