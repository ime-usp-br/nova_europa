<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Services\EvolucaoService;
use App\Services\PdfGenerationService;
use Symfony\Component\HttpFoundation\StreamedResponse;
use Illuminate\Support\Facades\App;

class AtestadoController extends Controller
{
    public function __construct(
        private EvolucaoService $evolucaoService,
        private PdfGenerationService $pdfGenerationService
    ) {}

    /**
     * Gera o atestado de matrícula para um aluno.
     *
     * @param int $nusp
     * @param string $codcrl
     * @return StreamedResponse
     */
    public function generate(int $nusp, string $codcrl): StreamedResponse
    {
        try {
            // Cria um objeto User temporário para o aluno (para compatibilidade com o serviço)
            $alunoModel = new User;
            $alunoModel->codpes = $nusp;

            // Processa a evolução do aluno para obter todos os dados necessários
            $evolucaoDTO = $this->evolucaoService->processarEvolucao($alunoModel, $codcrl);

            // Prepara os dados para a view do atestado
            $alunoArray = [
                'codpes' => $evolucaoDTO->aluno['codpes'],
                'nompes' => $evolucaoDTO->aluno['nompes'],
                'tipdocidf' => $evolucaoDTO->aluno['tipdocidf'],
                'numdocidf' => $evolucaoDTO->aluno['numdocidf'],
                'sglorgexdidf' => $evolucaoDTO->aluno['sglorgexdidf'],
                'nomcur' => $evolucaoDTO->aluno['nomcur'],
                'duridlcur' => $evolucaoDTO->curriculo['curriculo']['duracao_ideal'] ?? 8,
            ];
            $alunoParaAtestado = (object) $alunoArray;

            $semestreEstagio = $evolucaoDTO->semestreEstagio;

            App::setLocale('pt_BR');
            $dataPorExtenso = now()->translatedFormat('d \de F \de Y');

            return $this->pdfGenerationService->gerarAtestadoMatriculaPdf(
                $alunoParaAtestado,
                $semestreEstagio,
                $dataPorExtenso
            );
        } catch (\Exception $e) {
            abort(500, $e->getMessage());
        }
    }
}
