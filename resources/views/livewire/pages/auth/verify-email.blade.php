<?php

use App\Livewire\Actions\Logout;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Session;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    /**
     * Send an email verification notification to the user.
     */
    public function sendVerification(): void
    {
        // Verifica se o usuário já está verificado para evitar reenvios desnecessários
        if (Auth::user()->hasVerifiedEmail()) {
            // Redireciona para o dashboard ou página principal se já verificado
            // O 'navigate: true' usa o SPA mode do Livewire/Turbolinks
            $this->redirectIntended(default: route('dashboard', absolute: false), navigate: true);

            return; // Termina a execução aqui
        }

        // Envia a notificação de verificação de email
        Auth::user()->sendEmailVerificationNotification();

        // Define uma mensagem flash na sessão para indicar que o link foi enviado
        // Esta mensagem será exibida pelo componente <x-auth-session-status> ou similar (AC6)
        Session::flash('status', 'verification-link-sent');
    }

    /**
     * Log the current user out of the application.
     */
    public function logout(Logout $logout): void
    {
        $logout();

        $this->redirect('/', navigate: true);
    }
}; ?>

<div>
    <div class="flex justify-center mb-4">
        <a href="/" wire:navigate>
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-padrao.png') }}" alt="Logo IME-USP" class="w-20 h-auto block dark:hidden" dusk="ime-logo-light">
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-branca.png') }}" alt="Logo IME-USP" class="w-20 h-auto hidden dark:block" dusk="ime-logo-dark">
        </a>
    </div>

    <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
        {{ __('Thanks for signing up! Before getting started, could you verify your email address by clicking on the link we just emailed to you? If you didn\'t receive the email, we will gladly send you another.') }}
    </div>

    {{-- AC6: Exibe a mensagem de status flash usando o componente <x-auth-session-status /> --}}
    {{-- Verifica se a chave 'status' na sessão tem o valor esperado e passa a mensagem traduzida para o componente --}}
    @if (session('status') === 'verification-link-sent')
        <x-auth-session-status class="mb-4" :status="__('A new verification link has been sent to the email address you provided during registration.')" dusk="auth-session-status" />
    @endif


    <div class="mt-4 flex items-center justify-between">
        {{-- AC3: Botão que dispara a ação Livewire sendVerification (AC4) --}}
        <x-primary-button wire:click="sendVerification">
            {{ __('Resend Verification Email') }}
        </x-primary-button>

        <button wire:click="logout" type="submit" class="underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800">
            {{ __('Log Out') }}
        </button>
    </div>
</div>