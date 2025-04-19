<?php

namespace Tests;

use Illuminate\Foundation\Testing\LazilyRefreshDatabase;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    use LazilyRefreshDatabase;

    /**
     * Configura o ambiente de teste antes de cada teste na classe.
     *
     * Este método é chamado automaticamente pelo PHPUnit.
     * Aqui, desabilitamos o Vite para garantir que os testes PHPUnit/Feature
     * não dependam de assets compilados ou do servidor de desenvolvimento Vite.
     */
    protected function setUp(): void
    {
        parent::setUp();

        $this->withoutVite();
    }
}
