<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

/**
 * Error devuelto por la API que no tiene un tipo más específico.
 *
 * Expone el código de estado HTTP, el `code` estable de la API (ej.
 * "VALIDATION_ERROR") y, en errores de validación, el detalle por campo.
 * Ver la guía de errores de la API: https://yo-facturo.com/dev/errors/
 */
class ApiException extends YoFacturoException
{
    private ?int $statusCode;
    private ?string $apiCode;

    /** @var array<int, mixed> */
    private array $errors;

    /** @var mixed */
    private $responseBody;

    /**
     * @param array<int, mixed>|null $errors
     * @param mixed $responseBody
     */
    public function __construct(
        string $message,
        ?int $statusCode = null,
        ?string $apiCode = null,
        ?array $errors = null,
        $responseBody = null
    ) {
        parent::__construct($message);
        $this->statusCode = $statusCode;
        $this->apiCode = $apiCode;
        $this->errors = $errors ?? [];
        $this->responseBody = $responseBody;
    }

    public function getStatusCode(): ?int
    {
        return $this->statusCode;
    }

    /** El código estable de la API, ej. "NOT_FOUND" (campo `code` de la respuesta). */
    public function getApiCode(): ?string
    {
        return $this->apiCode;
    }

    /** @return array<int, mixed> */
    public function getErrors(): array
    {
        return $this->errors;
    }

    /** @return mixed */
    public function getResponseBody()
    {
        return $this->responseBody;
    }
}
