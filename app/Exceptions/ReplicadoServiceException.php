<?php

namespace App\Exceptions;

use Exception;
use Throwable;

/**
 * Exception thrown when ReplicadoService encounters an error.
 *
 * This exception is used to wrap any errors that occur when interacting
 * with the USP Replicado database, such as connection failures, query errors,
 * or data retrieval issues.
 */
class ReplicadoServiceException extends Exception
{
    /**
     * Create a new ReplicadoServiceException instance.
     *
     * @param  string  $message  The exception message
     * @param  int  $code  The exception code (default: 0)
     * @param  Throwable|null  $previous  The previous exception for exception chaining
     */
    public function __construct(string $message = '', int $code = 0, ?Throwable $previous = null)
    {
        parent::__construct($message, $code, $previous);
    }

    /**
     * Create an exception for database connection failures.
     *
     * @param  Throwable  $previous  The original exception
     */
    public static function connectionFailed(Throwable $previous): self
    {
        return new self(
            __('Unable to connect to Replicado database. Please check your connection settings.'),
            500,
            $previous
        );
    }

    /**
     * Create an exception for query execution failures.
     *
     * @param  string  $query  The query that failed
     * @param  Throwable  $previous  The original exception
     */
    public static function queryFailed(string $query, Throwable $previous): self
    {
        return new self(
            __('Failed to execute Replicado query: :query', ['query' => $query]),
            500,
            $previous
        );
    }

    /**
     * Create an exception for when a resource is not found.
     *
     * @param  string  $resource  The resource type that was not found
     * @param  int|string  $identifier  The identifier that was searched for
     */
    public static function notFound(string $resource, int|string $identifier): self
    {
        return new self(
            __(':resource not found with identifier: :identifier', [
                'resource' => $resource,
                'identifier' => (string) $identifier,
            ]),
            404
        );
    }

    /**
     * Create an exception for invalid parameters.
     *
     * @param  string  $parameter  The parameter name
     * @param  string  $reason  The reason why the parameter is invalid
     */
    public static function invalidParameter(string $parameter, string $reason): self
    {
        return new self(
            __('Invalid parameter :parameter: :reason', [
                'parameter' => $parameter,
                'reason' => $reason,
            ]),
            400
        );
    }
}
