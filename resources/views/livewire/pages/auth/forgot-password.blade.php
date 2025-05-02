<?php

use Illuminate\Support\Facades\Password;
use Illuminate\Support\Facades\Session;
use Livewire\Attributes\Layout;
use Livewire\Attributes\Rule;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    #[Rule(['required', 'email'])]
    public string $email = '';

    /**
     * Handle an incoming password reset link request.
     */
    public function sendPasswordResetLink(): void
    {
        $this->validate();

        $status = Password::sendResetLink(
            ['email' => $this->email]
        );

        if ($status === Password::ResetLinkSent) {
            Session::flash('status', __($status));

            return;
        }

        $this->addError('email', __($status));
    }
}; ?>

<div>
    {{-- Seção do Logo IME --}}
    <div class="flex justify-center mb-4">
        <a href="/" wire:navigate>
            {{-- Logo para tema claro --}}
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-padrao.png') }}" alt="Logo IME-USP" class="w-20 h-auto block dark:hidden" dusk="ime-logo-light">
            {{-- Logo para tema escuro --}}
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-branca.png') }}" alt="Logo IME-USP" class="w-20 h-auto hidden dark:block" dusk="ime-logo-dark">
        </a>
    </div>

    <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
        {{ __('Forgot your password? No problem. Just let us know your email address and we will email you a password reset link that will allow you to choose a new one.') }}
    </div>

    <!-- Session Status -->
    <x-auth-session-status class="mb-4" :status="session('status')" />

    <form wire:submit="sendPasswordResetLink">
        <!-- Email Address -->
        <div>
            <x-input-label for="email" :value="__('Email')" />
            <x-text-input wire:model="email" id="email" class="block mt-1 w-full" type="email" name="email" required autofocus dusk="email-input" />
            <x-input-error :messages="$errors->get('email')" class="mt-2" />
        </div>

        <div class="flex items-center justify-end mt-4">
            <x-primary-button dusk="send-reset-link-button">
                {{ __('Email Password Reset Link') }}
            </x-primary-button>
        </div>

        {{-- Link para voltar ao Login Local --}}
        <div class="flex items-center justify-start mt-4">
            <a class="underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800"
               href="{{ route('login.local') }}"
               wire:navigate
               dusk="login-link">
                {{ __('Log in') }}
            </a>
        </div>
    </form>
</div>