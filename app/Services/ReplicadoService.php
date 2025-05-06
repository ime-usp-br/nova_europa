<?php

namespace App\Services;

use App\Exceptions\ReplicadoServiceException; // Import custom exception
use Illuminate\Support\Facades\Log;
use Uspdev\Replicado\Pessoa;

/**
 * Service class to interact with USP's Replicado database.
 */
class ReplicadoService
{
    /**
     * Validates if the provided USP Number (codpes) and email belong to the same valid person in Replicado.
     *
     * This method needs to be implemented based on the available Replicado data access strategy.
     * It should check if the codpes exists and if the provided email is associated with that codpes.
     *
     * @param  int  $codpes  The USP number (NUSP).
     * @param  string  $email  The email address to validate against the codpes.
     * @return bool Returns true if the codpes and email match a valid person, false otherwise.
     *
     * @throws \App\Exceptions\ReplicadoServiceException If there's an issue communicating with the Replicado database.
     */
    public function validarNuspEmail(int $codpes, string $email): bool
    {
        if (! str_ends_with(strtolower($email), 'usp.br')) {
            Log::warning("Replicado Validation: Attempt to validate non-USP email '{$email}' for codpes {$codpes}.");
            // Depending on strictness, this might be an early return false or even an exception.
            // For now, let it proceed to check against Replicado records.
        }

        try {
            $emailsPessoa = Pessoa::emails($codpes);

            if (empty($emailsPessoa)) {
                Log::info("Replicado Validation: No person found or no emails registered for codpes {$codpes}.");

                return false;
            }

            foreach ($emailsPessoa as $emailCadastrado) {
                if (is_string($emailCadastrado) && (strtolower(trim($emailCadastrado)) === strtolower($email))) {
                    Log::info("Replicado Validation: Success for codpes {$codpes} and email '{$email}'.");

                    return true;
                }
            }

            Log::info("Replicado Validation: Email '{$email}' does not match registered emails for codpes {$codpes}.");

            return false;

        } catch (\Exception $e) {
            Log::error("Replicado Service Error: Failed validating codpes {$codpes} and email '{$email}'. Error: ".$e->getMessage(), ['exception' => $e]);
            // Re-throw as a custom, more specific exception for better handling by callers.
            throw new ReplicadoServiceException('Replicado service communication error while validating NUSP/email.', 0, $e);
        }
    }
}
