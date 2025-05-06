<?php

use App\Exceptions\ReplicadoServiceException; // Import custom exception
use App\Models\User;
use App\Services\ReplicadoService;
use Illuminate\Auth\Events\Registered;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log; // Keep for potential direct logging if needed
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    public string $name = '';
    public string $email = '';
    public string $password = '';
    public string $password_confirmation = '';

    public bool $sou_da_usp = false;
    public string $codpes = '';

    /**
     * Automatically check "Sou da USP" if email ends with usp.br
     */
    public function updatedEmail(string $value): void
    {
        if (str_ends_with(strtolower($value), 'usp.br')) {
            $this->sou_da_usp = true;
        }
    }

    /**
     * Validation rules.
     */
    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'string', 'lowercase', 'email', 'max:255', 'unique:'.User::class],
            'sou_da_usp' => ['boolean'],
            'codpes' => [
                Rule::requiredIf($this->sou_da_usp),
                'nullable',
                'numeric',
                'digits_between:6,8',
                function (string $attribute, mixed $value, Closure $fail) {
                    if ($this->sou_da_usp && !empty($value)) {
                        $replicadoService = app(ReplicadoService::class);
                        try {
                            if (!$replicadoService->validarNuspEmail((int)$value, $this->email)) {
                                // AC4: Fail validation if Replicado validation returns false
                                $fail('validation.custom.codpes.replicado_validation_failed');
                            }
                        } catch (ReplicadoServiceException $e) { // Catch specific exception
                            // AC5: Handle Replicado service communication failure.
                            // Logging is already done within ReplicadoService.
                            // Return a generic validation error message to the user.
                            $fail('validation.custom.codpes.replicado_service_unavailable');
                        } catch (\Exception $e) {
                            // Catch any other unexpected exceptions from the service call
                            Log::error('Unexpected error during Replicado validation: '.$e->getMessage(), ['exception' => $e]);
                            $fail('validation.custom.codpes.replicado_service_unavailable'); // Still show a generic error to user
                        }
                    }
                },
            ],
            'password' => ['required', 'string', 'confirmed', Rules\Password::defaults()],
        ];
    }


    /**
     * Handle an incoming registration request.
     */
    public function register(): void
    {
        $validated = $this->validate();

        $userData = [
            'name' => $validated['name'],
            'email' => $validated['email'],
            'password' => Hash::make($validated['password']),
            'codpes' => ($this->sou_da_usp && isset($validated['codpes'])) ? $validated['codpes'] : null,
        ];

        $user = User::create($userData);

        // AC7: Assign 'usp_user' role if USP user and Replicado validation was successful.
        // The Replicado validation success is implied if we passed the validation rules for 'codpes'.
        if ($this->sou_da_usp && isset($validated['codpes'])) {
            $user->assignRole('usp_user');
        }
        // AC8 (external_user role assignment) will be implemented here later.

        event(new Registered($user));

        Auth::login($user);

        $this->redirect(route('dashboard', absolute: false), navigate: true);
    }
}; ?>

{{-- Wrap the interactive section with x-data --}}
{{-- No extra Alpine state needed if Livewire handles it --}}
<div x-data="{}">
    <div class="flex justify-center mb-4">
        <a href="/" wire:navigate>
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-padrao.png') }}" alt="Logo IME-USP" class="w-20 h-auto block dark:hidden" dusk="ime-logo-light">
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-branca.png') }}" alt="Logo IME-USP" class="w-20 h-auto hidden dark:block" dusk="ime-logo-dark">
        </a>
    </div>

    <form wire:submit="register">
        <!-- Name -->
        <div>
            <x-input-label for="name" :value="__('Name')" dusk="name-label" />
            <x-text-input wire:model="name" id="name" class="block mt-1 w-full" type="text" name="name" required autofocus autocomplete="name" dusk="name-input" />
            <x-input-error :messages="$errors->get('name')" class="mt-2" dusk="name-error" />
        </div>

        <!-- Email Address -->
        <div class="mt-4">
            <x-input-label for="email" :value="__('Email')" dusk="email-label" />
            {{-- Use wire:model.blur to update Livewire state less frequently --}}
            <x-text-input wire:model.blur="email" id="email" class="block mt-1 w-full" type="email" name="email" required autocomplete="username" dusk="email-input" />
            <x-input-error :messages="$errors->get('email')" class="mt-2" dusk="email-error" />
        </div>

        {{-- --- ADDED USP FIELDS --- --}}
        <!-- "Sou da USP" Checkbox -->
        <div class="block mt-4">
            <label for="sou_da_usp" class="inline-flex items-center">
                {{-- AC13: Uses existing dusk selector 'is-usp-user-checkbox' from previous commit --}}
                <input wire:model.live="sou_da_usp" {{-- Use .live for immediate conditional logic --}}
                       id="sou_da_usp"
                       type="checkbox"
                       {{-- Disable checkbox if email is already a USP email --}}
                       :disabled="$wire.email.toLowerCase().endsWith('usp.br')"
                       class="rounded dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-indigo-600 shadow-sm focus:ring-indigo-500 dark:focus:ring-indigo-600 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                       name="sou_da_usp"
                       dusk="is-usp-user-checkbox">
                <span class="ms-2 text-sm text-gray-600 dark:text-gray-400">{{ __('I\'m from USP') }}</span>
            </label>
             <x-input-error :messages="$errors->get('sou_da_usp')" class="mt-2" dusk="sou_da_usp-error" />
        </div>

        <!-- Número USP (codpes) Field - Conditional -->
        {{-- Show if email ends with @usp.br OR the checkbox is checked --}}
        {{-- AC13: Added dusk="codpes-container" to the surrounding div --}}
        <div x-show="$wire.email.toLowerCase().endsWith('usp.br') || $wire.sou_da_usp"
             x-cloak {{-- Prevent flash of unstyled content --}}
             x-transition
             class="mt-4"
             dusk="codpes-container">
            <x-input-label for="codpes" :value="__('USP Number (codpes)')" dusk="codpes-label" />
             {{-- AC13: Uses existing dusk selector 'codpes-input' from previous commit --}}
            <x-text-input wire:model="codpes" id="codpes" class="block mt-1 w-full"
                          type="text" {{-- Use text, validation handles numeric --}}
                          inputmode="numeric" {{-- Hint for mobile keyboards --}}
                          name="codpes"
                          autocomplete="off"
                          x-bind:required="$wire.email.toLowerCase().endsWith('usp.br') || $wire.sou_da_usp"
                          dusk="codpes-input" />
            <x-input-error :messages="$errors->get('codpes')" class="mt-2" dusk="codpes-error" />
        </div>
        {{-- --- END ADDED USP FIELDS --- --}}


        <!-- Password -->
        <div class="mt-4">
            <x-input-label for="password" :value="__('Password')" dusk="password-label" />
            <x-text-input wire:model="password" id="password" class="block mt-1 w-full"
                            type="password"
                            name="password"
                            required autocomplete="new-password" dusk="password-input" />
            <x-input-error :messages="$errors->get('password')" class="mt-2" dusk="password-error" />
        </div>

        <!-- Confirm Password -->
        <div class="mt-4">
            <x-input-label for="password_confirmation" :value="__('Confirm Password')" dusk="password-confirmation-label" />
            <x-text-input wire:model="password_confirmation" id="password_confirmation" class="block mt-1 w-full"
                            type="password"
                            name="password_confirmation" required autocomplete="new-password" dusk="password-confirmation-input" />
            <x-input-error :messages="$errors->get('password_confirmation')" class="mt-2" dusk="password-confirmation-error" />
        </div>

        <div class="flex items-center justify-end mt-4">
            <a class="underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800" href="{{ route('login.local') }}" wire:navigate dusk="already-registered-link">
                {{ __('Already registered?') }}
            </a>
            <x-primary-button class="ms-4" dusk="register-button">
                {{ __('Register') }}
            </x-primary-button>
        </div>
    </form>
</div>