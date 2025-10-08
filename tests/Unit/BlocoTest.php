<?php

namespace Tests\Unit;

use App\Models\Bloco;
use App\Models\BlocoDisciplina;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Tests\TestCase;

class BlocoTest extends TestCase
{
    /**
     * Test that Bloco has fillable attributes defined.
     */
    public function test_bloco_has_fillable_attributes(): void
    {
        $bloco = new Bloco;

        $expected = [
            'nome',
            'codcrl',
            'creditos_aula_exigidos',
            'creditos_trabalho_exigidos',
            'num_disciplinas_exigidas',
        ];

        $this->assertEquals($expected, $bloco->getFillable());
    }

    /**
     * Test that Bloco has a hasMany relationship with BlocoDisciplina.
     */
    public function test_bloco_has_many_disciplinas_relationship(): void
    {
        $bloco = new Bloco;

        $relation = $bloco->disciplinas();

        $this->assertInstanceOf(HasMany::class, $relation);
        $this->assertInstanceOf(BlocoDisciplina::class, $relation->getRelated());
    }

    /**
     * Test that Bloco can be instantiated.
     */
    public function test_bloco_can_be_instantiated(): void
    {
        $bloco = new Bloco([
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        $this->assertInstanceOf(Bloco::class, $bloco);
        $this->assertEquals('Psicologia da Educação', $bloco->nome);
        $this->assertEquals('45024', $bloco->codcrl);
        $this->assertEquals(8, $bloco->creditos_aula_exigidos);
        $this->assertEquals(0, $bloco->creditos_trabalho_exigidos);
        $this->assertEquals(2, $bloco->num_disciplinas_exigidas);
    }
}
