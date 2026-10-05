<?php

declare(strict_types=1);

namespace YoFacturo;

use InvalidArgumentException;
use YoFacturo\Exceptions\ApiException;
use YoFacturo\Exceptions\AuthenticationException;
use YoFacturo\Exceptions\ConflictException;
use YoFacturo\Exceptions\NotFoundException;
use YoFacturo\Exceptions\RateLimitException;
use YoFacturo\Exceptions\ScopeException;
use YoFacturo\Exceptions\ServerException;
use YoFacturo\Exceptions\ValidationException;
use YoFacturo\Exceptions\YoFacturoException;
use YoFacturo\Resources\CustomersResource;
use YoFacturo\Resources\InvoicesResource;
use YoFacturo\Resources\ProductsResource;
use YoFacturo\Resources\SalesResource;

/**
 * Cliente principal del SDK de YoFacturo.
 *
 * Sin dependencias: usa curl nativo de PHP. El transporte real es
 * inyectable (parámetro `$transport`) para poder testear el cliente sin
 * red -- ver `php/tests/` si el repo las incluye, o `examples/`.
 */
class Client
{
    public const VERSION = '0.2.0';
    public const DEFAULT_BASE_URL = 'https://api.yo-facturo.com/api/v1';

    private string $apiKey;
    private string $baseUrl;
    private float $timeout;
    private int $maxRetries;

    /** @var callable(string, string, array<string, string>, ?string, float): array{0: int, 1: array<string, string>, 2: string} */
    private $transport;

    /** @var callable(float): void */
    private $sleep;

    public InvoicesResource $invoices;
    public CustomersResource $customers;
    public ProductsResource $products;
    public SalesResource $sales;

    /**
     * @param string $apiKey token `yf_live_...` (o `yf_test_...` para sandbox), generado
     *   desde Configuración → Integraciones → API Tokens en el panel.
     * @param string $baseUrl URL base de la API. Por defecto la de producción.
     * @param float $timeout timeout por request, en segundos.
     * @param int $maxRetries reintentos automáticos ante 429/5xx (con backoff
     *   exponencial). 0 desactiva los reintentos.
     * @param callable|null $transport transporte HTTP inyectable (para tests). Firma:
     *   `function(string $method, string $url, array $headers, ?string $body, float $timeout): array`
     *   que debe devolver `[int $status, array $responseHeaders, string $rawBody]`.
     * @param callable|null $sleep función usada para esperar entre reintentos (para
     *   tests). Firma: `function(float $seconds): void`.
     */
    public function __construct(
        string $apiKey,
        string $baseUrl = self::DEFAULT_BASE_URL,
        float $timeout = 30.0,
        int $maxRetries = 3,
        ?callable $transport = null,
        ?callable $sleep = null
    ) {
        if ($apiKey === '') {
            throw new InvalidArgumentException('apiKey es obligatorio');
        }

        $this->apiKey = $apiKey;
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->timeout = $timeout;
        $this->maxRetries = $maxRetries;
        $this->transport = $transport ?? [self::class, 'defaultTransport'];
        $this->sleep = $sleep ?? static function (float $seconds): void {
            usleep((int) ($seconds * 1000000));
        };

        $this->invoices = new InvoicesResource($this);
        $this->customers = new CustomersResource($this);
        $this->products = new ProductsResource($this);
        $this->sales = new SalesResource($this);
    }

    /**
     * @param array<string, mixed>|null $params
     * @return mixed
     */
    public function get(string $path, ?array $params = null)
    {
        return $this->request('GET', $path, $params);
    }

    /**
     * POST genérico. `$idempotencyKey` es opcional: si se manda, viaja en
     * el header `Idempotency-Key`. La API lo soporta hoy en `POST /sales/`,
     * `POST /products/` y `POST /bill/receipts/invoice/` -- reenviar la
     * misma clave dentro de las 24h reproduce la respuesta original en vez
     * de crear un recurso duplicado.
     *
     * @param array<string, mixed>|null $jsonBody
     * @return mixed
     */
    public function post(string $path, ?array $jsonBody = null, ?string $idempotencyKey = null)
    {
        $extraHeaders = $idempotencyKey !== null ? ['Idempotency-Key' => $idempotencyKey] : [];

        return $this->request('POST', $path, null, $jsonBody, $extraHeaders);
    }

    /**
     * @param array<string, mixed>|null $jsonBody
     * @return mixed
     */
    public function put(string $path, ?array $jsonBody = null)
    {
        return $this->request('PUT', $path, null, $jsonBody);
    }

    /**
     * @param array<string, mixed>|null $jsonBody
     * @return mixed
     */
    public function patch(string $path, ?array $jsonBody = null)
    {
        return $this->request('PATCH', $path, null, $jsonBody);
    }

    /** @return mixed */
    public function delete(string $path)
    {
        return $this->request('DELETE', $path);
    }

    /**
     * @param array<string, mixed>|null $params
     * @param array<string, mixed>|null $jsonBody
     * @param array<string, string> $extraHeaders
     * @return mixed
     */
    public function request(
        string $method,
        string $path,
        ?array $params = null,
        ?array $jsonBody = null,
        array $extraHeaders = []
    ) {
        $url = $this->buildUrl($path, $params);
        $headers = array_merge(
            [
                'X-API-Key' => $this->apiKey,
                'Accept' => 'application/json',
                'User-Agent' => 'yofacturo-sdk-php/' . self::VERSION,
            ],
            $extraHeaders
        );

        $body = null;
        if ($jsonBody !== null) {
            $body = (string) json_encode($jsonBody, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            $headers['Content-Type'] = 'application/json';
        }

        $attempts = $this->maxRetries + 1;
        for ($attempt = 0; $attempt < $attempts; $attempt++) {
            [$status, $responseHeaders, $raw] = ($this->transport)($method, $url, $headers, $body, $this->timeout);
            $data = self::parseJson($raw);

            if ($status >= 200 && $status < 300) {
                return $data;
            }

            $retryAfter = self::parseRetryAfter($responseHeaders);
            $retryable = $status === 429 || $status >= 500;
            if ($retryable && $attempt < $attempts - 1) {
                ($this->sleep)(self::backoffDelaySeconds($attempt, $retryAfter));
                continue;
            }

            [$message, $code, $fieldErrors] = self::extractError($data);

            throw self::exceptionFromResponse($status, $code, $message, $fieldErrors, $data, $retryAfter);
        }

        // @codeCoverageIgnoreStart
        throw new YoFacturoException('No se pudo completar la petición a la API de YoFacturo');
        // @codeCoverageIgnoreEnd
    }

    /** @param array<string, mixed>|null $params */
    private function buildUrl(string $path, ?array $params): string
    {
        $url = $this->baseUrl . $path;
        if ($params) {
            $filtered = array_filter($params, static function ($value): bool {
                return $value !== null;
            });
            if ($filtered) {
                $url .= '?' . http_build_query($filtered);
            }
        }

        return $url;
    }

    /** @return mixed */
    private static function parseJson(string $raw)
    {
        if ($raw === '') {
            return null;
        }

        $decoded = json_decode($raw, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            return ['success' => false, 'error' => $raw, 'code' => null];
        }

        return $decoded;
    }

    /** @param array<string, string> $headers */
    private static function parseRetryAfter(array $headers): ?float
    {
        foreach ($headers as $name => $value) {
            if (strtolower((string) $name) === 'retry-after') {
                return is_numeric($value) ? (float) $value : null;
            }
        }

        return null;
    }

    /**
     * @param mixed $data
     * @return array{0: string, 1: ?string, 2: ?array<int, mixed>}
     */
    private static function extractError($data): array
    {
        if (is_array($data)) {
            $message = $data['error'] ?? $data['message'] ?? 'Error desconocido de la API de YoFacturo';

            return [(string) $message, $data['code'] ?? null, $data['errors'] ?? null];
        }

        return ['Error desconocido de la API de YoFacturo', null, null];
    }

    private static function backoffDelaySeconds(int $attempt, ?float $retryAfter): float
    {
        if ($retryAfter !== null && $retryAfter >= 0) {
            return $retryAfter;
        }

        $base = min(8.0, 0.5 * (2 ** $attempt));

        return $base + (mt_rand(0, 250) / 1000);
    }

    /**
     * @param array<int, mixed>|null $errors
     * @param mixed $responseBody
     */
    private static function exceptionFromResponse(
        int $statusCode,
        ?string $code,
        string $message,
        ?array $errors,
        $responseBody,
        ?float $retryAfter
    ): ApiException {
        switch ($statusCode) {
            case 401:
                return new AuthenticationException($message, $statusCode, $code, $errors, $responseBody);
            case 403:
                return new ScopeException($message, $statusCode, $code, $errors, $responseBody);
            case 404:
                return new NotFoundException($message, $statusCode, $code, $errors, $responseBody);
            case 409:
                return new ConflictException($message, $statusCode, $code, $errors, $responseBody);
            case 400:
            case 422:
                return new ValidationException($message, $statusCode, $code, $errors, $responseBody);
            case 429:
                return new RateLimitException($message, $statusCode, $code, $errors, $responseBody, $retryAfter);
            default:
                if ($statusCode >= 500) {
                    return new ServerException($message, $statusCode, $code, $errors, $responseBody);
                }

                return new ApiException($message, $statusCode, $code, $errors, $responseBody);
        }
    }

    /**
     * Transporte por defecto: curl nativo, sin dependencias.
     *
     * @param array<string, string> $headers
     * @return array{0: int, 1: array<string, string>, 2: string}
     */
    public static function defaultTransport(string $method, string $url, array $headers, ?string $body, float $timeout): array
    {
        $curlHeaders = [];
        foreach ($headers as $name => $value) {
            $curlHeaders[] = "{$name}: {$value}";
        }

        $ch = curl_init($url);
        if ($ch === false) {
            throw new YoFacturoException('No se pudo inicializar curl');
        }

        $options = [
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => $curlHeaders,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_TIMEOUT => (int) ceil($timeout),
        ];
        if ($body !== null) {
            $options[CURLOPT_POSTFIELDS] = $body;
        }
        curl_setopt_array($ch, $options);

        $response = curl_exec($ch);
        if ($response === false || !is_string($response)) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new YoFacturoException("No se pudo conectar con la API de YoFacturo: {$error}");
        }

        $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $headerSize = (int) curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        curl_close($ch);

        $rawHeaders = substr($response, 0, $headerSize);
        $rawBody = substr($response, $headerSize);

        $responseHeaders = [];
        foreach (explode("\r\n", $rawHeaders) as $line) {
            $separator = strpos($line, ':');
            if ($separator !== false) {
                $name = trim(substr($line, 0, $separator));
                $value = trim(substr($line, $separator + 1));
                $responseHeaders[$name] = $value;
            }
        }

        return [$status, $responseHeaders, $rawBody];
    }
}
