<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use App\Services\ReplicadoService;
use Database\Seeders\RoleSeeder; // Import RoleSeeder
use Illuminate\Auth\Events\Registered; // Import Registered event
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Event; // Import Event facade
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rules\Password;
use Livewire\Volt\Volt;
use PHPUnit\Framework\Attributes\Test;
use Tests\Fakes\FakeReplicadoService;
use Tests\TestCase;

class RegistrationValidationTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Setup the test environment.
     *
     * Bind the fake service to the container for tests in this class.
     * Seed roles before each test.
     */
    protected function setUp(): void
    {
        parent::setUp();
        $this->instance(ReplicadoService::class, new FakeReplicadoService);
        $this->seed(RoleSeeder::class); // Seed roles
    }

    private function getUniqueEmail(bool $isUsp = false): string
    {
        $domain = $isUsp ? '@usp.br' : '@example.com';

        return 'test'.now()->timestamp.rand(100, 999).$domain;
    }

    private function getValidPassword(): string
    {
        return 'Password123!';
    }

    #[Test]
    public function valid_non_usp_user_can_register(): void
    {
        Event::fake(); // AC15: Fake events

        $password = $this->getValidPassword();
        $email = $this->getUniqueEmail();
        $name = 'Test Non USP';

        Volt::test('pages.auth.register')
            ->set('name', $name)
            ->set('email', $email)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('sou_da_usp', false)
            ->set('codpes', '') // Intentionally set as empty, should be ignored and result in null codpes
            ->call('register')
            ->assertHasNoErrors()
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated();
        $user = User::where('email', $email)->first();
        $this->assertNotNull($user);
        $this->assertEquals($name, $user->name);
        $this->assertNull($user->codpes);
        $this->assertTrue($user->hasRole('external_user'), "User should have 'external_user' role.");
        $this->assertFalse($user->hasRole('usp_user'), "User should not have 'usp_user' role.");

        // AC15: Assert Registered event was dispatched for the correct user
        Event::assertDispatched(Registered::class, function ($event) use ($user) {
            return $event->user->is($user);
        });
    }

    #[Test]
    public function valid_usp_user_with_codpes_and_successful_replicado_validation_can_register(): void
    {
        Event::fake(); // AC15: Fake events

        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567';
        $name = 'Test USP User Valid';

        $fakeReplicadoService = app(ReplicadoService::class);
        $fakeReplicadoService->shouldReturn(true);

        $component = Volt::test('pages.auth.register')
            ->set('name', $name)
            ->set('email', $uspEmail)
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', $codpes)
            ->call('register');

        $component->assertHasNoErrors()
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated();
        $user = User::where('email', $uspEmail)->first();
        $this->assertNotNull($user);
        $this->assertEquals($name, $user->name);
        $this->assertEquals($uspEmail, $user->email);
        $this->assertEquals($codpes, $user->codpes);

        // AC7: Assert user has 'usp_user' role
        $this->assertTrue($user->hasRole('usp_user'), "User should have 'usp_user' role.");
        $this->assertFalse($user->hasRole('external_user'), "User should not have 'external_user' role.");

        // AC15: Assert Registered event was dispatched for the correct user
        Event::assertDispatched(Registered::class, function ($event) use ($user) {
            return $event->user->is($user);
        });
    }

    #[Test]
    public function valid_non_usp_user_with_optional_codpes_can_register(): void
    {
        Event::fake(); // AC15: Fake events

        $password = $this->getValidPassword();
        $generatedEmail = $this->getUniqueEmail();
        $name = 'Test Non USP Optional Codpes';

        Volt::test('pages.auth.register')
            ->set('name', $name)
            ->set('email', $generatedEmail)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('sou_da_usp', false)
            ->set('codpes', '9876543') // This codpes should be ignored
            ->call('register')
            ->assertHasNoErrors()
            ->assertRedirect(route('dashboard', absolute: false));

        $this->assertAuthenticated();
        $user = User::where('email', $generatedEmail)->first();
        $this->assertNotNull($user);
        $this->assertEquals($name, $user->name);
        $this->assertNull($user->codpes); // Correctly null because sou_da_usp is false
        $this->assertTrue($user->hasRole('external_user'), "User should have 'external_user' role.");
        $this->assertFalse($user->hasRole('usp_user'), "User should not have 'usp_user' role.");

        // AC15: Assert Registered event was dispatched for the correct user
        Event::assertDispatched(Registered::class, function ($event) use ($user) {
            return $event->user->is($user);
        });
    }

    #[Test]
    public function registration_fails_when_name_is_missing(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('email', $this->getUniqueEmail())
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['name' => 'required']);
    }

    #[Test]
    public function registration_fails_when_email_is_missing(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'required']);
    }

    #[Test]
    public function registration_fails_when_password_is_missing(): void
    {
        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            ->call('register')
            ->assertHasErrors(['password' => 'required']);
    }

    #[Test]
    public function registration_fails_when_codpes_is_missing_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', '')
            ->call('register')
            ->assertHasErrors(['codpes' => 'required']);
    }

    #[Test]
    public function registration_fails_when_codpes_is_empty_string_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Empty Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', '')
            ->call('register')
            ->assertHasErrors(['codpes' => 'required']);
    }

    #[Test]
    public function registration_fails_for_invalid_email_format(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', 'invalid-email-format')
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'email']);
    }

    #[Test]
    public function registration_fails_when_email_is_already_taken(): void
    {
        $password = $this->getValidPassword();
        $existingUser = User::factory()->create();

        Volt::test('pages.auth.register')
            ->set('name', 'Another User')
            ->set('email', $existingUser->email)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->call('register')
            ->assertHasErrors(['email' => 'unique']);
    }

    #[Test]
    public function registration_fails_when_password_confirmation_mismatches(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            ->set('password', $password)
            ->set('password_confirmation', 'different-password')
            ->call('register')
            ->assertHasErrors(['password' => 'confirmed']);
    }

    #[Test]
    public function registration_fails_when_password_is_too_short(): void
    {
        Volt::test('pages.auth.register')
            ->set('name', 'Test Name')
            ->set('email', $this->getUniqueEmail())
            ->set('password', 'short')
            ->set('password_confirmation', 'short')
            ->call('register')
            ->assertHasErrors(['password']);
    }

    #[Test]
    public function registration_fails_when_codpes_is_not_numeric_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User NonNumeric')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', 'ABCDEFG')
            ->call('register')
            ->assertHasErrors(['codpes' => 'numeric']);
    }

    #[Test]
    public function registration_fails_when_codpes_is_too_short_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Short Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', '12345')
            ->call('register')
            ->assertHasErrors(['codpes' => 'digits_between']);
    }

    #[Test]
    public function registration_fails_when_codpes_is_too_long_for_usp_user(): void
    {
        $password = $this->getValidPassword();

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Long Codpes')
            ->set('email', $this->getUniqueEmail(true))
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', '123456789')
            ->call('register')
            ->assertHasErrors(['codpes' => 'digits_between']);
    }

    #[Test]
    public function registration_fails_when_replicado_validation_fails_for_usp_user(): void
    {
        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567';

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
            ->assertHasErrors(['codpes' => 'validation.custom.codpes.replicado_validation_failed']);

        $this->assertGuest();
        $this->assertDatabaseMissing('users', ['email' => $uspEmail]);
    }

    #[Test]
    public function registration_fails_when_replicado_service_is_unavailable_for_usp_user(): void
    {
        $password = $this->getValidPassword();
        $uspEmail = $this->getUniqueEmail(true);
        $codpes = '1234567';

        $fakeReplicadoService = app(ReplicadoService::class);
        $fakeReplicadoService->shouldFail(); // This configures FakeReplicadoService to throw ReplicadoServiceException

        Volt::test('pages.auth.register')
            ->set('name', 'Test USP User Replicado Error')
            ->set('email', $uspEmail)
            ->assertSet('sou_da_usp', true)
            ->set('password', $password)
            ->set('password_confirmation', $password)
            ->set('codpes', $codpes)
            ->call('register')
            ->assertHasErrors(['codpes' => 'validation.custom.codpes.replicado_service_unavailable']);

        $this->assertGuest();
        $this->assertDatabaseMissing('users', ['email' => $uspEmail]);
    }

    #[Test]
    public function default_password_rules_meet_requirements(): void
    {
        $rule = Password::defaults();

        $validatorShort = Validator::make(['password' => '1234567'], ['password' => $rule]);
        $this->assertTrue($validatorShort->fails());
        $this->assertArrayHasKey('password', $validatorShort->errors()->toArray());

        $validatorNoLetter = Validator::make(['password' => '12345678!'], ['password' => $rule]);
        $this->assertTrue($validatorNoLetter->fails(), 'Default password rule should require letters.');
        $this->assertArrayHasKey('password', $validatorNoLetter->errors()->toArray());

        $validatorNoNumber = Validator::make(['password' => 'Password!'], ['password' => $rule]);
        $this->assertTrue($validatorNoNumber->fails(), 'Default password rule should require numbers.');
        $this->assertArrayHasKey('password', $validatorNoNumber->errors()->toArray());

        $validatorNoSymbol = Validator::make(['password' => 'Password123'], ['password' => $rule]);
        $this->assertTrue($validatorNoSymbol->fails(), 'Default password rule should require symbols.');
        $this->assertArrayHasKey('password', $validatorNoSymbol->errors()->toArray());

        $validatorNoMixedCase = Validator::make(['password' => 'password123!'], ['password' => $rule]);
        $this->assertTrue($validatorNoMixedCase->fails(), 'Default password rule should require mixed case.');
        $this->assertArrayHasKey('password', $validatorNoMixedCase->errors()->toArray());

        $validatorValid = Validator::make(['password' => $this->getValidPassword()], ['password' => $rule]);
        $this->assertFalse($validatorValid->fails(), 'A valid password should pass default rules.');
    }
}
