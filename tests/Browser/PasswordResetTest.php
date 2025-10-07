<?php

namespace Tests\Browser;

use App\Models\User;
use App\View\Components\AuthSessionStatus;
use App\View\Components\GuestLayout;
use App\View\Components\InputError;
use App\View\Components\InputLabel;
use App\View\Components\PrimaryButton;
use App\View\Components\TextInput;
use App\View\Components\usp\header as UspHeader;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\Password; // Import Password facade
use Laravel\Dusk\Browser;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\Test;
use Tests\DuskTestCase;

/**
 * Contém os testes de browser (Dusk) para a funcionalidade de Reset de Senha Local.
 * Garante que a interface dos formulários de solicitar link e redefinir senha
 * exibam os elementos visuais corretos (logos, campos, botões, links).
 * Relacionado ao AC10 da Issue #22.
 */
#[CoversClass(GuestLayout::class)]
#[CoversClass(UspHeader::class)]
#[CoversClass(InputLabel::class)]
#[CoversClass(TextInput::class)]
#[CoversClass(PrimaryButton::class)]
#[CoversClass(InputError::class)]
#[CoversClass(AuthSessionStatus::class)]
class PasswordResetTest extends DuskTestCase
{
    use DatabaseMigrations;

    /**
     * Verifica se os elementos visuais essenciais (logos, campo email, botão, link)
     * estão presentes e visíveis na tela de solicitar link de redefinição (`/forgot-password`).
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function forgot_password_screen_elements_are_present(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/forgot-password')
                ->assertVisible('@usp-logo')
                ->assertPresent('@ime-logo-light')
                ->assertPresent('@ime-logo-dark')
                ->assertVisible('@email-input')
                ->assertVisible('@send-reset-link-button')
                ->assertSeeIn('@send-reset-link-button', __('Email Password Reset Link'))
                ->assertVisible('@login-link')
                ->assertSeeIn('@login-link', __('Log in'));
        });
    }

    /**
     * Verifica se os elementos visuais essenciais (logos, campos, botão)
     * estão presentes e visíveis na tela de redefinição de senha (`/reset-password/{token}`).
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function reset_password_screen_elements_are_present(): void
    {
        // 1. Criar usuário e gerar token de reset
        $user = User::factory()->create();
        $token = Password::broker()->createToken($user);

        $this->browse(function (Browser $browser) use ($user, $token) {
            // 2. Navegar para a rota com o token e o email na querystring (conforme mount do componente)
            $browser->visit('/reset-password/'.$token.'?email='.$user->email)
                ->assertVisible('@usp-logo')
                ->assertPresent('@ime-logo-light')
                ->assertPresent('@ime-logo-dark')
                ->assertVisible('@email-input')
                ->assertValue('@email-input', $user->email) // Verifica se o email veio na URL
                ->assertVisible('@password-input')
                ->assertVisible('@password-confirmation-input')
                ->assertVisible('@reset-password-button')
                ->assertSeeIn('@reset-password-button', __('Reset Password'));
        });
    }
}
