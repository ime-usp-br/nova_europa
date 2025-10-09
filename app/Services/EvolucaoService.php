<?php

namespace App\Services;

use App\DTOs\EvolucaoDTO;
use App\Exceptions\ReplicadoServiceException;
use App\Models\Bloco;
use App\Models\Trilha;
use App\Models\User;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Log;

/**
 * Service for processing student academic evolution.
 *
 * This service orchestrates the complex business logic for calculating
 * student progress against curriculum requirements, including:
 * - Course classification (Mandatory/Elective/Free/Extra-curricular)
 * - Equivalence rules processing
 * - Course-specific validations (Blocos for 45024, Trilhas for 45052)
 * - Internship semester calculation
 */
class EvolucaoService
{
    public function __construct(
        private ReplicadoService $replicadoService
    ) {}

    /**
     * Process student evolution against curriculum requirements.
     *
     * This is the main orchestration method that coordinates all business logic
     * for calculating student academic progress.
     *
     * @param  User  $aluno  The student
     * @param  string  $codcrl  Curriculum code to process against
     * @return EvolucaoDTO Complete evolution data
     *
     * @throws ReplicadoServiceException When data cannot be fetched
     * @throws \Exception When processing fails
     */
    public function processarEvolucao(User $aluno, string $codcrl): EvolucaoDTO
    {
        try {
            if ($aluno->codpes === null) {
                throw new \InvalidArgumentException(__('Student must have a valid codpes'));
            }

            Log::info(__('Processing student evolution'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
            ]);

            $alunoData = $this->replicadoService->buscarAluno($aluno->codpes);
            $curriculoData = $this->replicadoService->buscarGradeCurricular($codcrl);

            if ($alunoData['codpgm'] === null) {
                throw new \InvalidArgumentException(__('Student must have a valid program code'));
            }

            $historico = $this->replicadoService->buscarHistorico($aluno->codpes, $alunoData['codpgm']);

            // DEBUG: Check if codtur is present in raw historico data
            Log::info('Raw historico data from Replicado', [
                'total_records' => $historico->count(),
                'cursando_disciplines' => $historico->filter(fn($d) => $d['rstfim'] === null)->map(fn($d) => [
                    'coddis' => $d['coddis'],
                    'codtur' => $d['codtur'] ?? 'NULL',
                    'rstfim' => $d['rstfim'] ?? 'NULL',
                ])->toArray()
            ]);

            [
                'obrigatorias' => $disciplinasObrigatorias,
                'eletivas' => $disciplinasEletivas,
                'livres' => $disciplinasLivres,
                'extra_curriculares' => $disciplinasExtraCurriculares,
            ] = $this->classificarDisciplinas($historico, $curriculoData['disciplinas']);

            [
                'obrigatorias' => $disciplinasObrigatorias,
                'eletivas' => $disciplinasEletivas,
                'livres' => $disciplinasLivres,
                'extra_curriculares' => $disciplinasExtraCurriculares,
            ] = $this->processarEquivalencias(
                $disciplinasObrigatorias,
                $disciplinasEletivas,
                $disciplinasLivres,
                $disciplinasExtraCurriculares,
                $curriculoData['disciplinas'],
                $codcrl
            );

            $creditosObrigatorios = $this->calcularCreditos($disciplinasObrigatorias, $curriculoData, 'O');
            $creditosEletivos = $this->calcularCreditos($disciplinasEletivas, $curriculoData, 'C');
            $creditosLivres = $this->calcularCreditos($disciplinasLivres, $curriculoData, 'L');

            $porcentagensConsolidacao = $this->calcularPorcentagens(
                $creditosObrigatorios,
                $creditosEletivos,
                $creditosLivres
            );

            $semestreEstagio = $this->calcularSemestreEstagio(
                $creditosObrigatorios,
                $creditosEletivos,
                $creditosLivres,
                $curriculoData,
                $disciplinasObrigatorias
            );

            $blocos = null;
            $trilhas = null;

            if ($alunoData['codcur'] == 45024) {
                $blocos = $this->validarBlocos($codcrl, $historico);
            } elseif ($alunoData['codcur'] == 45052) {
                $trilhas = $this->validarTrilhas($codcrl, $historico);
            }

            Log::info(__('Student evolution processed successfully'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
            ]);

            // DEBUG: Check if codtur is preserved after classification
            $cursandoObrigatorias = $disciplinasObrigatorias->filter(fn($d) => $d['rstfim'] === null);
            Log::info('Cursando disciplines after classification', [
                'count' => $cursandoObrigatorias->count(),
                'disciplines' => $cursandoObrigatorias->map(fn($d) => [
                    'coddis' => $d['coddis'],
                    'codtur' => $d['codtur'] ?? 'NULL',
                    'rstfim' => $d['rstfim'] ?? 'NULL',
                ])->toArray()
            ]);

            // Organize mandatory courses by semester for grid display
            $disciplinasPorSemestre = $this->organizarDisciplinasPorSemestre(
                $disciplinasObrigatorias,
                $curriculoData['disciplinas']
            );

            return new EvolucaoDTO(
                aluno: [
                    'codpes' => $alunoData['codpes'],
                    'nompes' => $alunoData['nompes'],
                    'codcur' => $alunoData['codcur'],
                    'nomcur' => $alunoData['nomcur'],
                    'codhab' => $alunoData['codhab'],
                    'nomhab' => $alunoData['nomhab'],
                    'codpgm' => $alunoData['codpgm'],
                    'stapgm' => $alunoData['stapgm'],
                    'dtainivin' => $alunoData['dtainivin'],
                ],
                curriculo: [
                    'codcrl' => $codcrl,
                    'curriculo' => $curriculoData['curriculo'],
                    'disciplinas' => $curriculoData['disciplinas'],
                ],
                disciplinasObrigatorias: $disciplinasObrigatorias,
                disciplinasEletivas: $disciplinasEletivas,
                disciplinasLivres: $disciplinasLivres,
                disciplinasExtraCurriculares: $disciplinasExtraCurriculares,
                disciplinasPorSemestre: $disciplinasPorSemestre,
                creditosObrigatorios: $creditosObrigatorios,
                creditosEletivos: $creditosEletivos,
                creditosLivres: $creditosLivres,
                porcentagensConsolidacao: $porcentagensConsolidacao,
                semestreEstagio: $semestreEstagio,
                blocos: $blocos,
                trilhas: $trilhas,
            );
        } catch (ReplicadoServiceException $e) {
            Log::error(__('Replicado error processing evolution'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
                'error' => $e->getMessage(),
            ]);

            throw $e;
        } catch (\Exception $e) {
            Log::error(__('Error processing student evolution'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            throw new \Exception(__('Failed to process student evolution: :message', ['message' => $e->getMessage()]), 0, $e);
        }
    }

    /**
     * Classify disciplines into categories based on curriculum.
     *
     * Compares student's academic history against curriculum structure
     * to classify each course as Mandatory (O), Elective (C), Free (L),
     * or Extra-curricular.
     *
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretrb: int}>  $historico
     * @param  Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>  $gradeCurricular
     * @return array{obrigatorias: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>, eletivas: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>, livres: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>, extra_curriculares: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}>}
     */
    private function classificarDisciplinas(Collection $historico, Collection $gradeCurricular): array
    {
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}> $disciplinasObrigatorias */
        $disciplinasObrigatorias = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}> $disciplinasEletivas */
        $disciplinasEletivas = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}> $disciplinasLivres */
        $disciplinasLivres = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null, codtur: string, discrl: string, stamtr: string}> $disciplinasExtraCurriculares */
        $disciplinasExtraCurriculares = collect();

        foreach ($historico as $cursada) {
            // Filter only relevant statuses for PDF (A, D, MA, EQ*)
            if (! $this->isStatusRelevante($cursada['rstfim'])) {
                continue;
            }

            $disciplinaGrade = $gradeCurricular->first(function ($disc) use ($cursada) {
                return $disc['coddis'] === $cursada['coddis'] && $disc['verdis'] === $cursada['verdis'];
            });

            if ($disciplinaGrade) {
                $disciplinaProcessada = [
                    'coddis' => (string) $cursada['coddis'],
                    'verdis' => (int) $cursada['verdis'],
                    'nomdis' => (string) $cursada['nomdis'],
                    'creaul' => (int) $cursada['creaul'],
                    'cretrb' => (int) $cursada['cretrb'],
                    'rstfim' => (string) $cursada['rstfim'],
                    'notfim' => $cursada['notfim'] !== null ? (float) $cursada['notfim'] : null,
                    'codtur' => (string) ($cursada['codtur'] ?? ''),
                    'discrl' => (string) ($cursada['discrl'] ?? ''),
                    'stamtr' => (string) ($cursada['stamtr'] ?? ''),
                ];

                switch ($disciplinaGrade['tipobg']) {
                    case 'O':
                        $disciplinasObrigatorias->push($disciplinaProcessada);
                        break;
                    case 'C':
                        $disciplinasEletivas->push($disciplinaProcessada);
                        break;
                    case 'L':
                        $disciplinasLivres->push($disciplinaProcessada);
                        break;
                }
            } else {
                $disciplinasExtraCurriculares->push([
                    'coddis' => (string) $cursada['coddis'],
                    'verdis' => (int) $cursada['verdis'],
                    'nomdis' => (string) $cursada['nomdis'],
                    'creaul' => (int) $cursada['creaul'],
                    'cretrb' => (int) $cursada['cretrb'],
                    'rstfim' => (string) $cursada['rstfim'],
                    'notfim' => $cursada['notfim'] !== null ? (float) $cursada['notfim'] : null,
                    'codtur' => (string) ($cursada['codtur'] ?? ''),
                    'discrl' => (string) ($cursada['discrl'] ?? ''),
                    'stamtr' => (string) ($cursada['stamtr'] ?? ''),
                ]);
            }
        }

        return [
            'obrigatorias' => $disciplinasObrigatorias,
            'eletivas' => $disciplinasEletivas,
            'livres' => $disciplinasLivres,
            'extra_curriculares' => $disciplinasExtraCurriculares,
        ];
    }

    /**
     * Process equivalence rules to promote extra-curricular courses.
     *
     * Attempts to promote extra-curricular courses to their appropriate
     * categories if they fulfill equivalence requirements.
     *
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinasObrigatorias
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinasEletivas
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinasLivres
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinasExtraCurriculares
     * @param  Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>  $gradeCurricular
     * @return array{obrigatorias: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>, eletivas: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>, livres: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>, extra_curriculares: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>}
     */
    private function processarEquivalencias(
        Collection $disciplinasObrigatorias,
        Collection $disciplinasEletivas,
        Collection $disciplinasLivres,
        Collection $disciplinasExtraCurriculares,
        Collection $gradeCurricular,
        string $codcrl
    ): array {
        $disciplinasUsadas = collect();

        foreach ($gradeCurricular as $disciplinaGrade) {
            $jaCursada = $disciplinasObrigatorias->contains('coddis', $disciplinaGrade['coddis'])
                || $disciplinasEletivas->contains('coddis', $disciplinaGrade['coddis'])
                || $disciplinasLivres->contains('coddis', $disciplinaGrade['coddis']);

            if ($jaCursada) {
                continue;
            }

            try {
                $equivalencias = $this->replicadoService->buscarEquivalencias(
                    $disciplinaGrade['coddis'],
                    $codcrl
                );

                foreach ($equivalencias as $grupo) {
                    $disciplinasEquivalentes = $grupo['disciplinas_equivalentes'];

                    $todasCumpridas = $disciplinasEquivalentes->every(function ($discEquiv) use ($disciplinasExtraCurriculares) {
                        return $disciplinasExtraCurriculares->contains(function ($cursada) use ($discEquiv) {
                            return $cursada['coddis'] === $discEquiv['coddis']
                                && $cursada['verdis'] === $discEquiv['verdis'];
                        });
                    });

                    if ($todasCumpridas) {
                        $disciplinaPromovida = [
                            'coddis' => $disciplinaGrade['coddis'],
                            'verdis' => $disciplinaGrade['verdis'],
                            'nomdis' => $disciplinaGrade['nomdis'],
                            'creaul' => $disciplinaGrade['creaul'],
                            'cretrb' => $disciplinaGrade['cretrb'],
                            'rstfim' => 'EQUIVALENTE',
                            'notfim' => null,
                        ];

                        switch ($disciplinaGrade['tipobg']) {
                            case 'O':
                                $disciplinasObrigatorias->push($disciplinaPromovida);
                                break;
                            case 'C':
                                $disciplinasEletivas->push($disciplinaPromovida);
                                break;
                            case 'L':
                                $disciplinasLivres->push($disciplinaPromovida);
                                break;
                        }

                        foreach ($disciplinasEquivalentes as $discEquiv) {
                            $disciplinasUsadas->push([
                                'coddis' => $discEquiv['coddis'],
                                'verdis' => $discEquiv['verdis'],
                            ]);
                        }

                        break;
                    }
                }
            } catch (ReplicadoServiceException $e) {
                Log::warning(__('Error checking equivalences'), [
                    'coddis' => $disciplinaGrade['coddis'],
                    'error' => $e->getMessage(),
                ]);
            }
        }

        $disciplinasExtraCurriculares = $disciplinasExtraCurriculares->reject(
            /** @param array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null} $cursada */
            function (array $cursada) use ($disciplinasUsadas) {
                $coddis = $cursada['coddis'];
                $verdis = $cursada['verdis'];

                return $disciplinasUsadas->contains(function (array $usada) use ($coddis, $verdis) {
                    /** @var array{coddis: string, verdis: int} $usada */
                    return $usada['coddis'] === $coddis && $usada['verdis'] === $verdis;
                });
            }
        );

        return [
            'obrigatorias' => $disciplinasObrigatorias,
            'eletivas' => $disciplinasEletivas,
            'livres' => $disciplinasLivres,
            'extra_curriculares' => $disciplinasExtraCurriculares,
        ];
    }

    /**
     * Calculate credits for a discipline category.
     *
     * Converts carga horária (course load hours) to credits using the formula from the legacy system:
     * - Créditos Aula = Carga Horária Aula ÷ 15
     * - Créditos Trabalho = Carga Horária Trabalho ÷ 30
     *
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinas
     * @param  array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>}  $curriculoData
     * @param  string  $tipo  'O', 'C', or 'L'
     * @return array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}
     */
    private function calcularCreditos(Collection $disciplinas, array $curriculoData, string $tipo): array
    {
        $sumAula = $disciplinas->sum('creaul');
        $creditosAula = is_numeric($sumAula) ? (int) $sumAula : 0;

        $sumTrabalho = $disciplinas->sum('cretrb');
        $creditosTrabalho = is_numeric($sumTrabalho) ? (int) $sumTrabalho : 0;

        $curriculo = $curriculoData['curriculo'];

        // Converte carga horária em créditos (Sistema legado: aula/15, trabalho/30)
        $cargaHorariaAula = match ($tipo) {
            'O' => is_numeric($curriculo['cgahorobgaul'] ?? 0) ? (int) ($curriculo['cgahorobgaul'] ?? 0) : 0,
            'C' => is_numeric($curriculo['cgaoptcplaul'] ?? 0) ? (int) ($curriculo['cgaoptcplaul'] ?? 0) : 0,
            'L' => is_numeric($curriculo['cgaoptlreaul'] ?? 0) ? (int) ($curriculo['cgaoptlreaul'] ?? 0) : 0,
            default => 0,
        };

        $cargaHorariaTrabalho = match ($tipo) {
            'O' => is_numeric($curriculo['cgahorobgtrb'] ?? 0) ? (int) ($curriculo['cgahorobgtrb'] ?? 0) : 0,
            'C' => is_numeric($curriculo['cgaoptcpltrb'] ?? 0) ? (int) ($curriculo['cgaoptcpltrb'] ?? 0) : 0,
            'L' => is_numeric($curriculo['cgaoptlretrb'] ?? 0) ? (int) ($curriculo['cgaoptlretrb'] ?? 0) : 0,
            default => 0,
        };

        $exigidosAula = $cargaHorariaAula > 0 ? (int) ($cargaHorariaAula / 15) : 0;
        $exigidosTrabalho = $cargaHorariaTrabalho > 0 ? (int) ($cargaHorariaTrabalho / 30) : 0;

        return [
            'aula' => $creditosAula,
            'trabalho' => $creditosTrabalho,
            'exigidos_aula' => $exigidosAula,
            'exigidos_trabalho' => $exigidosTrabalho,
        ];
    }

    /**
     * Calculate completion percentages.
     *
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosObrigatorios
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosEletivos
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosLivres
     * @return array{obrigatorios: float, eletivos: float, livres: float, total: float}
     */
    private function calcularPorcentagens(array $creditosObrigatorios, array $creditosEletivos, array $creditosLivres): array
    {
        $totalObrigatorios = $creditosObrigatorios['aula'] + $creditosObrigatorios['trabalho'];
        $exigidosTotalObrigatorios = $creditosObrigatorios['exigidos_aula'] + $creditosObrigatorios['exigidos_trabalho'];
        $percObrigatorios = $exigidosTotalObrigatorios > 0
            ? ($totalObrigatorios / $exigidosTotalObrigatorios) * 100
            : 0;

        $totalEletivos = $creditosEletivos['aula'] + $creditosEletivos['trabalho'];
        $exigidosTotalEletivos = $creditosEletivos['exigidos_aula'] + $creditosEletivos['exigidos_trabalho'];
        $percEletivos = $exigidosTotalEletivos > 0
            ? ($totalEletivos / $exigidosTotalEletivos) * 100
            : 0;

        $totalLivres = $creditosLivres['aula'] + $creditosLivres['trabalho'];
        $exigidosTotalLivres = $creditosLivres['exigidos_aula'] + $creditosLivres['exigidos_trabalho'];
        $percLivres = $exigidosTotalLivres > 0
            ? ($totalLivres / $exigidosTotalLivres) * 100
            : 0;

        $totalConcluidos = $totalObrigatorios + $totalEletivos + $totalLivres;
        $totalExigidos = $exigidosTotalObrigatorios + $exigidosTotalEletivos + $exigidosTotalLivres;

        $percTotal = $totalExigidos > 0 ? ($totalConcluidos / $totalExigidos) * 100 : 0;

        return [
            'obrigatorios' => round($percObrigatorios, 2),
            'eletivos' => round($percEletivos, 2),
            'livres' => round($percLivres, 2),
            'total' => round($percTotal, 2),
        ];
    }

    /**
     * Calculate internship semester based on credit completion and enrollment status.
     *
     * Implements the complex business rules for determining eligibility semester
     * for internship, which may differ from the standard calculated semester.
     *
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosObrigatorios
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosEletivos
     * @param  array{aula: int, trabalho: int, exigidos_aula: int, exigidos_trabalho: int}  $creditosLivres
     * @param  array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>}  $curriculoData
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretrb: int, rstfim: string, notfim: float|null}>  $disciplinasObrigatorias
     */
    private function calcularSemestreEstagio(
        array $creditosObrigatorios,
        array $creditosEletivos,
        array $creditosLivres,
        array $curriculoData,
        Collection $disciplinasObrigatorias
    ): int {
        $totalConcluidos = ($creditosObrigatorios['aula'] + $creditosObrigatorios['trabalho'])
            + ($creditosEletivos['aula'] + $creditosEletivos['trabalho'])
            + ($creditosLivres['aula'] + $creditosLivres['trabalho']);

        $totalExigidos = ($creditosObrigatorios['exigidos_aula'] + $creditosObrigatorios['exigidos_trabalho'])
            + ($creditosEletivos['exigidos_aula'] + $creditosEletivos['exigidos_trabalho'])
            + ($creditosLivres['exigidos_aula'] + $creditosLivres['exigidos_trabalho']);

        if ($totalExigidos === 0) {
            return 1;
        }

        $curriculo = $curriculoData['curriculo'];
        $duracaoIdealValue = $curriculo['duridlcur'] ?? 10;
        $duracaoIdeal = is_numeric($duracaoIdealValue) ? (int) $duracaoIdealValue : 10;
        $semestreBase = (int) floor((($totalConcluidos / $totalExigidos) * $duracaoIdeal) + 1);
        $semestreBase = (int) min($semestreBase, $duracaoIdeal);

        $progresso = $semestreBase / $duracaoIdeal;

        if ($progresso >= 0.875) {
            $semestreAtual = (int) date('n') <= 6 ? 1 : 2;

            $disciplinasObrigatoriasFaltantes = $curriculoData['disciplinas']
                ->filter(fn ($disc) => $disc['tipobg'] === 'O')
                ->reject(function ($disc) use ($disciplinasObrigatorias) {
                    return $disciplinasObrigatorias->contains(function ($cursada) use ($disc) {
                        return $cursada['coddis'] === $disc['coddis'];
                    });
                });

            $temMatriculaApropriada = $disciplinasObrigatoriasFaltantes->isEmpty();

            if ($semestreAtual === 1) {
                $temObrigatoriaImpar = $disciplinasObrigatoriasFaltantes->contains(fn ($disc) => $disc['numsemidl'] % 2 === 1);
                if (! $temObrigatoriaImpar || $temMatriculaApropriada) {
                    $semestreBase--;
                }
            } else {
                $temObrigatoriaPar = $disciplinasObrigatoriasFaltantes->contains(fn ($disc) => $disc['numsemidl'] % 2 === 0);
                if (! $temObrigatoriaPar || $temMatriculaApropriada) {
                    $semestreBase--;
                }
            }

            if ($semestreBase === $duracaoIdeal && ! $disciplinasObrigatoriasFaltantes->isEmpty()) {
                $semestreBase--;
            }
        }

        return (int) max($semestreBase, 1);
    }

    /**
     * Validate Blocos requirements for Licenciatura em Matemática (45024).
     *
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretrb: int}>  $historico
     * @return Collection<int, array{bloco_id: int, nome: string, creditos_obtidos: array{aula: int, trabalho: int}, creditos_exigidos: array{aula: int, trabalho: int}, disciplinas_cursadas: Collection<int, array{coddis: string, nomdis: string, creaul: int, cretrb: int}>}>
     */
    private function validarBlocos(string $codcrl, Collection $historico): Collection
    {
        $blocos = Bloco::where('codcrl', $codcrl)
            ->with('disciplinas')
            ->get();

        return $blocos->map(function ($bloco) use ($historico) {
            /** @var Collection<int, array{coddis: string, nomdis: string, creaul: int, cretrb: int}> $disciplinasCursadas */
            $disciplinasCursadas = collect();
            $creditosAula = 0;
            $creditosTrabalho = 0;

            foreach ($bloco->disciplinas as $blocoDisciplina) {
                $cursada = $historico->first(function ($hist) use ($blocoDisciplina) {
                    return $hist['coddis'] === $blocoDisciplina->coddis
                        && in_array($hist['rstfim'], ['A', 'D'], true);
                });

                if ($cursada) {
                    $disciplinasCursadas->push([
                        'coddis' => (string) $cursada['coddis'],
                        'nomdis' => (string) $cursada['nomdis'],
                        'creaul' => (int) $cursada['creaul'],
                        'cretrb' => (int) $cursada['cretrb'],
                    ]);

                    $creditosAula += (int) $cursada['creaul'];
                    $creditosTrabalho += (int) $cursada['cretrb'];
                }
            }

            return [
                'bloco_id' => $bloco->id,
                'nome' => $bloco->nome,
                'creditos_obtidos' => [
                    'aula' => $creditosAula,
                    'trabalho' => $creditosTrabalho,
                ],
                'creditos_exigidos' => [
                    'aula' => $bloco->creditos_aula_exigidos ?? 0,
                    'trabalho' => $bloco->creditos_trabalho_exigidos ?? 0,
                ],
                'disciplinas_cursadas' => $disciplinasCursadas,
            ];
        });
    }

    /**
     * Validate Trilhas requirements for Ciência da Computação (45052).
     *
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretrb: int}>  $historico
     * @return Collection<int, array{trilha_id: int, nome: string, nucleo_cumprido: bool, trilha_completa: bool, disciplinas_cursadas: Collection<int, array{coddis: string, nomdis: string, tipo: string, regra: string}>, regras_cumpridas: Collection<int, array{regra_id: int, nome_regra: string, num_exigidas: int, num_cumpridas: int, cumprida: bool}>}>
     */
    private function validarTrilhas(string $codcrl, Collection $historico): Collection
    {
        $trilhas = Trilha::where('codcrl', $codcrl)
            ->with(['regras.disciplinas'])
            ->get();

        return $trilhas->map(function ($trilha) use ($historico) {
            /** @var Collection<int, array{coddis: string, nomdis: string, tipo: string, regra: string}> $disciplinasCursadas */
            $disciplinasCursadas = collect();
            /** @var Collection<int, array{regra_id: int, nome_regra: string, num_exigidas: int, num_cumpridas: int, cumprida: bool}> $regrasCumpridas */
            $regrasCumpridas = collect();

            foreach ($trilha->regras as $regra) {
                $disciplinasRegraCompletas = 0;

                foreach ($regra->disciplinas as $trilhaDisciplina) {
                    $cursada = $historico->first(function ($hist) use ($trilhaDisciplina) {
                        return $hist['coddis'] === $trilhaDisciplina->coddis
                            && in_array($hist['rstfim'], ['A', 'D'], true);
                    });

                    if ($cursada) {
                        $disciplinasCursadas->push([
                            'coddis' => (string) $cursada['coddis'],
                            'nomdis' => (string) $cursada['nomdis'],
                            'tipo' => (string) $trilhaDisciplina->tipo,
                            'regra' => (string) $regra->nome_regra,
                        ]);

                        $disciplinasRegraCompletas++;
                    }
                }

                $regraCumprida = $disciplinasRegraCompletas >= $regra->num_disciplinas_exigidas;

                $regrasCumpridas->push([
                    'regra_id' => $regra->id,
                    'nome_regra' => $regra->nome_regra,
                    'num_exigidas' => $regra->num_disciplinas_exigidas,
                    'num_cumpridas' => $disciplinasRegraCompletas,
                    'cumprida' => $regraCumprida,
                ]);
            }

            $primeiraRegra = $regrasCumpridas->first();
            $nucleoCumprido = $primeiraRegra !== null && $primeiraRegra['cumprida'];
            $trilhaCompleta = $regrasCumpridas->every(fn ($regra) => $regra['cumprida']);

            return [
                'trilha_id' => $trilha->id,
                'nome' => $trilha->nome,
                'nucleo_cumprido' => $nucleoCumprido,
                'trilha_completa' => $trilhaCompleta,
                'disciplinas_cursadas' => $disciplinasCursadas,
                'regras_cumpridas' => $regrasCumpridas,
            ];
        });
    }

    /**
     * Organize mandatory courses by ideal semester for grid display.
     *
     * Creates an array indexed by semester number (1-8+), where each semester
     * contains the courses that should be taken in that semester according to
     * the curriculum structure.
     *
     * @param  Collection  $disciplinasCursadas  Completed mandatory courses
     * @param  Collection  $disciplinasGrade  All curriculum courses with semester info
     * @return array<int, Collection> Array indexed by semester number
     */
    private function organizarDisciplinasPorSemestre(Collection $disciplinasCursadas, Collection $disciplinasGrade): array
    {
        // Filter only mandatory courses from curriculum
        $disciplinasObrigatoriasGrade = $disciplinasGrade->where('tipobg', 'O');

        // Create a map of completed courses by coddis+verdis for quick lookup
        $cursadasMap = $disciplinasCursadas->keyBy(fn ($disc) => $disc['coddis'].'_'.$disc['verdis']);

        // Initialize array for semesters 1-8 (most common case)
        $porSemestre = [];
        for ($i = 1; $i <= 8; $i++) {
            $porSemestre[$i] = collect();
        }

        // Iterate over curriculum (not over completed courses) to include pending courses
        foreach ($disciplinasObrigatoriasGrade as $discGrade) {
            $semestre = (int) $discGrade['numsemidl'];

            // Extend array if course is in semester > 8
            if ($semestre > 8 && ! isset($porSemestre[$semestre])) {
                $porSemestre[$semestre] = collect();
            }

            if ($semestre >= 1) {
                // Check if course was completed
                $chave = $discGrade['coddis'].'_'.$discGrade['verdis'];
                $cursada = $cursadasMap->get($chave);

                if ($cursada) {
                    // Completed course - add with all data
                    $porSemestre[$semestre]->push($cursada);
                } else {
                    // Pending course - add with rstfim = null
                    $porSemestre[$semestre]->push([
                        'coddis' => $discGrade['coddis'],
                        'verdis' => $discGrade['verdis'],
                        'nomdis' => $discGrade['nomdis'],
                        'creaul' => $discGrade['creaul'],
                        'cretrb' => $discGrade['cretrb'],
                        'rstfim' => null,
                        'notfim' => null,
                        'codtur' => null,
                        'discrl' => null,
                        'stamtr' => null,
                    ]);
                }
            }
        }

        return $porSemestre;
    }

    /**
     * Check if a course status is relevant for PDF display.
     *
     * Accepts:
     * - null: Currently enrolled courses (rstfim not yet assigned)
     * - A: Approved
     * - D: Waived (Aproveitamento de Estudos)
     * - MA: Enrolled (if present in database)
     * - EQ*: Equivalences
     *
     * Excludes: R, RN, RF (failed), T (withdrawn), etc.
     *
     * @param  string|null  $rstfim  Course completion status
     */
    private function isStatusRelevante(?string $rstfim): bool
    {
        // Accept null (currently enrolled) along with approved, waived, and equivalences
        return $rstfim === null
            || in_array($rstfim, ['A', 'D', 'MA'], true)
            || str_starts_with((string) $rstfim, 'EQ');
    }
}