<?php

use App\Services\EvolucaoService;
use App\Services\PdfGenerationService;
use Illuminate\Support\Facades\Route;

/**
 * Temporary test route for PDF generation
 *
 * REMOVE THIS FILE BEFORE DEPLOYING TO PRODUCTION!
 *
 * Usage:
 * http://localhost:8000/test-pdf?codpes=123456&codcrl=45052001
 */

Route::get('/test-pdf', function (EvolucaoService $evolucaoService, PdfGenerationService $pdfService) {
    // Get parameters from URL
    $codpes = request()->input('codpes');
    $codcrl = request()->input('codcrl');

    if (!$codpes || !$codcrl) {
        return response()->json([
            'error' => 'Missing parameters',
            'usage' => 'GET /test-pdf?codpes=123456&codcrl=45052001',
            'example' => 'http://localhost:8000/test-pdf?codpes=123456&codcrl=45052001'
        ], 400);
    }

    try {
        // Create a fake user with the provided codpes
        $fakeUser = new \App\Models\User();
        $fakeUser->codpes = (int) $codpes;
        $fakeUser->name = "Test User";
        $fakeUser->email = "test@test.com";

        // Process evolution
        $evolucaoDTO = $evolucaoService->processarEvolucao($fakeUser, $codcrl);

        // Generate PDF
        return $pdfService->gerarEvolucaoPdf($evolucaoDTO);

    } catch (\Exception $e) {
        return response()->json([
            'error' => $e->getMessage(),
            'trace' => $e->getTraceAsString(),
        ], 500);
    }
})->name('test.pdf');
