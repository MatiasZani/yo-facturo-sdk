<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

/**
 * 401 Unauthorized: falta el token, es inválido, fue revocado o expiró.
 */
class AuthenticationException extends ApiException
{
}
