<?php

use Illuminate\Auth\Events\PasswordReset;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Password;
use Illuminate\Support\Facades\Session;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules;
use Livewire\Attributes\Layout;
use Livewire\Attributes\Locked;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    #[Locked]
    public string $token = '';
    public string $email = '';
    public string $password = '';
    public string $password_confirmation = '';

    /**
     * Mount the component.
     */
    public function mount(string $token): void
    {
        $this->token = $token;

        $this->email = request()->string('email');
    }

    /**
     * Reset the password for the given user.
     */
    public function resetPassword(): void
    {
        // Valida os dados de entrada (token, email, senha, confirmação de senha)
        // Utiliza as regras padrão de validação de senha do Laravel.
        $this->validate([
            'token' => ['required'],
            'email' => ['required', 'string', 'email'],
            'password' => ['required', 'string', 'confirmed', Rules\Password::defaults()],
        ]);

        // Tenta redefinir a senha do usuário usando o Password Broker.
        // O método `reset` recebe as credenciais e uma closure que será executada
        // se o token e o email forem válidos.
        $status = Password::reset(
            $this->only('email', 'password', 'password_confirmation', 'token'),
            function ($user) {
                // Dentro da closure, atualiza a senha do usuário no banco de dados.
                $user->forceFill([
                    'password' => Hash::make($this->password), // Hash da nova senha
                    'remember_token' => Str::random(60), // Gera um novo remember token
                ])->save(); // Salva as alterações no usuário

                // Dispara o evento PasswordReset, que pode ser usado por listeners.
                event(new PasswordReset($user));
            }
        );

        // Se a redefinição de senha falhar (status diferente de PASSWORD_RESET),
        // adiciona um erro de validação ao campo de email com a mensagem de status traduzida.
        if ($status != Password::PASSWORD_RESET) {
            $this->addError('email', __($status));

            return; // Interrompe a execução
        }

        // *** INÍCIO DA MODIFICAÇÃO - AC9 Issue #22 ***
        // Se a redefinição for bem-sucedida:
        // 1. Define uma mensagem flash na sessão com o status traduzido (será exibida na próxima página).
        //    Ex: "Sua senha foi redefinida!" (vindo de lang/xx/passwords.php['reset'])
        Session::flash('status', __($status));

        // 2. Redireciona o usuário para a rota de login local (`login.local`),
        //    em vez da rota de login padrão (`login`) que agora é da Senha Única.
        $this->redirectRoute('login.local', navigate: true);
        // *** FIM DA MODIFICAÇÃO - AC9 Issue #22 ***
    }
}; ?>

{{-- Container principal do componente --}}
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

    {{-- Formulário de redefinição de senha --}}
    {{-- wire:submit previne o envio padrão e chama o método 'resetPassword' --}}
    <form wire:submit="resetPassword">
        <!-- Campo Email -->
        <div>
            <x-input-label for="email" :value="__('Email')" />
            {{-- Input de email, vinculado à propriedade $email via wire:model --}}
            {{-- Usa autocomplete="username" para compatibilidade com gerenciadores de senha --}}
            <x-text-input wire:model="email" id="email" class="block mt-1 w-full" type="email" name="email" required autofocus autocomplete="username" dusk="email-input"/>
            {{-- Exibe erros de validação para o campo 'email' --}}
            <x-input-error :messages="$errors->get('email')" class="mt-2" />
        </div>

        <!-- Campo Nova Senha -->
        <div class="mt-4">
            <x-input-label for="password" :value="__('Password')" />
            {{-- Input de senha, vinculado à propriedade $password --}}
            {{-- Usa autocomplete="new-password" para sugerir geração de senha segura --}}
            <x-text-input wire:model="password" id="password" class="block mt-1 w-full" type="password" name="password" required autocomplete="new-password" dusk="password-input"/>
            {{-- Exibe erros de validação para o campo 'password' --}}
            <x-input-error :messages="$errors->get('password')" class="mt-2" />
        </div>

        <!-- Campo Confirmação de Senha -->
        <div class="mt-4">
            <x-input-label for="password_confirmation" :value="__('Confirm Password')" />
            {{-- Input de confirmação, vinculado à propriedade $password_confirmation --}}
            <x-text-input wire:model="password_confirmation" id="password_confirmation" class="block mt-1 w-full"
                          type="password"
                          name="password_confirmation" required autocomplete="new-password" dusk="password-confirmation-input"/>
            {{-- Exibe erros de validação para o campo 'password_confirmation' --}}
            <x-input-error :messages="$errors->get('password_confirmation')" class="mt-2" />
        </div>

        {{-- Botão de envio --}}
        <div class="flex items-center justify-end mt-4">
            <x-primary-button dusk="reset-password-button">
                {{ __('Reset Password') }}
            </x-primary-button>
        </div>
    </form>
</div>