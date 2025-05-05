<?php

namespace App\Services;

use Illuminate\Support\Facades\Log; // Assuming Uspdev\Replicado is used
use Uspdev\Replicado\Pessoa; // For logging errors

/**
 * Service class to interact with USP's Replicado database.
 *
 * NOTE: This is a placeholder structure. The actual implementation depends
 * on the 'uspdev/replicado' package or direct DB connection setup.
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
     * @throws \Exception If there's an issue communicating with the Replicado database.
     */
    public function validarNuspEmail(int $codpes, string $email): bool
    {
        // --- Placeholder Implementation ---
        // This requires the actual logic using uspdev/replicado or similar.

        // Basic check: Ensure email is a USP email if we are validating
        // This might be redundant if already checked elsewhere, but adds safety.
        if (! str_ends_with(strtolower($email), 'usp.br')) {
            Log::warning("Replicado Validation: Attempt to validate non-USP email '{$email}' for codpes {$codpes}.");
            // return false; // Or handle as per requirements, maybe this check is done earlier.
        }

        try {
            // Example using uspdev/replicado (adjust based on actual package methods)
            $emailsPessoa = Pessoa::emails($codpes); // Get all emails associated with codpes

            if (empty($emailsPessoa)) {
                Log::info("Replicado Validation: No person found for codpes {$codpes}.");

                return false; // Person (codpes) doesn't exist or has no emails registered.
            }

            // Check if the provided email is in the list of the person's emails
            foreach ($emailsPessoa as $emailCadastrado) {
                if (is_string($emailCadastrado) && (strtolower(trim($emailCadastrado)) === strtolower($email))) {
                    Log::info("Replicado Validation: Success for codpes {$codpes} and email '{$email}'.");

                    return true; // Found a match
                }
            }

            // If loop completes without finding a matchs
            Log::info("Replicado Validation: Email '{$email}' does not match registered emails for codpes {$codpes}.");

            return false;

            /*
            // Alternative hypothetical direct query logic (if not using the package)
            $result = DB::connection('replicado') // Assuming a 'replicado' connection exists
                ->table('PESSOA') // Replace with actual table names
                ->join('EMAILPESSOA', 'PESSOA.codpes', '=', 'EMAILPESSOA.codpes')
                ->where('PESSOA.codpes', $codpes)
                ->where('EMAILPESSOA.codema', $email)
                // Add conditions to check for active status if necessary
                ->exists();

            return $result;
            */

        } catch (\Exception $e) {
            // Log the error for investigation
            Log::error("Replicado Service Error: Failed validating codpes {$codpes} and email '{$email}'. Error: ".$e->getMessage());

            // Re-throw the exception to be handled by the caller (e.g., the validation rule)
            // This allows the caller to decide how to handle service failures (e.g., show specific error).
            throw new \Exception('Replicado service communication error.', 0, $e);
        }

        // Default to false if something unexpected happens, though exceptions should be caught.
        // return false; // This line might be unreachable if exceptions are always thrown/caught.
    }

    // Add other methods to interact with Replicado as needed...
}
