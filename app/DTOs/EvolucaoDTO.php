<?php

namespace App\DTOs;

use Illuminate\Support\Collection;

/**
 * Data Transfer Object for student evolution data.
 *
 * Encapsulates all processed student evolution information including
 * classified disciplines, credit calculations, course-specific validations,
 * and internship semester calculations.
 */
class EvolucaoDTO
{
    /**
     * @param  array{codpes: int, nompes: string|null, codcur: int|null, nomcur: string|null, codhab: int|null, nomhab: string|null, codpgm: int|null, stapgm: string|null, dtainivin: string|null}  $aluno  Student complete information
     * @param  array{codcrl: string, curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>}  $curriculo  Curriculum information
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>  $disciplinasObrigatorias  Mandatory courses completed
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>  $disciplinasEletivas  Elective courses completed
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>  $disciplinasLivres  Free choice courses completed
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>  $disciplinasExtraCurriculares  Extra-curricular courses
     * @param  array<int, Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string|null, notfim: float|null, codtur: string|null, discrl: string|null, stamtr: string|null}>>  $disciplinasPorSemestre  Mandatory courses organized by ideal semester
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosObrigatorios  Mandatory credits (completed and required, separated by type)
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosEletivos  Elective credits (completed and required, separated by type)
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosLivres  Free choice credits (completed and required, separated by type)
     * @param  array{obrigatorios: float, eletivos: float, livres: float, total: float}  $porcentagensConsolidacao  Completion percentages
     * @param  int  $semestreEstagio  Calculated internship semester
     * @param  Collection<int, array{bloco_id: int, nome: string, creditos_obtidos: array{aula: int, trabalho: int}, creditos_exigidos: array{aula: int, trabalho: int}, disciplinas_cursadas: Collection<int, array{coddis: string, nomdis: string, creaul: int, cretrb: int}>}>|null  $blocos  Blocos validation (45024 only)
     * @param  Collection<int, array{trilha_id: int, nome: string, nucleo_cumprido: bool, trilha_completa: bool, disciplinas_cursadas: Collection<int, array{coddis: string, nomdis: string, creaul: int, cretrb: int, codtur: string, rstfim: string, tipo: string, regra: string}>, regras_cumpridas: Collection<int, array{regra_id: int, nome_regra: string, num_exigidas: int, num_cumpridas: int, cumprida: bool}>}>|null  $trilhas  Trilhas validation (45052 only)
     */
    public function __construct(
        public array $aluno,
        public array $curriculo,
        public Collection $disciplinasObrigatorias,
        public Collection $disciplinasEletivas,
        public Collection $disciplinasLivres,
        public Collection $disciplinasExtraCurriculares,
        public array $disciplinasPorSemestre,
        public array $creditosObrigatorios,
        public array $creditosEletivos,
        public array $creditosLivres,
        public array $porcentagensConsolidacao,
        public int $semestreEstagio,
        public ?Collection $blocos = null,
        public ?Collection $trilhas = null,
    ) {}

    /**
     * Convert DTO to array for serialization.
     *
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'aluno' => $this->aluno,
            'curriculo' => [
                'codcrl' => $this->curriculo['codcrl'],
                'curriculo' => $this->curriculo['curriculo'],
                'total_disciplinas' => $this->curriculo['disciplinas']->count(),
            ],
            'disciplinas' => [
                'obrigatorias' => $this->disciplinasObrigatorias->toArray(),
                'eletivas' => $this->disciplinasEletivas->toArray(),
                'livres' => $this->disciplinasLivres->toArray(),
                'extra_curriculares' => $this->disciplinasExtraCurriculares->toArray(),
            ],
            'creditos' => [
                'obrigatorios' => $this->creditosObrigatorios,
                'eletivos' => $this->creditosEletivos,
                'livres' => $this->creditosLivres,
            ],
            'porcentagens' => $this->porcentagensConsolidacao,
            'semestre_estagio' => $this->semestreEstagio,
            'blocos' => $this->blocos?->toArray(),
            'trilhas' => $this->trilhas?->toArray(),
        ];
    }
}
