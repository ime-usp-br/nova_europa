<?php

use Illuminate\Support\Facades\Password;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

// Define o layout 'guest' para este componente Volt
new #[Layout('layouts.guest')] class extends Component
{
    // Propriedade pública para vincular ao campo de e-mail no formulário
    public string $email = '';

    /**
     * Envia um link de redefinição de senha para o endereço de e-mail fornecido.
     * Esta lógica será relevante para AC8, mas a estrutura do método é necessária
     * para o funcionamento do formulário definido neste componente (AC1).
     */
    public function sendPasswordResetLink(): void
    {
        // Valida se o e-mail é obrigatório e tem formato válido
        $this->validate([
            'email' => ['required', 'string', 'email'],
        ]);

        // Tenta enviar o link de redefinição de senha usando o Password Broker padrão.
        // O Password Broker lida com a lógica de encontrar o usuário pelo e-mail
        // e enviar a notificação (que contém o link)
        $status = Password::sendResetLink(
            $this->only('email') // Passa apenas o e-mail para o broker
        );

        // Se o envio falhar (status diferente de RESET_LINK_SENT), adiciona um erro
        // de validação ao campo de e-mail com a mensagem de status traduzida.
        if ($status != Password::RESET_LINK_SENT) {
            $this->addError('email', __($status)); // Usa __() para traduzir o status

            return; // Interrompe a execução
        }

        // Se o envio for bem-sucedido, limpa o campo de e-mail no formulário
        $this->reset('email');

        // Define uma mensagem flash na sessão com o status traduzido (será exibida pelo <x-auth-session-status>)
        session()->flash('status', __($status)); // Usa __() para traduzir o status
    }
}; ?>

{{-- Container principal do componente --}}
<div>
    {{-- Seção do Logo IME (AC1) --}}
    <div class="flex justify-center mb-4">
        <a href="/" wire:navigate>
            {{-- Logo para tema claro, usa Vite::asset para obter o caminho --}}
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-padrao.png') }}" alt="Logo IME-USP" class="w-20 h-auto block dark:hidden" dusk="ime-logo-light">
            {{-- Logo para tema escuro (hidden por padrão, block em dark mode) --}}
            <img src="{{ Vite::asset('resources/images/ime/logo-vertical-simplificada-branca.png') }}" alt="Logo IME-USP" class="w-20 h-auto hidden dark:block" dusk="ime-logo-dark">
        </a>
    </div>

    {{-- Texto explicativo sobre a funcionalidade (AC1) --}}
    <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
        {{ __('Forgot your password? No problem. Just let us know your email address and we will email you a password reset link that will allow you to choose a new one.') }}
    </div>

    {{-- Componente para exibir mensagens de status da sessão (relevante para AC8) --}}
    <x-auth-session-status class="mb-4" :status="session('status')" />

    {{-- Formulário para solicitar o link (AC1) --}}
    {{-- wire:submit previne o envio padrão e chama o método 'sendPasswordResetLink' do componente --}}
    <form wire:submit="sendPasswordResetLink">
        {{-- Campo de Email (AC1) --}}
        <div>
            {{-- Rótulo do campo, usa o componente x-input-label e tradução --}}
            <x-input-label for="email" :value="__('Email')" />
            {{-- Input de texto, vinculado à propriedade $email via wire:model --}}
            {{-- Usa o componente x-text-input para estilo padronizado --}}
            <x-text-input wire:model="email" id="email" class="block mt-1 w-full" type="email" name="email" required autofocus />
            {{-- Componente para exibir erros de validação associados ao campo 'email' --}}
            <x-input-error :messages="$errors->get('email')" class="mt-2" />
        </div>

        {{-- Seção do botão de envio (AC1) --}}
        <div class="flex items-center justify-end mt-4">
            {{-- Botão primário, usa o componente x-primary-button e tradução --}}
            <x-primary-button>
                {{ __('Email Password Reset Link') }}
            </x-primary-button>
        </div>
    </form>
</div>