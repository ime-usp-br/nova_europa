<?php

namespace App\Services;

use App\Exceptions\ReplicadoServiceException;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Log;
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
     * @return array{codpes: int, nompes: string|null, dtanas: string|null, email: string|null, codcur: int|null, nomcur: string|null, codhab: int|null, nomhab: string|null, dtainivin: string|null, codpgm: int|null, stapgm: string|null} Student data
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
                    P.codpes, P.nompes, P.dtanas,
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

            /** @var array<string, mixed>|false $alunoData */
            $alunoData = ReplicadoDB::fetch($query, ['codpes' => $codpes]);

            if (empty($alunoData)) {
                throw ReplicadoServiceException::notFound(__('Student'), $codpes);
            }

            $email = Pessoa::email($codpes);

            return [
                'codpes' => (int) $alunoData['codpes'],
                'nompes' => $alunoData['nompes'] ? (string) $alunoData['nompes'] : null,
                'dtanas' => $alunoData['dtanas'] ? (string) $alunoData['dtanas'] : null,
                'email' => $email ?: null,
                'codcur' => $alunoData['codcur'] ? (int) $alunoData['codcur'] : null,
                'nomcur' => $alunoData['nomcur'] ? (string) $alunoData['nomcur'] : null,
                'codhab' => $alunoData['codhab'] ? (int) $alunoData['codhab'] : null,
                'nomhab' => $alunoData['nomhab'] ? (string) $alunoData['nomhab'] : null,
                'dtainivin' => $alunoData['dtainivin'] ? (string) $alunoData['dtainivin'] : null,
                'codpgm' => $alunoData['codpgm'] ? (int) $alunoData['codpgm'] : null,
                'stapgm' => $alunoData['stapgm'] ? (string) $alunoData['stapgm'] : null,
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
            if (empty(trim($codcrl))) {
                throw ReplicadoServiceException::invalidParameter('codcrl', __('Cannot be empty'));
            }

            $curriculoQuery = '
                SELECT
                    codcrl, dtainicrl, dtafimcrl, duridlcur,
                    cgahorobgaul, cgahorobgtrb,
                    cgaoptcplaul, cgaoptcpltrb,
                    cgaoptlreaul, cgaoptlretrb
                FROM CURRICULOGR
                WHERE codcrl = :codcrl
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
}