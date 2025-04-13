<?php

use App\Livewire\Forms\LoginForm;
use Illuminate\Support\Facades\Session;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    public LoginForm $form;

    /**
     * Processa uma tentativa de autenticação recebida.
     *
     * Valida os dados do formulário, tenta autenticar o usuário,
     * regenera a sessão em caso de sucesso e redireciona
     * para o painel (dashboard) ou para o destino pretendido.
     *
     * @return void
     * @throws \Illuminate\Validation\ValidationException Se a validação do formulário falhar ou a autenticação falhar.
     */
    public function login(): void
    {
        $this->validate(); // Valida o LoginForm

        $this->form->authenticate(); // Tenta autenticar (pode lançar ValidationException em caso de falha)

        Session::regenerate();

        $this->redirectIntended(default: route('dashboard', absolute: false), navigate: true);
    }
}; ?>

<div>
    <!-- Session Status -->
    <x-auth-session-status class="mb-4" :status="session('status')" />

    <form wire:submit="login">
        <!-- Email Address -->
        <div>
            <x-input-label for="email" :value="__('Email')" />
            <x-text-input wire:model="form.email" id="email" class="block mt-1 w-full" type="email" name="email" required autofocus autocomplete="username" />
            <x-input-error :messages="$errors->get('form.email')" class="mt-2" />
        </div>

        <!-- Password -->
        <div class="mt-4">
            <x-input-label for="password" :value="__('Password')" /> {{-- Chave em Inglês --}}

            <x-text-input wire:model="form.password" id="password" class="block mt-1 w-full"
                            type="password"
                            name="password"
                            required autocomplete="current-password" />

            <x-input-error :messages="$errors->get('form.password')" class="mt-2" />
        </div>

        <!-- Remember Me -->
        <div class="block mt-4">
            <label for="remember" class="inline-flex items-center">
                <input wire:model="form.remember" id="remember" type="checkbox" class="rounded dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-indigo-600 shadow-sm focus:ring-indigo-500 dark:focus:ring-indigo-600 dark:focus:ring-offset-gray-800" name="remember">
                <span class="ms-2 text-sm text-gray-600 dark:text-gray-400">{{ __('Remember me') }}</span> {{-- Chave em Inglês --}}
            </label>
        </div>

        <div class="flex items-center justify-end mt-4">
            {{-- Link para Registrar-se (AC5) - Adicionado --}}
            @if (Route::has('register'))
                <a href="{{ route('register') }}" wire:navigate class="underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800">
                    {{ __('Register') }}
                </a>
            @endif

            {{-- Link Esqueci Minha Senha (AC4) - Movido para ms-4 para espaçamento --}}
            @if (Route::has('password.request'))
                <a class="ms-4 underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800" href="{{ route('password.request') }}" wire:navigate>
                    {{ __('Forgot your password?') }}
                </a>
            @endif

            <x-primary-button class="ms-4"> {{-- Ajustado margin para ms-4 --}}
                {{ __('Log in') }}
            </x-primary-button>
        </div>

    </form>

    {{-- Botão Login com Senha Única USP (AC2) --}}
    <div class="flex items-center justify-center mt-4">
        <a href="{{ route('login') }}" class="w-full inline-flex items-center justify-center px-4 py-2 bg-yellow-500 dark:bg-yellow-600 border border-transparent rounded-md font-semibold text-xs text-white dark:text-gray-900 uppercase tracking-widest hover:bg-yellow-400 dark:hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition ease-in-out duration-150">
            {{ __('Login with Senha Única USP') }}
        </a>
    </div>

</div>