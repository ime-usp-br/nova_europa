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
 * Contém os testes de browser (Dusk) para a funcionalidade de Login.
 * Garante que a interface de login local e seus elementos funcionem corretamente,
 * incluindo a interação com os botões de login local e Senha Única,
 * e os links de navegação para registro e recuperação de senha.
 */
#[CoversClass(LoginForm::class)]
#[CoversClass(GuestLayout::class)]
#[CoversClass(UspHeader::class)]
class LoginTest extends DuskTestCase
{
    use DatabaseMigrations;

    /**
     * Verifica se os elementos visuais essenciais (logos, campos, botões, links)
     * estão presentes e visíveis na tela de login local (`/login/local`).
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
                ->assertSeeIn('@login-button', __('Log in'))
                ->assertVisible('@senhaunica-login-button')
                ->assertSeeIn('@senhaunica-login-button', __('Login with Senha Única USP'))
                ->assertVisible('@forgot-password-link')
                ->assertSeeIn('@forgot-password-link', __('Forgot your password?'))
                ->assertVisible('@register-link')
                ->assertSeeIn('@register-link', __('Register'));
        });
    }

    /**
     * Garante que um usuário registrado possa se autenticar com sucesso
     * utilizando o formulário de login local (email e senha) e seja
     * redirecionado para o painel de controle (`/dashboard`).
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
     * Verifica se, ao tentar fazer login com credenciais locais inválidas
     * (email correto, senha incorreta), o usuário permanece na página de login
     * e uma mensagem de erro de autenticação (`auth.failed`) é exibida.
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
     * Assegura que clicar no botão "Login com Senha Única USP" inicie um
     * processo de redirecionamento, removendo o usuário da página de login local.
     * O teste não verifica a URL exata de destino, apenas que a navegação ocorreu.
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
                ->assertPathIsNot('/login/local'); // Ensures a redirect happened
        });
    }

    /**
     * Verifica se clicar no link "Forgot your password?" na tela de login local
     * redireciona o usuário corretamente para a página de recuperação de senha (`/forgot-password`).
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

    /**
     * Garante que clicar no link "Register" na tela de login local redireciona
     * o usuário para a página de registro (`/register`) e que os elementos
     * esperados (campos de nome, email, senha, botão de registro, link "Já registrado?")
     * estejam visíveis nesta nova página.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function clicking_register_link_redirects_correctly_and_shows_register_elements(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/login/local')
                ->waitFor('@register-link')
                ->click('@register-link')
                ->waitForLocation('/register')
                ->assertPathIs('/register')
                ->assertVisible('@name-input')
                ->assertVisible('@email-input')
                ->assertVisible('@password-input')
                ->assertVisible('@password-confirmation-input')
                ->assertVisible('@register-button')
                ->assertSeeIn('@register-button', __('Register'))
                ->assertVisible('@already-registered-link')
                ->assertSeeIn('@already-registered-link', __('Already registered?'));
        });
    }
}
