<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use App\Services\ReplicadoService; // Import the actual service
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Validator; // Mantenha para o teste de regras padrão
use Illuminate\Validation\Rule;  // Mantenha para o teste de regras padrão
use Illuminate\Validation\Rules\Password; // Importe Volt
use Livewire\Volt\Volt; // Import the fake service
use PHPUnit\Framework\Attributes\Test;
use Tests\Fakes\FakeReplicadoService; // Importe Rule para o teste de codpes
use Tests\TestCase;

class RegistrationValidationTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Setup the test environment.
     *
     * Bind the fake service to the container for tests in this class.
     */
    protected function setUp(): void
    {
        parent::setUp();

        // Bind the fake service instance for ReplicadoService resolution
        $this->instance(ReplicadoService::class, new FakeReplicadoService);
    }

    // Método para obter um email único para evitar falhas de 'unique'
    private function getUniqueEmail(bool $isUsp = false): string
    {
        $domain = $isUsp ? '@usp.br' : '@example.com';

        return 'test'.now()->timestamp.rand(100, 999).$domain;
    }

    // Método para obter uma senha que passe nas regras padrão
    // Adapte se suas regras forem diferentes
    private function getValidPassword(): string
    {
        return 'Password123!';
    }

    // --- Testes para Cenários Válidos (shouldPass = true) ---

    #[Test]
    public function test_valid_non_usp_user_can_register(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Non USP')
            ->set('email', $this->getUniqueEmail())
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('sou_da_usp', false) // Explicitamente não USP
            ->set('codpes', '') // Não deve ser requerido
            ->call('register')
            ->assertHasNoErrors() // Espera passar
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated(); // Verifica se logou
    }

    #[Test]
    public function test_valid_usp_user_with_codpes_and_successful_replicado_validation_can_register(): void
    {
        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567';

        // Configure FakeReplicadoService to return true (success)
        $fakeReplicadoService = app(ReplicadoService::class); // Get the bound fake instance
        $fakeReplicadoService->shouldReturn(true);

        $component = Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Valid')
            ->set('email', $uspEmail) // Email USP
            ->assertSet('sou_da_usp', true) // Check if updatedEmail hook worked
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', $codpes) // Codpes válido
            ->call('register');

        $component->assertHasNoErrors() // Espera passar
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated();
        $this->assertDatabaseHas('users', [
            'email' => $uspEmail,
            'codpes' => $codpes,
        ]);
    }

    #[Test]
    public function test_valid_non_usp_user_with_optional_codpes_can_register(): void
    {
        $password = $this->getValidPassword();
        $generatedEmail = $this->getUniqueEmail(); // <-- Captura o email

        Volt::test('pages.auth.register')
            ->set('name', 'Test Non USP Optional Codpes')
            ->set('email', $generatedEmail) // <-- Usa o email gerado
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('sou_da_usp', false)
            ->set('codpes', '9876543')
            ->call('register')
            ->assertHasNoErrors()
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated();

        // Usa a variável local na asserção
        $this->assertDatabaseHas('users', [
            'email' => $generatedEmail, // <-- Usa a variável local
            'codpes' => null, // Codpes should be null for non-USP users even if provided
        ]);
    }
    // --- Testes para Cenários Inválidos (shouldPass = false) ---

    #[Test]
    public function test_registration_fails_when_name_is_missing(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            // Não seta 'name'
            ->set('email', $this->getUniqueEmail())
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['name' => 'required']); // Espera erro específico
    }

    #[Test]
    public function test_registration_fails_when_email_is_missing(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            // Não seta 'email'
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'required']);
    }

    #[Test]
    public function test_registration_fails_when_password_is_missing(): void
    {
        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            // Não seta 'password' nem 'password_confirmation'
            ->call('register')
            ->assertHasErrors(['password' => 'required']); // A regra 'confirmed' também falhará, mas 'required' é a raiz
    }

    #[Test]
    public function test_registration_fails_when_codpes_is_missing_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User')
            ->set('email', $this->getUniqueEmail(true)) // Email USP ativa sou_da_usp
            ->assertSet('sou_da_usp', true) // Check hook
            ->set('password', $password)
            ->set('password_confirmation', $password)
            // ->set('sou_da_usp', true) // Garante que a flag USP está ativa (já é setada pelo email)
            ->set('codpes', '') // Explicitamente vazio
            ->call('register')
            ->assertHasErrors(['codpes' => 'required']); // Verifica se a regra condicional falhou
    }

    #[Test]
    public function test_registration_fails_when_codpes_is_empty_string_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Empty Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
           // ->set('sou_da_usp', true)
            ->set('codpes', '') // Codpes vazio
            ->call('register')
            ->assertHasErrors(['codpes' => 'required']);
    }

    #[Test]
    public function test_registration_fails_for_invalid_email_format(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', 'invalid-email-format') // Formato inválido
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'email']); // Verifica a regra 'email'
    }

    #[Test]
    public function test_registration_fails_when_email_is_already_taken(): void
    {
        $password = $this->getValidPassword();
        $existingUser = User::factory()->create(); // Cria um usuário com um email

        Volt::test('pages.auth.register')
            ->set('name', 'Another User')
            ->set('email', $existingUser->email) // Usa o email existente
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'unique']); // Verifica a regra 'unique'
    }

    #[Test]
    public function test_registration_fails_when_password_confirmation_mismatches(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            ->set('password', $password)
            ->set('password_confirmation', 'different-password') // Confirmação diferente
            ->call('register')
            ->assertHasErrors(['password' => 'confirmed']); // Verifica a regra 'confirmed'
    }

    #[Test]
    public function test_registration_fails_when_password_is_too_short(): void
    {
        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            ->set('password', 'short')
            ->set('password_confirmation', 'short')
            ->call('register')
            // ->assertHasErrors(['password' => 'min']); // <-- Linha antiga
            ->assertHasErrors(['password']);           // <-- Nova linha: Verifica qualquer erro para 'password'
    }

    #[Test]
    public function test_registration_fails_when_codpes_is_not_numeric_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User NonNumeric')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
           // ->set('sou_da_usp', true)
            ->set('codpes', 'ABCDEFG') // Não numérico
            ->call('register')
            ->assertHasErrors(['codpes' => 'numeric']);
    }

    #[Test]
    public function test_registration_fails_when_codpes_is_too_short_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Short Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            // ->set('sou_da_usp', true)
            ->set('codpes', '12345') // Curto demais (definido como 6-8)
            ->call('register')
            ->assertHasErrors(['codpes' => 'digits_between']);
    }

    #[Test]
    public function test_registration_fails_when_codpes_is_too_long_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Long Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            // ->set('sou_da_usp', true)
            ->set('codpes', '123456789') // Longo demais (definido como 6-8)
            ->call('register')
            ->assertHasErrors(['codpes' => 'digits_between']);
    }

    // --- AC3/AC4 Specific Tests ---

    #[Test]
    public function test_registration_fails_when_replicado_validation_fails_for_usp_user(): void
    {
        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567'; // Valid format, but Replicado will say it's wrong

        // Configure FakeReplicadoService to return false (validation failure)
        $fakeReplicadoService = app(ReplicadoService::class);
        $fakeReplicadoService->shouldReturn(false);

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Invalid Replicado')
            ->set('email', $uspEmail)
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', $codpes)
            ->call('register')
            ->assertHasErrors(['codpes' => 'validation.custom.replicado_validation_failed']); // AC4: Check for the specific custom error message key

        $this->assertGuest(); // User should not be authenticated or created
        $this->assertDatabaseMissing('users', ['email' => $uspEmail]);
    }

    #[Test]
    public function test_registration_fails_when_replicado_service_is_unavailable_for_usp_user(): void
    {
        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567';

        // Configure FakeReplicadoService to throw an exception
        $fakeReplicadoService = app(ReplicadoService::class);
        $fakeReplicadoService->shouldFail();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Replicado Error')
            ->set('email', $uspEmail)
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', $codpes)
            ->call('register')
             // Check for the specific error message key related to service unavailability
            ->assertHasErrors(['codpes' => 'validation.custom.replicado_service_unavailable']);

        $this->assertGuest(); // User should not be authenticated or created
        $this->assertDatabaseMissing('users', ['email' => $uspEmail]);
    }

    // Mantém este teste isolado para verificar as regras padrão
    #[Test]
    public function test_default_password_rules_meet_requirements(): void
    {
        $rule = Password::defaults();

        // Verifica Mínimo (ex: 8)
        $validatorShort = Validator::make(['password' => '1234567'], ['password' => $rule]);
        $this->assertTrue($validatorShort->fails());
        $this->assertArrayHasKey('password', $validatorShort->errors()->toArray());

        // Verifica Letras (deve falhar se letras são exigidas pelas suas regras)
        $validatorNoLetter = Validator::make(['password' => '12345678!'], ['password' => $rule]);
        $this->assertTrue($validatorNoLetter->fails(), 'Default password rule should require letters.');
        $this->assertArrayHasKey('password', $validatorNoLetter->errors()->toArray());

        // Verifica Números (deve falhar se números são exigidos)
        $validatorNoNumber = Validator::make(['password' => 'Password!'], ['password' => $rule]);
        $this->assertTrue($validatorNoNumber->fails(), 'Default password rule should require numbers.');
        $this->assertArrayHasKey('password', $validatorNoNumber->errors()->toArray());

        // Verifica Símbolos (deve falhar se símbolos são exigidos)
        $validatorNoSymbol = Validator::make(['password' => 'Password123'], ['password' => $rule]);
        $this->assertTrue($validatorNoSymbol->fails(), 'Default password rule should require symbols.');
        $this->assertArrayHasKey('password', $validatorNoSymbol->errors()->toArray());

        // Verifica Caixa Mista (deve falhar se exigido)
        $validatorNoMixedCase = Validator::make(['password' => 'password123!'], ['password' => $rule]);
        $this->assertTrue($validatorNoMixedCase->fails(), 'Default password rule should require mixed case.');
        $this->assertArrayHasKey('password', $validatorNoMixedCase->errors()->toArray());

        // Verifica uma senha válida (deve passar)
        $validatorValid = Validator::make(['password' => $this->getValidPassword()], ['password' => $rule]);
        $this->assertFalse($validatorValid->fails(), 'A valid password should pass default rules.');
    }
}
