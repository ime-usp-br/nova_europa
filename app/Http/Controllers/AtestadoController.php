<?php

namespace App\Http\Controllers;

use App\DTOs\AtestadoDTO;
use App\Models\User;
use App\Services\EvolucaoService;
use App\Services\PdfGenerationService;
use Illuminate\Support\Facades\App;
use Symfony\Component\HttpFoundation\StreamedResponse;

class AtestadoController extends Controller
{
    public function __construct(
        private EvolucaoService $evolucaoService,
        private PdfGenerationService $pdfGenerationService
    ) {}

    /**
     * Gera o atestado de matrícula para um aluno.
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
            $duracaoIdealValue = $evolucaoDTO->curriculo['curriculo']['duracao_ideal'] ?? 8;
            $alunoParaAtestado = new AtestadoDTO(
                codpes: $evolucaoDTO->aluno['codpes'],
                nompes: $evolucaoDTO->aluno['nompes'],
                tipdocidf: $evolucaoDTO->aluno['tipdocidf'],
                numdocidf: $evolucaoDTO->aluno['numdocidf'],
                sglorgexdidf: $evolucaoDTO->aluno['sglorgexdidf'],
                nomcur: $evolucaoDTO->aluno['nomcur'],
                duridlcur: is_numeric($duracaoIdealValue) ? (int) $duracaoIdealValue : 8,
            );

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
