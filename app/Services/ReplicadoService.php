<?php

namespace App\Services;

use App\Exceptions\ReplicadoServiceException;
use Illuminate\Support\Collection;
use PDOException;
use Throwable;
use Uspdev\Replicado\DB as ReplicadoDB;
use Uspdev\Replicado\Graduacao;
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
     * @return array{codpes: int, nompes: string|null, dtanas: string|null, email: string|null, codcur: int|null, nomcur: string|null, codhab: int|null, nomhab: string|null, dtainivin: string|null} Student data
     *
     * @throws ReplicadoServiceException When student not found or database error occurs
     */
    public function buscarAluno(int $codpes): array
    {
        try {
            // Validate parameter
            if ($codpes <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpes', __('Must be a positive integer'));
            }

            // Fetch basic personal data
            $pessoaData = Pessoa::dump($codpes);

            if (empty($pessoaData)) {
                throw ReplicadoServiceException::notFound(__('Student'), $codpes);
            }

            // Fetch active course data
            $cursoData = Graduacao::obterCursoAtivo($codpes);

            // Fetch email
            $email = Pessoa::email($codpes);

            // Build structured response with explicit type casting
            /** @var int $resultCodepes */
            $resultCodepes = $pessoaData['codpes'] ?? $codpes;
            /** @var string|null $resultNompes */
            $resultNompes = $pessoaData['nompes'] ?? null;
            /** @var string|null $resultDtanas */
            $resultDtanas = $pessoaData['dtanas'] ?? null;
            /** @var int|null $resultCodcur */
            $resultCodcur = $cursoData['codcur'] ?? null;
            /** @var string|null $resultNomcur */
            $resultNomcur = $cursoData['nomcur'] ?? null;
            /** @var int|null $resultCodhab */
            $resultCodhab = $cursoData['codhab'] ?? null;
            /** @var string|null $resultNomhab */
            $resultNomhab = $cursoData['nomhab'] ?? null;
            /** @var string|null $resultDtainivin */
            $resultDtainivin = $cursoData['dtainivin'] ?? null;

            return [
                'codpes' => $resultCodepes,
                'nompes' => $resultNompes,
                'dtanas' => $resultDtanas,
                'email' => $email ?: null,
                'codcur' => $resultCodcur,
                'nomcur' => $resultNomcur,
                'codhab' => $resultCodhab,
                'nomhab' => $resultNomhab,
                'dtainivin' => $resultDtainivin,
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
     * @return Collection<int, array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretra: int}> Collection of academic history records
     *
     * @throws ReplicadoServiceException When database error occurs
     */
    public function buscarHistorico(int $codpes, int $codpgm): Collection
    {
        try {
            // Validate parameters
            if ($codpes <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpes', __('Must be a positive integer'));
            }

            if ($codpgm <= 0) {
                throw ReplicadoServiceException::invalidParameter('codpgm', __('Must be a positive integer'));
            }

            $query = "
                SELECT
                    H.codpes,
                    H.codpgm,
                    H.coddis,
                    H.verdis,
                    H.codtur,
                    H.notfim,
                    H.frqfim,
                    H.rstfim,
                    H.discrl,
                    H.stamtr,
                    H.dtavalfim,
                    D.nomdis,
                    D.creaul,
                    D.cretra
                FROM HISTESCOLARGR H
                INNER JOIN DISCIPLINAGR D ON H.coddis = D.coddis AND H.verdis = D.verdis
                WHERE H.codpes = CONVERT(int, :codpes)
                  AND H.codpgm = CONVERT(int, :codpgm)
                  AND H.stamtr IN ('M', 'E')
                ORDER BY H.dtavalfim DESC
            ";

            $params = [
                'codpes' => $codpes,
                'codpgm' => $codpgm,
            ];

            /** @var array<int, array{codpes: int|string, codpgm: int|string, coddis: string, verdis: int, codtur: string, notfim: float|null, frqfim: float|null, rstfim: string, discrl: string, stamtr: string, dtavalfim: string|null, nomdis: string, creaul: int, cretra: int}> $result */
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
     * @param  string  $codcrl  Curriculum code
     * @return array{curriculo: array<string, mixed>, disciplinas: Collection<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}>} Curriculum data
     *
     * @throws ReplicadoServiceException When curriculum not found or database error occurs
     */
    public function buscarGradeCurricular(string $codcrl): array
    {
        try {
            // Validate parameter
            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            // Fetch curriculum basic data
            $curriculoQuery = '
                SELECT
                    codcrl,
                    dtainicrl,
                    dtafimcrl,
                    numdiaintmin,
                    numdiaintmax,
                    dtainivencrl,
                    numcredaulobg,
                    numcredaulopc,
                    numcredaulopt,
                    numcredtrbopc
                FROM CURRICULOGR
                WHERE codcrl = :codcrl
            ';

            /** @var array<string, mixed>|false $curriculoData */
            $curriculoData = ReplicadoDB::fetch($curriculoQuery, ['codcrl' => $codcrl]);

            if (empty($curriculoData)) {
                throw ReplicadoServiceException::notFound(__('Curriculum'), $codcrl);
            }

            // Fetch curriculum disciplines
            $disciplinasQuery = '
                SELECT
                    G.coddis,
                    G.verdis,
                    G.tipobg,
                    G.numsemidl,
                    D.nomdis,
                    D.creaul,
                    D.cretra
                FROM GRADECURRICULAR G
                INNER JOIN DISCIPLINAGR D ON G.coddis = D.coddis AND G.verdis = D.verdis
                WHERE G.codcrl = :codcrl
                ORDER BY G.numsemidl, D.nomdis
            ';

            /** @var array<int, array{coddis: string, verdis: int, tipobg: string, numsemidl: int, nomdis: string, creaul: int, cretra: int}> $disciplinas */
            $disciplinas = ReplicadoDB::fetchAll($disciplinasQuery, ['codcrl' => $codcrl]);

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
            // Validate parameters
            if (empty(trim($coddis))) {
                throw ReplicadoServiceException::invalidParameter('coddis', __('Cannot be empty'));
            }

            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            // First, find equivalence groups that include this discipline for this curriculum
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

            // For each group, fetch all equivalent disciplines
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
}
