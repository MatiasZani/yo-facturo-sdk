<?php

declare(strict_types=1);

namespace YoFacturo\Exceptions;

// Alias real (no una subclase) de `ScopeException`, para paridad con el
// nombre que usan otros SDKs. Mismo caso: 403 Forbidden.
class_alias(ScopeException::class, __NAMESPACE__ . '\\PermissionException');
