<?php

namespace Tests\Feature;

use App\Models\Bloco;
use App\Models\BlocoDisciplina;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class BlocoDatabaseTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Test that a Bloco can be created in the database.
     */
    public function test_bloco_can_be_created_in_database(): void
    {
        $bloco = Bloco::create([
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        $this->assertDatabaseHas('blocos', [
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        $this->assertInstanceOf(Bloco::class, $bloco);
        $this->assertTrue($bloco->exists);
    }

    /**
     * Test that BlocoDisciplina can be associated with a Bloco.
     */
    public function test_bloco_disciplina_can_be_associated_with_bloco(): void
    {
        $bloco = Bloco::create([
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        $disciplina = BlocoDisciplina::create([
            'bloco_id' => $bloco->id,
            'coddis' => 'EDF0290',
        ]);

        $this->assertDatabaseHas('bloco_disciplinas', [
            'bloco_id' => $bloco->id,
            'coddis' => 'EDF0290',
        ]);

        $this->assertEquals($bloco->id, $disciplina->bloco_id);
    }

    /**
     * Test that Bloco can retrieve its associated disciplinas through relationship.
     */
    public function test_bloco_can_retrieve_associated_disciplinas(): void
    {
        $bloco = Bloco::create([
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        BlocoDisciplina::create([
            'bloco_id' => $bloco->id,
            'coddis' => 'EDF0290',
        ]);

        BlocoDisciplina::create([
            'bloco_id' => $bloco->id,
            'coddis' => 'EDF0285',
        ]);

        $bloco->refresh();

        $this->assertCount(2, $bloco->disciplinas);
        $this->assertEquals('EDF0290', $bloco->disciplinas[0]->coddis);
        $this->assertEquals('EDF0285', $bloco->disciplinas[1]->coddis);
    }

    /**
     * Test that deleting a Bloco cascades to its disciplinas.
     */
    public function test_deleting_bloco_cascades_to_disciplinas(): void
    {
        $bloco = Bloco::create([
            'nome' => 'Psicologia da Educação',
            'codcrl' => '45024',
            'creditos_aula_exigidos' => 8,
            'creditos_trabalho_exigidos' => 0,
            'num_disciplinas_exigidas' => 2,
        ]);

        $disciplina = BlocoDisciplina::create([
            'bloco_id' => $bloco->id,
            'coddis' => 'EDF0290',
        ]);

        $this->assertDatabaseHas('bloco_disciplinas', ['id' => $disciplina->id]);

        $bloco->delete();

        $this->assertDatabaseMissing('blocos', ['id' => $bloco->id]);
        $this->assertDatabaseMissing('bloco_disciplinas', ['id' => $disciplina->id]);
    }
}
