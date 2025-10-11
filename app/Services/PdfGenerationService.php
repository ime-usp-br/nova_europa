<?php

namespace App\Services;

use App\DTOs\EvolucaoDTO;
use Illuminate\Support\Facades\View;
use Spatie\Browsershot\Browsershot;
use Symfony\Component\HttpFoundation\StreamedResponse;

/**
 * Service for generating PDF documents from student evolution data.
 *
 * This service uses Spatie Browsershot (Chromium/Puppeteer) to convert
 * HTML/CSS templates into high-quality PDF documents. This approach allows
 * using modern HTML/CSS for complex layouts instead of programmatic PDF generation.
 *
 * @example Usage in a controller:
 *
 * ```php
 * use App\Services\PdfGenerationService;
 * use App\Services\EvolucaoService;
 *
 * class EvolucaoController extends Controller
 * {
 *     public function __construct(
 *         private EvolucaoService $evolucaoService,
 *         private PdfGenerationService $pdfService
 *     ) {}
 *
 *     public function gerarPdf(Request $request)
 *     {
 *         // 1. Get authenticated user
 *         $aluno = auth()->user();
 *
 *         // 2. Process student evolution
 *         $evolucaoDTO = $this->evolucaoService->processarEvolucao(
 *             $aluno,
 *             $request->input('codcrl')
 *         );
 *
 *         // 3. Generate and return PDF
 *         return $this->pdfService->gerarEvolucaoPdf($evolucaoDTO);
 *
 *         // Optional: Generate black & white PDF
 *         // return $this->pdfService->gerarEvolucaoPdf($evolucaoDTO, colorido: false);
 *     }
 * }
 * ```
 */
class PdfGenerationService
{
    /**
     * Generate student evolution PDF document.
     *
     * Renders a Blade template with evolution data and converts to PDF.
     * Returns a StreamedResponse for browser download.
     *
     * @param  EvolucaoDTO  $dados  Complete evolution data from EvolucaoService
     * @param  bool  $colorido  Whether to use colored PDF (default: true)
     * @return StreamedResponse PDF download response
     *
     * @throws \Exception When PDF generation fails
     */
    public function gerarEvolucaoPdf(EvolucaoDTO $dados, bool $colorido = true): StreamedResponse
    {
        try {
            // Validate course code
            $codcur = $dados->aluno['codcur'];
            if ($codcur === null) {
                throw new \InvalidArgumentException(__('Course code is required to generate PDF'));
            }

            // Determine template based on course code
            $template = $this->determinarTemplate($codcur);

            // Render Blade template with evolution data
            $html = View::make($template, [
                'dados' => $dados,
                'colorido' => $colorido,
            ])->render();

            // Generate PDF using Browsershot
            $pdfContent = Browsershot::html($html)
                ->setNodeBinary('/usr/bin/node') // Explicitly set node path
                ->setNpmBinary('/usr/bin/npm') // Explicitly set npm path
                ->noSandbox() // Required for Docker/containerized environments
                ->format('A4') // A4 size (210mm x 297mm)
                ->margins(10, 10, 10, 10) // top, right, bottom, left in mm
                ->showBackground() // Enable background colors/images
                ->pdf(); // Return PDF content as string

            // Create filename
            $codpes = $dados->aluno['codpes'];
            $filename = "evolucao_{$codpes}.pdf";

            // Return as StreamedResponse for download
            return new StreamedResponse(
                function () use ($pdfContent) {
                    echo $pdfContent;
                },
                200,
                [
                    'Content-Type' => 'application/pdf',
                    'Content-Disposition' => "attachment; filename=\"{$filename}\"",
                    'Content-Length' => strlen($pdfContent),
                ]
            );
        } catch (\Exception $e) {
            throw new \Exception(__('Failed to generate PDF: :message', ['message' => $e->getMessage()]), 0, $e);
        }
    }

    /**
     * Determine which template to use based on course code.
     *
     * Different courses have different PDF layouts:
     * - 45052 (Computer Science): Includes Trilhas section
     * - 45024 (Math Education): Includes Blocos section
     * - 45070, 45042 (Biology): Includes supplementary electives
     * - Others: Standard template
     *
     * @param  int  $codcur  Course code
     * @return string Blade template path
     */
    private function determinarTemplate(int $codcur): string
    {
        return match ($codcur) {
            45052 => 'pdf.evolucao-45052', // Computer Science with Trilhas
            45024 => 'pdf.evolucao-45024', // Math Education with Blocos
            45070, 45042 => 'pdf.evolucao-map', // Biology programs
            default => 'pdf.evolucao-padrao', // Standard template
        };
    }

    /**
     * Generate enrollment certificate PDF.
     *
     * @param object $aluno
     * @param int $semestreEstagio
     * @param string $dataPorExtenso
     * @return StreamedResponse
     * @throws \Exception
     */
    public function gerarAtestadoMatriculaPdf(object $aluno, int $semestreEstagio, string $dataPorExtenso): StreamedResponse
    {
        try {
            $html = View::make('pdf.atestado-matricula', [
                'aluno' => $aluno,
                'semestreEstagio' => $semestreEstagio,
                'dataPorExtenso' => $dataPorExtenso,
            ])->render();

            $pdfContent = Browsershot::html($html)
                ->setNodeBinary('/usr/bin/node')
                ->setNpmBinary('/usr/bin/npm')
                ->noSandbox()
                ->format('A4')
                ->pdf();

            $filename = "atestado_matricula_{$aluno->codpes}.pdf";

            return new StreamedResponse(
                function () use ($pdfContent) {
                    echo $pdfContent;
                },
                200,
                [
                    'Content-Type' => 'application/pdf',
                    'Content-Disposition' => "attachment; filename=\"{$filename}\"",
                    'Content-Length' => strlen($pdfContent),
                ]
            );
        } catch (\Exception $e) {
            throw new \Exception(__('Failed to generate enrollment certificate PDF: :message', ['message' => $e->getMessage()]), 0, $e);
        }
    }
}
