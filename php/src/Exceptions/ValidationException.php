<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

/**
 * 400/422: la petición está mal formada o no pasa las validaciones de negocio.
 *
 * Cuando la API devuelve un array `errors` con el detalle por campo, queda
 * disponible en `getErrors()`.
 */
class ValidationException extends ApiException
{
}
