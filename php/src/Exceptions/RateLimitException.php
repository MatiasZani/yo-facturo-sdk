<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

/**
 * 429 Too Many Requests: se superó el límite de frecuencia de la cuenta.
 */
class RateLimitException extends ApiException
{
    private ?float $retryAfter;

    /**
     * @param array<int, mixed>|null $errors
     * @param mixed $responseBody
     */
    public function __construct(
        string $message,
        ?int $statusCode = null,
        ?string $apiCode = null,
        ?array $errors = null,
        $responseBody = null,
        ?float $retryAfter = null
    ) {
        parent::__construct($message, $statusCode, $apiCode, $errors, $responseBody);
        $this->retryAfter = $retryAfter;
    }

    /**
     * Segundos a esperar antes de reintentar, si la API mandó el header
     * `Retry-After`. Hoy no siempre está presente en producción -- puede
     * ser `null`; el cliente igual reintenta con backoff exponencial propio.
     */
    public function getRetryAfter(): ?float
    {
        return $this->retryAfter;
    }
}
