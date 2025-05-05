<?php

namespace Tests\Fakes;

use App\Services\ReplicadoService;
use Exception;

/**
 * Fake implementation of ReplicadoService for testing purposes.
 */
class FakeReplicadoService extends ReplicadoService
{
    /**
     * Controls the return value of validarNuspEmail.
     * true = success, false = validation failure, null = simulate service error.
     */
    public ?bool $validationResult = true;

    /**
     * Determines if the service should throw an exception.
     */
    public bool $shouldThrowException = false;

    /**
     * Simulates the validation logic.
     *
     * @throws \Exception
     */
    public function validarNuspEmail(int $codpes, string $email): bool
    {
        if ($this->shouldThrowException) {
            throw new Exception('Simulated Replicado service communication error.');
        }

        // Return the predefined result (true for success, false for invalid)
        return $this->validationResult ?? true; // Default to true if not set explicitly
    }

    /**
     * Sets the desired validation result for the next call.
     *
     * @param  bool|null  $result  true for success, false for failure, null to reset to default (true)
     * @return $this
     */
    public function shouldReturn(?bool $result): self
    {
        $this->validationResult = $result;
        $this->shouldThrowException = false; // Ensure it doesn't throw exception

        return $this;
    }

    /**
     * Configures the fake service to throw an exception on the next call.
     *
     * @return $this
     */
    public function shouldFail(): self
    {
        $this->shouldThrowException = true;

        return $this;
    }
}
