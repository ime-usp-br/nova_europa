<?php

namespace Tests\Browser;

use App\Livewire\Forms\LoginForm;
use App\Models\User;
use App\View\Components\GuestLayout;
use App\View\Components\usp\header as UspHeader;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Laravel\Dusk\Browser;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\Test;
use Tests\DuskTestCase;

/**
 * Testes para a funcionalidade de Login usando Laravel Dusk.
 *
 * Corresponde à Issue #31.
 */
#[CoversClass(LoginForm::class)]
#[CoversClass(GuestLayout::class)]
#[CoversClass(UspHeader::class)]
class LoginTest extends DuskTestCase
{
    use DatabaseMigrations;

    /**
     * Testa se elementos essenciais da UI estão presentes na tela de login local.
     *
     * Este teste cobre o AC8 da Issue #31.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function local_login_screen_elements_are_present(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/login/local')
                ->assertVisible('@usp-logo')
                ->assertPresent('@ime-logo-light')
                ->assertPresent('@ime-logo-dark')
                ->assertVisible('@email-input')
                ->assertVisible('@password-input')
                ->assertVisible('@login-button')
                ->assertSeeIn('@login-button', strtoupper(__('Log in')))
                ->assertVisible('@senhaunica-login-button')
                ->assertSeeIn('@senhaunica-login-button', strtoupper(__('Login with Senha Única USP')))
                ->assertVisible('@forgot-password-link')
                ->assertSeeIn('@forgot-password-link', __('Forgot your password?'))
                ->assertVisible('@register-link')
                ->assertSeeIn('@register-link', __('Register'));
        });
    }

    /**
     * Testa se um usuário pode logar com sucesso usando o formulário de credenciais locais.
     *
     * Este teste cobre o AC9 da Issue #31.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function user_can_login_successfully_via_local_form(): void
    {
        $user = User::factory()->create([
            'email' => 'dusk-user@example.com',
        ]);

        $this->browse(function (Browser $browser) use ($user) {
            $browser->logout();
            $browser->visit('/login/local')
                ->waitFor('@email-input')
                ->type('@email-input', $user->email)
                ->waitFor('@password-input')
                ->type('@password-input', 'password')
                ->waitFor('@login-button')
                ->click('@login-button')
                ->waitForLocation('/dashboard')
                ->assertPathIs('/dashboard');
        });
    }

    /**
     * Testa se uma mensagem de erro de autenticação é exibida com credenciais inválidas.
     *
     * Cobre o AC10 da Issue #31.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function user_cannot_login_with_invalid_credentials(): void
    {
        $user = User::factory()->create([
            'email' => 'dusk-invalid@example.com',
        ]);

        $this->browse(function (Browser $browser) use ($user) {
            $browser->logout();
            $browser->visit('/login/local')
                ->waitFor('@email-input')
                ->type('@email-input', $user->email)
                ->waitFor('@password-input')
                ->type('@password-input', 'wrong-password')
                ->waitFor('@login-button')
                ->click('@login-button')
                ->pause(100)
                ->assertPathIs('/login/local')
                ->waitFor('@email-error')
                ->assertVisible('@email-error')
                ->assertSeeIn('@email-error', trans('auth.failed'));
        });
    }

    /**
     * Testa se clicar no botão Senha Única inicia um redirecionamento.
     *
     * Cobre o AC11 da Issue #31.
     * Verifica que o navegador não está mais na página de login local após o clique,
     * implicando que um redirecionamento foi iniciado (seja para /login ou para o provedor externo).
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function clicking_senhaunica_button_initiates_redirect(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/login/local')
                ->waitFor('@senhaunica-login-button')
                ->click('@senhaunica-login-button')
                ->pause(100)
                ->assertPathIsNot('/login/local');
        });
    }

    /**
     * Testa se clicar no link "Esqueceu sua senha?" redireciona corretamente.
     *
     * Cobre o AC12 da Issue #31.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function clicking_forgot_password_link_redirects_correctly(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/login/local')
                ->waitFor('@forgot-password-link')
                ->click('@forgot-password-link')
                ->waitForLocation('/forgot-password')
                ->assertPathIs('/forgot-password');
        });
    }
}
