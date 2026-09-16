<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

/**
 * 403 Forbidden: el plan no incluye la API, venció la suscripción o falta un scope.
 */
class ScopeException extends ApiException
{
}
