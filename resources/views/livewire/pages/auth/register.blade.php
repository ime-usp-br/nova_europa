<?php

use App\Models\User;
use Illuminate\Auth\Events\Registered;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\Rule; // Import Rule for required_if
use Illuminate\Validation\Rules;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.guest')] class extends Component
{
    public string $name = '';
    public string $email = '';
    public string $password = '';
    public string $password_confirmation = '';

    // --- ADDED LIVEWIRE PROPERTIES ---
    public bool $sou_da_usp = false;
    public string $codpes = '';
    // --- END ADDED ---

    // --- ADDED LIFECYCLE HOOK ---
    /**
     * Automatically check "Sou da USP" if email ends with usp.br
     */
    public function updatedEmail(string $value): void
    {
        if (str_ends_with(strtolower($value), 'usp.br')) {
            $this->sou_da_usp = true;
        }
        // Optional: uncheck if email is changed away from @usp.br and wasn't manually checked?
        // else {
        //     // Only uncheck if it wasn't manually set? This gets tricky.
        //     // Maybe it's better to just let the user uncheck it if they change email.
        // }
    }
    // --- END ADDED ---


    /**
     * Validation rules.
     */
    public function rules(): array // Changed to method to allow dynamic rules
    {
        return [
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'string', 'lowercase', 'email', 'max:255', 'unique:'.User::class],
            // --- ADDED/MODIFIED VALIDATION ---
            'sou_da_usp' => ['boolean'], // Validate the checkbox value itself
            'codpes' => [
                // Only require codpes if the sou_da_usp checkbox is checked
                // (which is automatically checked if email ends with @usp.br)
                Rule::requiredIf($this->sou_da_usp),
                'nullable', // Allows it to be null if not required
                'numeric', // Basic numeric check
                'digits_between:6,8', // Adjust digits as needed for Nº USP format
                // Add custom validation rule or Replicado check later if needed
            ],
            // --- END ADDED/MODIFIED ---
            'password' => ['required', 'string', 'confirmed', Rules\Password::defaults()],
        ];
    }


    /**
     * Handle an incoming registration request.
     */
    public function register(): void
    {
        // Validate using the rules() method
        $validated = $this->validate();

        // --- MODIFIED USER CREATION ---
        // Include sou_da_usp and codpes if needed in the User model's fillable array
        // (Add 'codpes' to $fillable in App\Models\User.php)
        // You might store 'sou_da_usp' or derive it later. Let's add codpes for now.
        $userData = [
            'name' => $validated['name'],
            'email' => $validated['email'],
            'password' => Hash::make($validated['password']),
            'codpes' => $this->sou_da_usp ? $validated['codpes'] : null, // Only save if marked as USP
        ];
        // --- END MODIFIED ---

        event(new Registered($user = User::create($userData))); // Use modified data

        Auth::login($user);

        $this->redirect(route('dashboard', absolute: false), navigate: true);
    }
}; ?>

{{-- Wrap the interactive section with x-data --}}
{{-- No extra Alpine state needed if Livewire handles it --}}
<div x-data="{}">
    <form wire:submit="register">
        <!-- Name -->
        <div>
            <x-input-label for="name" :value="__('Name')" />
            <x-text-input wire:model="name" id="name" class="block mt-1 w-full" type="text" name="name" required autofocus autocomplete="name" />
            <x-input-error :messages="$errors->get('name')" class="mt-2" />
        </div>

        <!-- Email Address -->
        <div class="mt-4">
            <x-input-label for="email" :value="__('Email')" />
            {{-- Use wire:model.defer.blur to update Livewire state less frequently --}}
            {{-- Or use wire:model.live if you need instant backend reaction beyond the hook --}}
            <x-text-input wire:model.blur="email" id="email" class="block mt-1 w-full" type="email" name="email" required autocomplete="username" />
            <x-input-error :messages="$errors->get('email')" class="mt-2" />
        </div>

        {{-- --- ADDED USP FIELDS --- --}}
        <!-- "Sou da USP" Checkbox -->
        <div class="block mt-4">
            <label for="sou_da_usp" class="inline-flex items-center">
                <input wire:model="sou_da_usp"
                       id="sou_da_usp"
                       type="checkbox"
                       {{-- Disable checkbox if email is already a USP email --}}
                       :disabled="$wire.email.toLowerCase().endsWith('usp.br')"
                       class="rounded dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-indigo-600 shadow-sm focus:ring-indigo-500 dark:focus:ring-indigo-600 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                       name="sou_da_usp">
                <span class="ms-2 text-sm text-gray-600 dark:text-gray-400">{{ __('Sou da USP') }}</span>
            </label>
             <x-input-error :messages="$errors->get('sou_da_usp')" class="mt-2" />
        </div>

        <!-- Número USP (codpes) Field - Conditional -->
        {{-- Show if email ends with @usp.br OR the checkbox is checked --}}
        <div x-show="$wire.email.toLowerCase().endsWith('usp.br') || $wire.sou_da_usp"
             x-transition
             class="mt-4">
            <x-input-label for="codpes" :value="__('Número USP (codpes)')" />
            <x-text-input wire:model="codpes" id="codpes" class="block mt-1 w-full"
                          type="text" {{-- Use text, validation handles numeric --}}
                          inputmode="numeric" {{-- Hint for mobile keyboards --}}
                          name="codpes"
                          autocomplete="off" />
            <x-input-error :messages="$errors->get('codpes')" class="mt-2" />
        </div>
        {{-- --- END ADDED USP FIELDS --- --}}


        <!-- Password -->
        <div class="mt-4">
            <x-input-label for="password" :value="__('Password')" />
            <x-text-input wire:model="password" id="password" class="block mt-1 w-full"
                            type="password"
                            name="password"
                            required autocomplete="new-password" />
            <x-input-error :messages="$errors->get('password')" class="mt-2" />
        </div>

        <!-- Confirm Password -->
        <div class="mt-4">
            <x-input-label for="password_confirmation" :value="__('Confirm Password')" />
            <x-text-input wire:model="password_confirmation" id="password_confirmation" class="block mt-1 w-full"
                            type="password"
                            name="password_confirmation" required autocomplete="new-password" />
            <x-input-error :messages="$errors->get('password_confirmation')" class="mt-2" />
        </div>

        <div class="flex items-center justify-end mt-4">
            <a class="underline text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800" href="{{ route('login.local') }}" wire:navigate>
                {{ __('Already registered?') }}
            </a>
            <x-primary-button class="ms-4">
                {{ __('Register') }}
            </x-primary-button>
        </div>
    </form>
</div>