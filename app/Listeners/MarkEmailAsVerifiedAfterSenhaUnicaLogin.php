<?php

namespace App\Listeners;

use Illuminate\Auth\Events\Login;
use App\Models\User;
use Illuminate\Support\Facades\Log;

class MarkEmailAsVerifiedAfterSenhaUnicaLogin
{
    /**
     * Handle the event.
     *
     * @param  \Illuminate\Auth\Events\Login  $event
     * @return void
     */
    public function handle(Login $event): void
    {
        if ($event->user instanceof User) {
            /** @var User $user */
            $user = $event->user;

            if ($user->codpes && is_null($user->email_verified_at) && is_null($user->getAuthPassword())) {
                $user->forceFill([ 
                    'email_verified_at' => now(),
                ])->save();

                Log::info("Email para usuário USP #{$user->id} ({$user->email}) verificado automaticamente após login via Senha Única (password local nulo).");
            }
        }
    }
}