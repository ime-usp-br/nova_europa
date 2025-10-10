<?php

namespace Tests\Feature;

use App\Models\Trilha;
use App\Models\TrilhaDisciplina;
use App\Models\TrilhaRegra;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TrilhaDatabaseTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Test that a Trilha can be created in the database.
     */
    public function test_trilha_can_be_created_in_database(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $this->assertDatabaseHas('trilhas', [
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $this->assertInstanceOf(Trilha::class, $trilha);
        $this->assertTrue($trilha->exists);
    }

    /**
     * Test that TrilhaRegra can be associated with a Trilha.
     */
    public function test_trilha_regra_can_be_associated_with_trilha(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $regra = TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        $this->assertDatabaseHas('trilha_regras', [
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        $this->assertEquals($trilha->id, $regra->trilha_id);
    }

    /**
     * Test that TrilhaDisciplina can be associated with a TrilhaRegra.
     */
    public function test_trilha_disciplina_can_be_associated_with_regra(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $regra = TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        $disciplina = TrilhaDisciplina::create([
            'regra_id' => $regra->id,
            'coddis' => 'MAC0460',
            'tipo' => 'obrigatoria',
        ]);

        $this->assertDatabaseHas('trilha_disciplinas', [
            'regra_id' => $regra->id,
            'coddis' => 'MAC0460',
            'tipo' => 'obrigatoria',
        ]);

        $this->assertEquals($regra->id, $disciplina->regra_id);
    }

    /**
     * Test that Trilha can retrieve its associated regras through relationship.
     */
    public function test_trilha_can_retrieve_associated_regras(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Eletivas da Trilha',
            'num_disciplinas_exigidas' => 2,
        ]);

        $trilha->refresh();

        $this->assertCount(2, $trilha->regras);
        $this->assertEquals('Núcleo da Trilha', $trilha->regras[0]->nome_regra);
        $this->assertEquals('Eletivas da Trilha', $trilha->regras[1]->nome_regra);
    }

    /**
     * Test that TrilhaRegra can retrieve its associated disciplinas.
     */
    public function test_trilha_regra_can_retrieve_associated_disciplinas(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $regra = TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        TrilhaDisciplina::create([
            'regra_id' => $regra->id,
            'coddis' => 'MAC0460',
            'tipo' => 'obrigatoria',
        ]);

        TrilhaDisciplina::create([
            'regra_id' => $regra->id,
            'coddis' => 'MAC0499',
            'tipo' => 'eletiva',
        ]);

        $regra->refresh();

        $this->assertCount(2, $regra->disciplinas);
        $this->assertEquals('MAC0460', $regra->disciplinas[0]->coddis);
        $this->assertEquals('obrigatoria', $regra->disciplinas[0]->tipo);
        $this->assertEquals('MAC0499', $regra->disciplinas[1]->coddis);
        $this->assertEquals('eletiva', $regra->disciplinas[1]->tipo);
    }

    /**
     * Test that deleting a Trilha cascades to its regras and disciplinas.
     */
    public function test_deleting_trilha_cascades_to_regras_and_disciplinas(): void
    {
        $trilha = Trilha::create([
            'nome' => 'Ciência de Dados',
            'codcur' => '45052',
        ]);

        $regra = TrilhaRegra::create([
            'trilha_id' => $trilha->id,
            'nome_regra' => 'Núcleo da Trilha',
            'num_disciplinas_exigidas' => 5,
        ]);

        $disciplina = TrilhaDisciplina::create([
            'regra_id' => $regra->id,
            'coddis' => 'MAC0460',
            'tipo' => 'obrigatoria',
        ]);

        $this->assertDatabaseHas('trilha_regras', ['id' => $regra->id]);
        $this->assertDatabaseHas('trilha_disciplinas', ['id' => $disciplina->id]);

        $trilha->delete();

        $this->assertDatabaseMissing('trilhas', ['id' => $trilha->id]);
        $this->assertDatabaseMissing('trilha_regras', ['id' => $regra->id]);
        $this->assertDatabaseMissing('trilha_disciplinas', ['id' => $disciplina->id]);
    }
}
