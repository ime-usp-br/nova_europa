<?php

namespace App\Services;

use App\Exceptions\ReplicadoServiceException;
use Illuminate\Support\Collection;
use PDOException;
use Throwable;
use Uspdev\Replicado\DB as ReplicadoDB;
use Uspdev\Replicado\Pessoa;

/**
 * Service for interacting with USP Replicado database.
 *
 * This service centralizes all interactions with the Replicado database,
 * providing a clean abstraction layer over the uspdev/replicado package.
 * It handles error management and data transformation consistently.
 */
class ReplicadoService
{
    /**
     * Fetch student data by USP code (NUSP).
     *
     * Returns comprehensive student information including personal data
     * and current enrollment details.
     *
     * @param  int  $codpes  Student USP code (NUSP)
     * @return array{codpes: int, nompes: string|null, dtanas: string|null, email: string|null, tipdocidf: string|null, numdocidf: string|null, sglorgexdidf: string|null, codcur: int|null, nomcur: string|null, codhab: int|null, nomhab: string|null, dtainivin: string|null, codpgm: int|null, stapgm: string|null} Student data
     *
     * @throws ReplicadoServiceException When student not found or database error occurs
     */
    public function buscarAluno(int $codpes): array
    {
        try {
            if ($codpes <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpes', __('Must be a positive integer'));
            }

            $query = "
                SELECT TOP 1
                    P.codpes, P.nompes, P.dtanas, P.tipdocidf, P.numdocidf, P.sglorgexdidf,
                    H.codcur, C.nomcur, H.codhab, HB.nomhab, V.dtainivin,
                    PR.codpgm, PR.stapgm
                FROM PESSOA AS P
                INNER JOIN VINCULOPESSOAUSP AS V ON (P.codpes = V.codpes)
                INNER JOIN HABILPROGGR AS H ON (P.codpes = H.codpes)
                INNER JOIN PROGRAMAGR AS PR ON (P.codpes = PR.codpes AND H.codpgm = PR.codpgm)
                INNER JOIN CURSOGR AS C ON (H.codcur = C.codcur)
                INNER JOIN HABILITACAOGR AS HB ON (H.codcur = HB.codcur AND H.codhab = HB.codhab)
                WHERE P.codpes = :codpes
                  AND V.tipvin = 'ALUNOGR'
                  AND H.dtafim IS NULL
                  AND PR.stapgm <> 'E'
                ORDER BY H.dtaini DESC
            ";

            /** @var array<string, mixed>|false $rawAlunoData */
            $rawAlunoData = ReplicadoDB::fetch($query, ['codpes' => $codpes]);

            if (empty($rawAlunoData)) {
                throw ReplicadoServiceException::notFound(__('Student'), $codpes);
            }

            /** @var array{codpes: int|string|null, nompes: string|null, dtanas: string|null, tipdocidf: string|null, numdocidf: string|null, sglorgexdidf: string|null, codcur: int|string|null, nomcur: string|null, codhab: int|string|null, nomhab: string|null, dtainivin: string|null, codpgm: int|string|null, stapgm: string|null} $alunoData */
            $alunoData = $rawAlunoData;

            $email = Pessoa::email($codpes);

            return [
                'codpes' => (int) $alunoData['codpes'],
                'nompes' => ! empty($alunoData['nompes']) ? (string) $alunoData['nompes'] : null,
                'dtanas' => ! empty($alunoData['dtanas']) ? (string) $alunoData['dtanas'] : null,
                'email' => $email ?: null,
                'tipdocidf' => ! empty($alunoData['tipdocidf']) ? (string) $alunoData['tipdocidf'] : null,
                'numdocidf' => ! empty($alunoData['numdocidf']) ? (string) $alunoData['numdocidf'] : null,
                'sglorgexdidf' => ! empty($alunoData['sglorgexdidf']) ? (string) $alunoData['sglorgexdidf'] : null,
                'codcur' => ! empty($alunoData['codcur']) ? (int) $alunoData['codcur'] : null,
                'nomcur' => ! empty($alunoData['nomcur']) ? (string) $alunoData['nomcur'] : null,
                'codhab' => ! empty($alunoData['codhab']) ? (int) $alunoData['codhab'] : null,
                'nomhab' => ! empty($alunoData['nomhab']) ? (string) $alunoData['nomhab'] : null,
                'dtainivin' => ! empty($alunoData['dtainivin']) ? (string) $alunoData['dtainivin'] : null,
                'codpgm' => ! empty($alunoData['codpgm']) ? (int) $alunoData['codpgm'] : null,
                'stapgm' => ! empty($alunoData['stapgm']) ? (string) $alunoData['stapgm'] : null,
            ];

        } catch (PDOException $e) {
            throw ReplicadoServiceException::connectionFailed($e);
        } catch (ReplicadoServiceException $e) {
            throw $e;
        } catch (Throwable $e) {
            throw new ReplicadoServiceException(
                __('Error fetching student data: :message', ['message' => $e->getMessage()]),
                500,
                $e
            );
        }
    }

    /**
     * Fetch student academic history by USP code and program code.
     *
     * Returns a collection of all courses taken by the student in the specified program,
     * including grades, attendance, and course details.
     *
     * @param  int  $codpes  Student USP code (NUSP)
     * @param  int  $codpgm  Program code
     * @return Collection<int, array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretrb: int}> Collection of academic history records
     *
     * @throws ReplicadoServiceException When database error occurs
     */
    public function buscarHistorico(int $codpes, int $codpgm): Collection
    {
        try {
            if ($codpes <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpes', __('Must be a positive integer'));
            }
            if ($codpgm <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpgm', __('Must be a positive integer'));
            }

            $query = "
                SELECT
                    H.codpes, H.codpgm, H.coddis, H.verdis, H.codtur,
                    H.notfim, H.frqfim, H.rstfim, H.discrl, H.stamtr,
                    H.dtavalfim, D.nomdis, D.creaul, D.cretrb
                FROM HISTESCOLARGR H
                INNER JOIN DISCIPLINAGR D ON H.coddis = D.coddis AND H.verdis = D.verdis
                LEFT JOIN TURMAGR AS T ON H.coddis = T.coddis AND H.verdis = T.verdis AND H.codtur = T.codtur
                WHERE H.codpes = CONVERT(int, :codpes)
                  AND H.codpgm = CONVERT(int, :codpgm)
                  AND H.stamtr = 'M'
                  AND (T.tiptur IS NULL OR T.tiptur <> 'Prática Vinculada')
                ORDER BY H.coddis ASC
            ";

            $params = [
                'codpes' => $codpes,
                'codpgm' => $codpgm,
            ];

            /** @var array<int, array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretrb: int}> $result */
            $result = ReplicadoDB::fetchAll($query, $params);

            return collect($result);
        } catch (PDOException $e) {
            throw ReplicadoServiceException::connectionFailed($e);
        } catch (ReplicadoServiceException $e) {
            throw $e;
        } catch (Throwable $e) {
            throw ReplicadoServiceException::queryFailed('buscarHistorico', $e);
        }
    }

    /**
     * Fetch curriculum structure by curriculum code.
     *
     * Returns complete curriculum information including basic data
     * and all disciplines that compose the curriculum.
     *
     * For courses with a basic cycle (codhab = 0), this method automatically
     * merges the basic cycle disciplines with the specific program disciplines
     * to provide a unified curriculum view.
     *
     * @param  string  $codcrl  Curriculum code
     * @return array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}>} Curriculum data
     *
     * @throws ReplicadoServiceException When curriculum not found or database error occurs
     */
    public function buscarGradeCurricular(string $codcrl): array
    {
        try {
            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            $curriculoQuery = '
                SELECT
                    C.codcrl, C.codcur, C.codhab, C.dtainicrl, C.dtafimcrl,
                    C.cgahorobgaul, C.cgahorobgtrb,
                    C.cgaoptcplaul, C.cgaoptcpltrb,
                    C.cgaoptlreaul, C.cgaoptlretrb,
                    COALESCE(H.duridlhab, C.duridlcur) as duracao_ideal
                FROM CURRICULOGR C
                LEFT JOIN HABILDURACAO H ON (
                    H.codcur = C.codcur
                    AND H.codhab = C.codhab
                    AND H.dtainivaldur <= C.dtainicrl
                    AND (H.dtafimvaldur IS NULL OR H.dtafimvaldur >= C.dtainicrl)
                )
                WHERE C.codcrl = :codcrl
            ';

            /** @var array<string, mixed>|false $curriculoData */
            $curriculoData = ReplicadoDB::fetch($curriculoQuery, ['codcrl' => $codcrl]);

            if (empty($curriculoData)) {
                throw ReplicadoServiceException::notFound(__('Curriculum'), $codcrl);
            }

            $disciplinasQuery = '
                SELECT
                    G.coddis, G.verdis, G.tipobg, G.numsemidl,
                    D.nomdis, D.creaul, D.cretrb
                FROM GRADECURRICULAR G
                INNER JOIN DISCIPLINAGR D ON G.coddis = D.coddis AND G.verdis = D.verdis
                WHERE G.codcrl = :codcrl
                ORDER BY G.numsemidl, D.nomdis
            ';

            /** @var array<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}> $disciplinas */
            $disciplinas = ReplicadoDB::fetchAll($disciplinasQuery, ['codcrl' => $codcrl]);

            // Check if this curriculum has a basic cycle (codhab != 0 means specific program)
            // For BMA/BMAC courses, we need to merge basic cycle (codhab=0) with specific program
            $codhab = is_numeric($curriculoData['codhab'] ?? null) ? (int) $curriculoData['codhab'] : 0;
            $codcur = is_numeric($curriculoData['codcur'] ?? null) ? (int) $curriculoData['codcur'] : 0;
            $dtainicrl = $curriculoData['dtainicrl'] ?? null;

            if ($codhab !== 0 && $codcur > 0 && $dtainicrl !== null) {
                // This is a specific program (codhab like 104, 504, etc)
                // Check for corresponding basic cycle (codhab like 001, 004)
                $codcrlCicloBasico = $this->construirCodcrlCicloBasico($codcrl);

                // Only search for basic cycle if it's different from the current codcrl
                // (Avoid searching when already on basic cycle like 004)
                if ($codcrlCicloBasico !== $codcrl) {
                    // Try to find exact basic cycle match first
                    /** @var array<string, mixed>|false $curriculoCicloBasico */
                    $curriculoCicloBasico = ReplicadoDB::fetch($curriculoQuery, [
                        'codcrl' => $codcrlCicloBasico,
                    ]);

                    // If exact match not found, find closest basic cycle by date
                    if (! $curriculoCicloBasico) {
                        $periodoIndicador = substr($codcrl, 8, 1); // Last digit of codhab (0=integral, 1=day, 4=night)
                        $cohabCicloBasico = (int) $periodoIndicador; // Convert to int: 0, 1, or 4

                        $cicloMaisProximoQuery = '
                            SELECT TOP 1 codcrl, codcur, codhab, dtainicrl, dtafimcrl, duridlcur,
                                cgahorobgaul, cgahorobgtrb,
                                cgaoptcplaul, cgaoptcpltrb,
                                cgaoptlreaul, cgaoptlretrb
                            FROM CURRICULOGR
                            WHERE codcur = :codcur
                                AND codhab = :codhab
                                AND dtainicrl <= :dtainicrl
                            ORDER BY dtainicrl DESC
                        ';

                        /** @var array<string, mixed>|false $curriculoCicloBasico */
                        $curriculoCicloBasico = ReplicadoDB::fetch($cicloMaisProximoQuery, [
                            'codcur' => $codcur,
                            'codhab' => $cohabCicloBasico,
                            'dtainicrl' => $curriculoData['dtainicrl'],
                        ]);
                    }

                    if ($curriculoCicloBasico) {
                        // Basic cycle exists, merge its disciplines
                        /** @var array<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretrb: int}> $disciplinasCicloBasico */
                        $disciplinasCicloBasico = ReplicadoDB::fetchAll($disciplinasQuery, ['codcrl' => $curriculoCicloBasico['codcrl']]);

                        // Merge basic cycle disciplines with specific program disciplines
                        $disciplinas = array_merge($disciplinasCicloBasico, $disciplinas);

                        // Sort by semester and name
                        usort($disciplinas, function ($a, $b) {
                            $semCompare = $a['numsemidl'] <=> $b['numsemidl'];
                            if ($semCompare !== 0) {
                                return $semCompare;
                            }

                            return strcmp($a['nomdis'], $b['nomdis']);
                        });

                        // Sum required credits from both curricula
                        // cgahorobgaul = Mandatory course load hours (aula)
                        // cgahorobgtrb = Mandatory work hours (trabalho)
                        // cgaoptcplaul = Elective course load hours (aula)
                        // cgaoptcpltrb = Elective work hours (trabalho)
                        // cgaoptlreaul = Free course load hours (aula)
                        // cgaoptlretrb = Free work hours (trabalho)
                        $curriculoData['cgahorobgaul'] = (is_numeric($curriculoData['cgahorobgaul'] ?? null) ? (int) $curriculoData['cgahorobgaul'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgahorobgaul'] ?? null) ? (int) $curriculoCicloBasico['cgahorobgaul'] : 0);
                        $curriculoData['cgahorobgtrb'] = (is_numeric($curriculoData['cgahorobgtrb'] ?? null) ? (int) $curriculoData['cgahorobgtrb'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgahorobgtrb'] ?? null) ? (int) $curriculoCicloBasico['cgahorobgtrb'] : 0);
                        $curriculoData['cgaoptcplaul'] = (is_numeric($curriculoData['cgaoptcplaul'] ?? null) ? (int) $curriculoData['cgaoptcplaul'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgaoptcplaul'] ?? null) ? (int) $curriculoCicloBasico['cgaoptcplaul'] : 0);
                        $curriculoData['cgaoptcpltrb'] = (is_numeric($curriculoData['cgaoptcpltrb'] ?? null) ? (int) $curriculoData['cgaoptcpltrb'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgaoptcpltrb'] ?? null) ? (int) $curriculoCicloBasico['cgaoptcpltrb'] : 0);
                        $curriculoData['cgaoptlreaul'] = (is_numeric($curriculoData['cgaoptlreaul'] ?? null) ? (int) $curriculoData['cgaoptlreaul'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgaoptlreaul'] ?? null) ? (int) $curriculoCicloBasico['cgaoptlreaul'] : 0);
                        $curriculoData['cgaoptlretrb'] = (is_numeric($curriculoData['cgaoptlretrb'] ?? null) ? (int) $curriculoData['cgaoptlretrb'] : 0)
                            + (is_numeric($curriculoCicloBasico['cgaoptlretrb'] ?? null) ? (int) $curriculoCicloBasico['cgaoptlretrb'] : 0);
                    }
                }
            }

            // Fallback for duracao_ideal if NULL: calculate from maximum semester of mandatory courses
            if (empty($curriculoData['duracao_ideal'])) {
                $maxSemestre = collect($disciplinas)
                    ->where('tipobg', 'O')
                    ->max('numsemidl');
                $curriculoData['duracao_ideal'] = $maxSemestre ?? 8;
            }

            return [
                'curriculo' => $curriculoData,
                'disciplinas' => collect($disciplinas),
            ];
        } catch (PDOException $e) {
            throw ReplicadoServiceException::connectionFailed($e);
        } catch (ReplicadoServiceException $e) {
            throw $e;
        } catch (Throwable $e) {
            throw ReplicadoServiceException::queryFailed('buscarGradeCurricular', $e);
        }
    }

    /**
     * Construct basic cycle codcrl from a specific program codcrl.
     *
     * Basic cycle has codhab ending in 04 (004 for night, 001 for day).
     * Specific programs have codhab like 104, 204, 504, etc.
     *
     * Examples:
     * - 450700504251 -> 450700004251 (night cycle: 504 -> 004)
     * - 450700104241 -> 450700001241 (day cycle: 104 -> 001)
     *
     * @param  string  $codcrl  Original curriculum code
     * @return string Basic cycle curriculum code
     */
    private function construirCodcrlCicloBasico(string $codcrl): string
    {
        // codcrl format: CCCCCCHHHDYY
        // CCCCCC = codcur (6 digits, e.g., 450420, 450700)
        // HHH = codhab (3 digits, last digit is period indicator: 0=integral, 1=day, 4=night)
        // D = semester (1 digit: 1 or 2)
        // YY = year (2 digits)
        //
        // Basic cycle pattern:
        // - Integral programs (X00): 000
        // - Day programs (X01): 001 (legacy)
        // - Night programs (X04): 004
        //
        // Example: 450420 101 232
        //          codcur ^HHH ^DYY
        // Becomes: 450420 001 232 (keep only last digit: 1)

        if (strlen($codcrl) !== 12) {
            return $codcrl; // Invalid format, return as-is
        }

        $codcur = substr($codcrl, 0, 6); // CCCCCC (6 digits)
        $anoSemestre = substr($codcrl, 9, 3); // DYY (3 digits)

        // Get last digit of codhab (period indicator: 0=integral, 1=day, 4=night)
        $periodoIndicador = substr($codcrl, 8, 1); // Position 8 (last digit of codhab)

        // Build basic cycle codcrl: CCCCCC + 00 + period + DYY
        return $codcur.'00'.$periodoIndicador.$anoSemestre;
    }

    /**
     * Fetch equivalence rules for a discipline in a specific curriculum.
     *
     * Returns all equivalence groups and their component disciplines
     * that can substitute the target discipline.
     *
     * @param  string  $coddis  Discipline code
     * @param  string  $codcrl  Curriculum code
     * @return Collection<int, array{codeqv: int, disciplinas_equivalentes: Collection<int, array{coddis: string, verdis: int, nomdis: string}>}> Collection of equivalence groups
     *
     * @throws ReplicadoServiceException When database error occurs
     */
    public function buscarEquivalencias(string $coddis, string $codcrl): Collection
    {
        try {
            if (empty(trim($coddis))) {
                throw ReplicadoServiceException::invalidParameter('coddis', __('Cannot be empty'));
            }
            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            $gruposQuery = '
                SELECT DISTINCT G.codeqv
                FROM GRUPOEQUIVGR G
                WHERE G.coddis = :coddis
                  AND G.codcrl = :codcrl
            ';

            /** @var array<int, array{codeqv: int}> $grupos */
            $grupos = ReplicadoDB::fetchAll($gruposQuery, [
                'coddis' => $coddis,
                'codcrl' => $codcrl,
            ]);

            if (empty($grupos)) {
                /** @var Collection<int, array{codeqv: int, disciplinas_equivalentes: Collection<int, array{coddis: string, verdis: int, nomdis: string}>}> */
                return collect([]);
            }

            /** @var Collection<int, array{codeqv: int, disciplinas_equivalentes: Collection<int, array{coddis: string, verdis: int, nomdis: string}>}> $equivalencias */
            $equivalencias = collect();

            foreach ($grupos as $grupo) {
                $codeqv = $grupo['codeqv'];

                $disciplinasQuery = '
                    SELECT
                        E.coddis,
                        E.verdis,
                        D.nomdis
                    FROM EQUIVALENCIAGR E
                    INNER JOIN DISCIPLINAGR D ON E.coddis = D.coddis AND E.verdis = D.verdis
                    WHERE E.codeqv = CONVERT(int, :codeqv)
                    ORDER BY E.coddis
                ';

                /** @var array<int, array{coddis: string, verdis: int, nomdis: string}> $disciplinas */
                $disciplinas = ReplicadoDB::fetchAll($disciplinasQuery, ['codeqv' => $codeqv]);

                $equivalencias->push([
                    'codeqv' => $codeqv,
                    'disciplinas_equivalentes' => collect($disciplinas),
                ]);
            }

            return $equivalencias;
        } catch (PDOException $e) {
            throw ReplicadoServiceException::connectionFailed($e);
        } catch (ReplicadoServiceException $e) {
            throw $e;
        } catch (Throwable $e) {
            throw ReplicadoServiceException::queryFailed('buscarEquivalencias', $e);
        }
    }

    /**
     * Fetch student data for the enrollment certificate.
     *
     * @param  int  $codpes  Student USP code (NUSP)
     * @return object|null Student data
     *
     * @throws ReplicadoServiceException
     */
    public function obterDadosAlunoAtestado(int $codpes, string $codcrl): ?object
    {
        try {
            if ($codpes <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpes', __('Must be a positive integer'));
            }
            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            $query = "
                SELECT TOP 1
                    P.codpes, P.nompes, P.tipdocidf, P.numdocidf, P.sglorgexdidf,
                    C.nomcur,
                    COALESCE(HD.duridlhab, CGL.duridlcur) as duridlcur
                FROM
                    PESSOA AS P
                INNER JOIN
                    VINCULOPESSOAUSP AS V ON (P.codpes = V.codpes)
                INNER JOIN
                    PROGRAMAGR AS PR ON (P.codpes = PR.codpes)
                INNER JOIN
                    HABILPROGGR AS H ON (PR.codpgm = H.codpgm)
                INNER JOIN
                    CURRICULOGR AS CGL ON (H.codcur = CGL.codcur AND H.codhab = CGL.codhab)
                INNER JOIN
                    CURSOGR AS C ON (CGL.codcur = C.codcur)
                LEFT JOIN
                    HABILDURACAO AS HD ON (CGL.codcur = HD.codcur AND CGL.codhab = HD.codhab AND HD.dtainivaldur <= CGL.dtainicrl AND (HD.dtafimvaldur IS NULL OR HD.dtafimvaldur >= CGL.dtainicrl))
                WHERE
                    P.codpes = :codpes
                    AND CGL.codcrl = :codcrl
                    AND V.tipvin = 'ALUNOGR'
                    AND PR.stapgm <> 'E'
                ORDER BY
                    H.dtaini DESC
            ";

            $result = ReplicadoDB::fetch($query, ['codpes' => $codpes, 'codcrl' => $codcrl]);

            if (empty($result)) {
                return null;
            }

            return (object) $result;

        } catch (PDOException $e) {
            throw ReplicadoServiceException::connectionFailed($e);
        } catch (Throwable $e) {
            throw new ReplicadoServiceException(
                __('Error fetching student data for certificate: :message', ['message' => $e->getMessage()]),
                500,
                $e
            );
        }
    }
}
