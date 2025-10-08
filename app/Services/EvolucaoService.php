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
            // Validate user has codpes
            if ($aluno->codpes === null) {
                throw new \InvalidArgumentException(__('Student must have a valid codpes'));
            }

            Log::info(__('Processing student evolution'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
            ]);

            // Fetch required data from Replicado
            $alunoData = $this->replicadoService->buscarAluno($aluno->codpes);
            $curriculoData = $this->replicadoService->buscarGradeCurricular($codcrl);

            // Validate course code
            if ($alunoData['codcur'] === null) {
                throw new \InvalidArgumentException(__('Student must have a valid course'));
            }

            $historico = $this->replicadoService->buscarHistorico($aluno->codpes, $alunoData['codcur']);

            // Filter only approved courses
            $historico = $historico->filter(fn ($curso) => in_array($curso['rstfim'], ['A', 'D']));

            // Step 1: Classify disciplines into categories
            [
                'obrigatorias' => $disciplinasObrigatorias,
                'eletivas' => $disciplinasEletivas,
                'livres' => $disciplinasLivres,
                'extra_curriculares' => $disciplinasExtraCurriculares,
            ] = $this->classificarDisciplinas($historico, $curriculoData['disciplinas']);

            // Step 2: Process equivalences to promote extra-curricular courses
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

            // Step 3: Calculate credits
            $creditosObrigatorios = $this->calcularCreditos($disciplinasObrigatorias, $curriculoData, 'O');
            $creditosEletivos = $this->calcularCreditos($disciplinasEletivas, $curriculoData, 'C');
            $creditosLivres = $this->calcularCreditos($disciplinasLivres, $curriculoData, 'L');

            // Step 4: Calculate completion percentages
            $porcentagensConsolidacao = $this->calcularPorcentagens(
                $creditosObrigatorios,
                $creditosEletivos,
                $creditosLivres
            );

            // Step 5: Calculate internship semester
            $semestreEstagio = $this->calcularSemestreEstagio(
                $creditosObrigatorios,
                $creditosEletivos,
                $creditosLivres,
                $curriculoData,
                $disciplinasObrigatorias
            );

            // Step 6: Course-specific validations
            $blocos = null;
            $trilhas = null;

            if ($alunoData['codcur'] == 45024) {
                // Licenciatura em Matemática: Validate Blocos
                $blocos = $this->validarBlocos($codcrl, $historico);
            } elseif ($alunoData['codcur'] == 45052) {
                // Ciência da Computação: Validate Trilhas
                $trilhas = $this->validarTrilhas($codcrl, $historico);
            }

            Log::info(__('Student evolution processed successfully'), [
                'codpes' => $aluno->codpes,
                'codcrl' => $codcrl,
            ]);

            return new EvolucaoDTO(
                aluno: [
                    'codpes' => $alunoData['codpes'],
                    'nompes' => $alunoData['nompes'],
                    'codcur' => $alunoData['codcur'],
                    'nomcur' => $alunoData['nomcur'],
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
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretra: int}>  $historico
     * @param  Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}>  $gradeCurricular
     * @return array{obrigatorias: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, eletivas: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, livres: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, extra_curriculares: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>}
     */
    private function classificarDisciplinas(Collection $historico, Collection $gradeCurricular): array
    {
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}> $disciplinasObrigatorias */
        $disciplinasObrigatorias = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}> $disciplinasEletivas */
        $disciplinasEletivas = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}> $disciplinasLivres */
        $disciplinasLivres = collect();
        /** @var Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}> $disciplinasExtraCurriculares */
        $disciplinasExtraCurriculares = collect();

        foreach ($historico as $cursada) {
            // Find discipline in curriculum
            $disciplinaGrade = $gradeCurricular->first(function ($disc) use ($cursada) {
                return $disc['coddis'] === $cursada['coddis'] && $disc['verdis'] === $cursada['verdis'];
            });

            if ($disciplinaGrade) {
                // Discipline exists in curriculum - classify by tipobg
                $disciplinaProcessada = [
                    'coddis' => (string) $cursada['coddis'],
                    'verdis' => (int) $cursada['verdis'],
                    'nomdis' => (string) $cursada['nomdis'],
                    'creaul' => (int) $cursada['creaul'],
                    'cretra' => (int) $cursada['cretra'],
                    'rstfim' => (string) $cursada['rstfim'],
                    'notfim' => $cursada['notfim'] !== null ? (float) $cursada['notfim'] : null,
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
                // Discipline not in curriculum - mark as extra-curricular (may be promoted later)
                $disciplinasExtraCurriculares->push([
                    'coddis' => (string) $cursada['coddis'],
                    'verdis' => (int) $cursada['verdis'],
                    'nomdis' => (string) $cursada['nomdis'],
                    'creaul' => (int) $cursada['creaul'],
                    'cretra' => (int) $cursada['cretra'],
                    'rstfim' => (string) $cursada['rstfim'],
                    'notfim' => $cursada['notfim'] !== null ? (float) $cursada['notfim'] : null,
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
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinasObrigatorias
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinasEletivas
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinasLivres
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinasExtraCurriculares
     * @param  Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}>  $gradeCurricular
     * @return array{obrigatorias: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, eletivas: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, livres: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>, extra_curriculares: Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>}
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
            // Skip if already completed directly
            $jaCursada = $disciplinasObrigatorias->contains('coddis', $disciplinaGrade['coddis'])
                || $disciplinasEletivas->contains('coddis', $disciplinaGrade['coddis'])
                || $disciplinasLivres->contains('coddis', $disciplinaGrade['coddis']);

            if ($jaCursada) {
                continue;
            }

            // Check for equivalences
            try {
                $equivalencias = $this->replicadoService->buscarEquivalencias(
                    $disciplinaGrade['coddis'],
                    $codcrl
                );

                foreach ($equivalencias as $grupo) {
                    $disciplinasEquivalentes = $grupo['disciplinas_equivalentes'];

                    // Check if student completed ALL disciplines in equivalence group
                    $todasCumpridas = $disciplinasEquivalentes->every(function ($discEquiv) use ($disciplinasExtraCurriculares) {
                        return $disciplinasExtraCurriculares->contains(function ($cursada) use ($discEquiv) {
                            return $cursada['coddis'] === $discEquiv['coddis']
                                && $cursada['verdis'] === $discEquiv['verdis'];
                        });
                    });

                    if ($todasCumpridas) {
                        // Promote target discipline with EQUIVALENTE status
                        $disciplinaPromovida = [
                            'coddis' => $disciplinaGrade['coddis'],
                            'verdis' => $disciplinaGrade['verdis'],
                            'nomdis' => $disciplinaGrade['nomdis'],
                            'creaul' => $disciplinaGrade['creaul'],
                            'cretra' => $disciplinaGrade['cretra'],
                            'rstfim' => 'EQUIVALENTE',
                            'notfim' => null,
                        ];

                        // Add to appropriate category
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

                        // Mark used disciplines for removal
                        foreach ($disciplinasEquivalentes as $discEquiv) {
                            $disciplinasUsadas->push([
                                'coddis' => $discEquiv['coddis'],
                                'verdis' => $discEquiv['verdis'],
                            ]);
                        }

                        break; // Stop checking other equivalence groups for this discipline
                    }
                }
            } catch (ReplicadoServiceException $e) {
                // Log but continue processing
                Log::warning(__('Error checking equivalences'), [
                    'coddis' => $disciplinaGrade['coddis'],
                    'error' => $e->getMessage(),
                ]);
            }
        }

        // Remove used disciplines from extra-curricular list
        $disciplinasExtraCurriculares = $disciplinasExtraCurriculares->reject(
            /** @param array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null} $cursada */
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
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinas
     * @param  array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}>}  $curriculoData
     * @param  string  $tipo  'O', 'C', or 'L'
     * @return array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}
     */
    private function calcularCreditos(Collection $disciplinas, array $curriculoData, string $tipo): array
    {
        // Sum returns numeric, safe to cast
        $sumAula = $disciplinas->sum('creaul');
        $creditosAula = is_numeric($sumAula) ? (int) $sumAula : 0;

        $sumTrabalho = $disciplinas->sum('cretra');
        $creditosTrabalho = is_numeric($sumTrabalho) ? (int) $sumTrabalho : 0;

        // Get required credits from curriculum
        $curriculo = $curriculoData['curriculo'];

        $exigidosAula = match ($tipo) {
            'O' => is_numeric($curriculo['numcredaulobg'] ?? 0) ? (int) ($curriculo['numcredaulobg'] ?? 0) : 0,
            'C' => is_numeric($curriculo['numcredaulopc'] ?? 0) ? (int) ($curriculo['numcredaulopc'] ?? 0) : 0,
            'L' => is_numeric($curriculo['numcredaulopt'] ?? 0) ? (int) ($curriculo['numcredaulopt'] ?? 0) : 0,
            default => 0,
        };

        $exigidosTrabalho = match ($tipo) {
            'C' => is_numeric($curriculo['numcredtrbopc'] ?? 0) ? (int) ($curriculo['numcredtrbopc'] ?? 0) : 0,
            default => 0,
        };

        return [
            'aula' => $creditosAula,
            'trabalho' => $creditosTrabalho,
            'total' => $creditosAula + $creditosTrabalho,
            'exigidos_aula' => $exigidosAula,
            'exigidos_trabalho' => $exigidosTrabalho,
            'exigidos_total' => $exigidosAula + $exigidosTrabalho,
        ];
    }

    /**
     * Calculate completion percentages.
     *
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosObrigatorios
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosEletivos
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosLivres
     * @return array{obrigatorios: float, eletivos: float, livres: float, total: float}
     */
    private function calcularPorcentagens(array $creditosObrigatorios, array $creditosEletivos, array $creditosLivres): array
    {
        $percObrigatorios = $creditosObrigatorios['exigidos_total'] > 0
            ? ($creditosObrigatorios['total'] / $creditosObrigatorios['exigidos_total']) * 100
            : 0;

        $percEletivos = $creditosEletivos['exigidos_total'] > 0
            ? ($creditosEletivos['total'] / $creditosEletivos['exigidos_total']) * 100
            : 0;

        $percLivres = $creditosLivres['exigidos_total'] > 0
            ? ($creditosLivres['total'] / $creditosLivres['exigidos_total']) * 100
            : 0;

        $totalConcluidos = $creditosObrigatorios['total'] + $creditosEletivos['total'] + $creditosLivres['total'];
        $totalExigidos = $creditosObrigatorios['exigidos_total'] + $creditosEletivos['exigidos_total'] + $creditosLivres['exigidos_total'];

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
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosObrigatorios
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosEletivos
     * @param  array{aula: int, trabalho: int, total: int, exigidos_aula: int, exigidos_trabalho: int, exigidos_total: int}  $creditosLivres
     * @param  array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}>}  $curriculoData
     * @param  Collection<int, array{coddis: string, verdis: int, nomdis: string, creaul: int, cretra: int, rstfim: string, notfim: float|null}>  $disciplinasObrigatorias
     */
    private function calcularSemestreEstagio(
        array $creditosObrigatorios,
        array $creditosEletivos,
        array $creditosLivres,
        array $curriculoData,
        Collection $disciplinasObrigatorias
    ): int {
        // Calculate base semester using credit completion ratio
        $totalConcluidos = $creditosObrigatorios['total'] + $creditosEletivos['total'] + $creditosLivres['total'];
        $totalExigidos = $creditosObrigatorios['exigidos_total'] + $creditosEletivos['exigidos_total'] + $creditosLivres['exigidos_total'];

        if ($totalExigidos === 0) {
            return 1;
        }

        $curriculo = $curriculoData['curriculo'];
        $duracaoIdealValue = $curriculo['numdiaintmax'] ?? 10;
        $duracaoIdeal = is_numeric($duracaoIdealValue) ? (int) $duracaoIdealValue : 10;
        $semestreBase = (int) floor((($totalConcluidos / $totalExigidos) * $duracaoIdeal) + 1);
        $semestreBase = (int) min($semestreBase, $duracaoIdeal);

        // Calculate progress percentage
        $progresso = $semestreBase / $duracaoIdeal;

        // Apply adjustment rules if progress >= 87.5%
        if ($progresso >= 0.875) {
            $semestreAtual = (int) date('n') <= 6 ? 1 : 2; // 1 = first semester, 2 = second semester

            // Get mandatory courses from curriculum that haven't been completed
            $disciplinasObrigatoriasFaltantes = $curriculoData['disciplinas']
                ->filter(fn ($disc) => $disc['tipobg'] === 'O')
                ->reject(function ($disc) use ($disciplinasObrigatorias) {
                    return $disciplinasObrigatorias->contains(function ($cursada) use ($disc) {
                        return $cursada['coddis'] === $disc['coddis'];
                    });
                });

            // Check enrollment in semester-appropriate mandatory courses
            // Note: This is a simplified implementation. Real implementation would need
            // to check actual enrollment (MATRICULA table) and course semesters.
            $temMatriculaApropriada = $disciplinasObrigatoriasFaltantes->isEmpty();

            if ($semestreAtual === 1) {
                // First semester: check for odd semester mandatory courses
                $temObrigatoriaImpar = $disciplinasObrigatoriasFaltantes->contains(fn ($disc) => $disc['numsemidl'] % 2 === 1);
                if (! $temObrigatoriaImpar || $temMatriculaApropriada) {
                    $semestreBase--;
                }
            } else {
                // Second semester: check for even semester mandatory courses
                $temObrigatoriaPar = $disciplinasObrigatoriasFaltantes->contains(fn ($disc) => $disc['numsemidl'] % 2 === 0);
                if (! $temObrigatoriaPar || $temMatriculaApropriada) {
                    $semestreBase--;
                }
            }

            // Final adjustment: if at ideal duration but still has mandatory courses
            if ($semestreBase === $duracaoIdeal && ! $disciplinasObrigatoriasFaltantes->isEmpty()) {
                $semestreBase--;
            }
        }

        return (int) max($semestreBase, 1);
    }

    /**
     * Validate Blocos requirements for Licenciatura em Matemática (45024).
     *
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretra: int}>  $historico
     * @return Collection<int, array{bloco_id: int, nome: string, creditos_obtidos: array{aula: int, trabalho: int}, creditos_exigidos: array{aula: int, trabalho: int}, disciplinas_cursadas: Collection<int, array{coddis: string, nomdis: string, creaul: int, cretra: int}>}>
     */
    private function validarBlocos(string $codcrl, Collection $historico): Collection
    {
        $blocos = Bloco::where('codcrl', $codcrl)
            ->with('disciplinas')
            ->get();

        return $blocos->map(function ($bloco) use ($historico) {
            /** @var Collection<int, array{coddis: string, nomdis: string, creaul: int, cretra: int}> $disciplinasCursadas */
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
                        'cretra' => (int) $cursada['cretra'],
                    ]);

                    $creditosAula += (int) $cursada['creaul'];
                    $creditosTrabalho += (int) $cursada['cretra'];
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
     * @param  Collection<int, covariant array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretra: int}>  $historico
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

            // Determine if núcleo is complete (usually the first regra)
            $primeiraRegra = $regrasCumpridas->first();
            $nucleoCumprido = $primeiraRegra !== null && $primeiraRegra['cumprida'];

            // Determine if full trilha is complete (all regras must be fulfilled)
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
}
