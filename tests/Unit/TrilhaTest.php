<?php

namespace Tests\Unit;

use App\Models\Trilha;
use App\Models\TrilhaRegra;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Tests\TestCase;

class TrilhaTest extends TestCase
{
    /**
     * Test that Trilha has fillable attributes defined.
     */
    public function test_trilha_has_fillable_attributes(): void
    {
        $trilha = new Trilha;

        $expected = [
            'nome',
            'codcrl',
        ];

        $this->assertEquals($expected, $trilha->getFillable());
    }

    /**
     * Test that Trilha has a hasMany relationship with TrilhaRegra.
     */
    public function test_trilha_has_many_regras_relationship(): void
    {
        $trilha = new Trilha;

        $relation = $trilha->regras();

        $this->assertInstanceOf(HasMany::class, $relation);
        $this->assertInstanceOf(TrilhaRegra::class, $relation->getRelated());
    }

    /**
     * Test that Trilha can be instantiated.
     */
    public function test_trilha_can_be_instantiated(): void
    {
        $trilha = new Trilha([
            'nome' => 'Ciência de Dados',
            'codcrl' => '45052',
        ]);

        $this->assertInstanceOf(Trilha::class, $trilha);
        $this->assertEquals('Ciência de Dados', $trilha->nome);
        $this->assertEquals('45052', $trilha->codcrl);
    }
}
