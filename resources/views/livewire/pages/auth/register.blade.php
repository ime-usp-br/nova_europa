<?php

use App\Models\User;
use Illuminate\Auth\Events\Registered;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\Rules;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    public string $name = '';
    public string $email = '';
    public string $password = '';
    public string $password_confirmation = '';
    public bool $isUspUser = false; // Property to track the checkbox state

    /**
     * Handle an incoming registration request.
     */
    public function register(): void
    {
        $validated = $this->validate([
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'string', 'lowercase', 'email', 'max:255', 'unique:'.User::class],
            'password' => ['required', 'string', 'confirmed', Rules\Password::defaults()],
            // Add validation for 'codpes' here later based on 'isUspUser' or email domain
        ]);

        $validated['password'] = Hash::make($validated['password']);

        // Add logic to handle 'codpes' field saving later

        event(new Registered($user = User::create($validated)));

        Auth::login($user);

        $this->redirect(route('dashboard', absolute: false), navigate: true);
    }
}; ?>

<div>
    <form wire:submit="register">
        <!-- Name -->
        <div>
            <x-input-label for="name" :value="__('Name')" />
            <x-text-input wire:model="name" id="name" class="block mt-1 w-full" type="text" name="name" required autofocus autocomplete="name" dusk="name-input" />
            <x-input-error :messages="$errors->get('name')" class="mt-2" />
        </div>

        <!-- Email Address -->
        <div class="mt-4">
            <x-input-label for="email" :value="__('Email')" />
            <x-text-input wire:model="email" id="email" class="block mt-1 w-full" type="email" name="email" required autocomplete="username" dusk="email-input" />
            <x-input-error :messages="$errors->get('email')" class="mt-2" />
        </div>

        <!-- I'm from USP Checkbox -->
        <div class="block mt-4">
            <label for="is_usp_user" class="inline-flex items-center">
                <input id="is_usp_user" type="checkbox" class="rounded dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-indigo-600 shadow-sm focus:ring-indigo-500 dark:focus:ring-indigo-600 dark:focus:ring-offset-gray-800" name="is_usp_user" wire:model.live="isUspUser" dusk="is-usp-user-checkbox">
                <span class="ms-2 text-sm text-gray-600 dark:text-gray-400">{{ __('I\'m from USP') }}</span>
            </label>
            <x-input-error :messages="$errors->get('isUspUser')" class="mt-2" />
        </div>

        <!-- Número USP (codpes) - To be added and made conditional later -->
        {{--
        <div class="mt-4" x-data="{ showCodpes: @entangle('isUspUser').live || $wire.email.endsWith('@usp.br') }" x-show="showCodpes" x-cloak>
             <x-input-label for="codpes" :value="__('Número USP (codpes)')" />
             <x-text-input wire:model="codpes" id="codpes" class="block mt-1 w-full" type="text" name="codpes" :required="$wire.isUspUser || str_ends_with($wire.email, '@usp.br')" autocomplete="off" dusk="codpes-input" />
             <x-input-error :messages="$errors->get('codpes')" class="mt-2" />
        </div>
        --}}


        <!-- Password -->
        <div class="mt-4">
            <x-input-label for="password" :value="__('Password')" />

            <x-text-input wire:model="password" id="password" class="block mt-1 w-full"
                            type="password"
                            name="password"
                            required autocomplete="new-password" dusk="password-input" />

            <x-input-error :messages="$errors->get('password')" class="mt-2" />
        </div>

        <!-- Confirm Password -->
        <div class="mt-4">
            <x-input-label for="password_confirmation" :value="__('Confirm Password')" />

            <x-text-input wire:model="password_confirmation" id="password_confirmation" class="block mt-1 w-full"
                            type="password"
                            name="password_confirmation" required autocomplete="new-password" dusk="password-confirmation-input" />

            <x-input-error :messages="$errors->get('password_confirmation')" class="mt-2" />
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