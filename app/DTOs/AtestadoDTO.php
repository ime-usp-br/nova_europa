<?php

namespace App\DTOs;

/**
 * Data Transfer Object for enrollment certificate data.
 */
class AtestadoDTO
{
    public function __construct(
        public int $codpes,
        public ?string $nompes,
        public ?string $tipdocidf,
        public ?string $numdocidf,
        public ?string $sglorgexdidf,
        public ?string $nomcur,
        public int $duridlcur
    ) {}
}
