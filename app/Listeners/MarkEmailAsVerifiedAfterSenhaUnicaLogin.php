<?php

namespace App\Listeners;

use App\Models\User;
use Illuminate\Auth\Events\Login;
use Illuminate\Support\Facades\Log;

class MarkEmailAsVerifiedAfterSenhaUnicaLogin
{
    /**
     * Handle the event.
     */
    public function handle(Login $event): void
    {
        if ($event->user instanceof User) {
            /** @var User $user */
            $user = $event->user;

            // Check if user has codpes (USP user), email is not verified,
            // and local password is null (indicating a Senha Única user without a local password)
            if ($user->codpes && is_null($user->email_verified_at) && $user->password === null) {
                $user->forceFill([
                    'email_verified_at' => now(),
                ])->save();

                Log::info("Email para usuário USP #{$user->id} ({$user->email}) verificado automaticamente após login via Senha Única (password local nulo).");
            }
        }
    }
}
