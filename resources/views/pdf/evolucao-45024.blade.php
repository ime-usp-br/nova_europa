<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ __('Student Evolution') }} - {{ $dados->aluno['codpes'] }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-blue: #0d47a1;
            --primary-blue-light: #1976d2;
            --primary-blue-lighter: #42a5f5;
            --accent-orange: #ff6f00;
            --accent-green: #2e7d32;
            --accent-red: #c62828;
            --gray-50: #fafafa;
            --gray-100: #f5f5f5;
            --gray-200: #eeeeee;
            --gray-300: #e0e0e0;
            --gray-400: #bdbdbd;
            --gray-600: #757575;
            --gray-800: #424242;
            --gray-900: #212121;
        }

        body {
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            font-size: 7pt;
            line-height: 1.3;
            color: var(--gray-900);
            background: #fff;
        }

        @page {
            margin: 10mm 12mm;
            size: A4;
        }

        /* Header Section - Print-Friendly */
        .header {
            background: white;
            color: var(--gray-900);
            padding: 8px 12px;
            margin-bottom: 10px;
            border: 2px solid var(--primary-blue);
            border-radius: 6px;
            page-break-after: avoid;
        }

        .header h1 {
            font-size: 12pt;
            font-weight: 600;
            margin-bottom: 6px;
            letter-spacing: -0.3px;
            text-transform: uppercase;
            border-bottom: 2px solid var(--primary-blue);
            padding-bottom: 4px;
            color: var(--primary-blue);
        }

        .header-info {
            font-size: 6.5pt;
            margin-bottom: 3px;
            line-height: 1.4;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .header-info strong {
            font-weight: 600;
            margin-right: 4px;
        }

        .header-badge {
            background: white;
            border: 1px solid var(--gray-400);
            padding: 1px 6px;
            border-radius: 10px;
            font-size: 6pt;
            font-weight: 500;
            margin-left: 3px;
        }

        /* Section Titles - Modern Design */
        .section-title {
            font-size: 8.5pt;
            font-weight: 600;
            margin-top: 8px;
            margin-bottom: 4px;
            color: var(--primary-blue);
            padding-left: 8px;
            border-left: 3px solid var(--primary-blue);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            page-break-after: avoid;
        }

        /* Grid for mandatory courses - Enhanced Visual Design */
        .grid-semestres {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-bottom: 8px;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            page-break-inside: auto;
        }

        .grid-semestres th {
            background: white;
            color: var(--primary-blue);
            padding: 4px 2px;
            text-align: center;
            font-weight: 600;
            font-size: 7pt;
            border: 1px solid var(--gray-400);
        }

        .grid-semestres th:first-child {
            border-top-left-radius: 6px;
        }

        .grid-semestres th:last-child {
            border-right: none;
            border-top-right-radius: 6px;
        }

        .grid-semestres td {
            border: 1px solid var(--gray-300);
            padding: 3px;
            vertical-align: top;
            font-size: 6.5pt;
            min-height: 30px;
            background: white;
            transition: background-color 0.2s;
        }

        .grid-semestres td:first-child {
            background: white;
            font-weight: 600;
            color: var(--primary-blue);
        }

        .grid-semestres tr:hover td {
            background: white;
        }

        .grid-semestres tr:last-child td:first-child {
            border-bottom-left-radius: 6px;
        }

        .disciplina-item {
            margin-bottom: 3px;
            padding: 2px;
            border-radius: 3px;
            background: white;
            border-left: 2px solid transparent;
        }

        .disciplina-item.aprovada {
            border-left-color: var(--accent-green);
        }

        .disciplina-item.cursando {
            border-left-color: var(--primary-blue-lighter);
        }

        .disciplina-item.dispensada {
            border-left-color: var(--accent-orange);
        }

        .disciplina-item.pendente {
            border-left-color: var(--gray-400);
        }

        .disciplina-codigo {
            font-weight: 600;
            font-size: 6.5pt;
            color: var(--gray-900);
            display: inline;
        }

        .disciplina-creditos {
            font-size: 5.5pt;
            color: var(--gray-600);
            display: inline;
            margin-left: 2px;
        }

        .disciplina-turma {
            font-size: 5.5pt;
            color: var(--gray-600);
            margin-top: 1px;
        }

        .status-badge {
            display: inline-block;
            padding: 0px 4px;
            border-radius: 8px;
            font-size: 5pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.2px;
        }

        .status-badge.aprovada {
            background: white;
            border: 1px solid var(--accent-green);
            color: var(--accent-green);
        }

        .status-badge.cursando {
            background: white;
            border: 1px solid var(--primary-blue-lighter);
            color: var(--primary-blue);
        }

        .status-badge.dispensada {
            background: white;
            border: 1px solid var(--accent-orange);
            color: var(--accent-orange);
        }

        .status-badge.pendente {
            background: white;
            border: 1px solid var(--gray-400);
            color: var(--gray-600);
        }

        /* Simple tables for electives/free/extra - Enhanced */
        .simple-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-bottom: 6px;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            page-break-inside: avoid;
        }

        .simple-table th {
            background: white;
            border: 1px solid var(--gray-400);
            padding: 3px;
            text-align: center;
            font-weight: 600;
            font-size: 6.5pt;
            color: var(--gray-800);
        }

        .simple-table td {
            border: 1px solid var(--gray-300);
            padding: 3px;
            vertical-align: top;
            font-size: 6pt;
            min-height: 25px;
            background: white;
        }

        /* Blocos-specific styles */
        .bloco-container {
            margin-bottom: 10px;
            padding: 6px;
            border: 1px solid var(--gray-300);
            border-radius: 4px;
            background: white;
            page-break-inside: avoid;
        }

        .bloco-title {
            font-size: 7.5pt;
            font-weight: 600;
            color: var(--primary-blue);
            margin-bottom: 4px;
        }

        .bloco-summary {
            font-size: 6pt;
            margin: 3px 0;
            padding: 2px 0;
            color: var(--gray-700);
        }

        .bloco-summary strong {
            font-weight: 600;
            color: var(--gray-900);
        }

        .bloco-disciplinas-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 4px;
            border-radius: 4px;
            overflow: hidden;
        }

        .bloco-disciplinas-table td {
            border: 1px solid var(--gray-300);
            padding: 3px;
            font-size: 6pt;
            background: white;
        }

        /* Complementary Information (Blocos Details) - MAP style */
        .supplementary-container {
            margin-bottom: 10px;
            padding: 6px;
            border: 1px solid var(--gray-300);
            border-radius: 4px;
            background: white;
            page-break-inside: avoid;
        }

        .supplementary-title {
            font-size: 7.5pt;
            font-weight: 600;
            color: var(--primary-blue);
            margin-bottom: 4px;
        }

        .supplementary-description {
            font-size: 6pt;
            color: var(--gray-600);
            margin-bottom: 6px;
            font-style: italic;
        }

        .subsection-title {
            font-size: 7.5pt;
            font-weight: 600;
            color: var(--gray-800);
            margin-top: 6px;
            margin-bottom: 3px;
        }

        .trilha-summary {
            font-size: 6pt;
            margin: 3px 0;
            padding: 2px 0;
            color: var(--gray-700);
        }

        .trilha-summary strong {
            font-weight: 600;
            color: var(--gray-900);
        }

        /* Credit Consolidation - Print-Friendly Design */
        .consolidacao-section {
            background: white;
            padding: 8px;
            border-radius: 6px;
            margin: 8px 0;
            border: 2px solid var(--primary-blue);
            page-break-inside: avoid;
        }

        .consolidacao-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 6px;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        .consolidacao-table th {
            background: white;
            color: var(--primary-blue);
            padding: 4px;
            text-align: center;
            font-weight: 600;
            font-size: 6.5pt;
            border: 1px solid var(--gray-400);
        }

        .consolidacao-table td {
            border: 1px solid var(--gray-300);
            padding: 4px;
            text-align: center;
            font-size: 6.5pt;
            background: white;
        }

        .consolidacao-table td:first-child {
            background: white;
            font-weight: 600;
            text-align: left;
            padding-left: 8px;
        }

        .credit-value {
            font-weight: 600;
            color: var(--primary-blue);
        }

        .credit-value.complete {
            color: var(--accent-green);
        }

        .credit-value.incomplete {
            color: var(--accent-red);
        }

        /* Parecer section - Enhanced Card */
        .parecer {
            background: white;
            border: 2px solid var(--primary-blue);
            border-radius: 6px;
            padding: 8px;
            margin-top: 10px;
            page-break-inside: avoid;
        }

        .parecer-checkbox {
            margin: 6px 0;
            padding: 4px 8px;
            background: white;
            border: 1px solid var(--gray-300);
            border-radius: 3px;
            font-size: 6.5pt;
            font-weight: 500;
        }

        .parecer-observacoes {
            margin-top: 6px;
        }

        .parecer-observacoes strong {
            color: var(--primary-blue);
            font-size: 6.5pt;
        }

        .parecer-input-area {
            border: 1px solid var(--gray-300);
            border-radius: 3px;
            height: 30px;
            margin-top: 3px;
            background: white;
        }

        .parecer-assinatura {
            margin-top: 8px;
        }

        .parecer-assinatura strong {
            color: var(--primary-blue);
            font-size: 6.5pt;
        }

        .assinatura-line {
            border-bottom: 1px solid var(--gray-400);
            height: 20px;
            width: 300px;
            margin-top: 3px;
            background: white;
        }

        /* Footer - Modern Minimal */
        .footer {
            position: fixed;
            bottom: 8px;
            right: 12px;
            font-size: 5.5pt;
            color: var(--gray-600);
            background: white;
            padding: 4px 8px;
            border-radius: 8px;
            border: 1px solid var(--gray-300);
        }

        /* Page Break Controls */
        .page-break-avoid {
            page-break-inside: avoid;
            break-inside: avoid;
        }

        .page-break-after-avoid {
            page-break-after: avoid;
            break-after: avoid;
        }

        .page-break-before-avoid {
            page-break-before: avoid;
            break-before: avoid;
        }

        .page-break-before {
            page-break-before: always;
            break-before: always;
        }

        /* Keep section title with its content */
        .section-with-content {
            page-break-inside: avoid;
        }

        /* Utility Classes */
        .text-muted {
            color: var(--gray-600);
        }

        .text-primary {
            color: var(--primary-blue);
        }

        .text-success {
            color: var(--accent-green);
        }

        .text-warning {
            color: var(--accent-orange);
        }

        .font-weight-bold {
            font-weight: 600;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{{ __('Student Evolution in Course') }}</h1>
        <div class="header-info">
            <strong>{{ __('Student') }}:</strong> {{ $dados->aluno['codpes'] }} - {{ $dados->aluno['nompes'] }}
            <span class="header-badge">{{ __('Program') }} {{ $dados->aluno['codpgm'] ?? '-' }}</span>
            <strong style="margin-left: 16px;">{{ __('Admission') }}:</strong> {{ $dados->aluno['dtainivin'] ? \Carbon\Carbon::parse($dados->aluno['dtainivin'])->format('d/m/Y') : '-' }}
            <strong style="margin-left: 16px;">{{ __('Status') }}:</strong> {{ $dados->aluno['stapgm'] ?? '-' }}
            <strong style="margin-left: 16px;">{{ __('Studying') }}:</strong> {{ __(':period period', ['period' => $dados->semestreEstagio]) }}
        </div>
        <div class="header-info">
            <strong>{{ __('Course') }}:</strong> {{ $dados->aluno['codcur'] }} - {{ $dados->aluno['nomcur'] }}
            @if($dados->aluno['nomhab'])
                <span class="header-badge">{{ $dados->aluno['nomhab'] }}</span>
            @endif
            <strong style="margin-left: 16px;">{{ __('Curriculum') }}:</strong> {{ $dados->curriculo['codcrl'] }}
            <strong style="margin-left: 16px;">{{ __('Validity') }}:</strong>
            @if(isset($dados->curriculo['curriculo']['dtainicrl']))
                {{ \Carbon\Carbon::parse($dados->curriculo['curriculo']['dtainicrl'])->format('d/m/Y') }}
            @endif
            -
            @if(isset($dados->curriculo['curriculo']['dtafimcrl']))
                {{ \Carbon\Carbon::parse($dados->curriculo['curriculo']['dtafimcrl'])->format('d/m/Y') }}
            @endif
        </div>
    </div>

    <!-- Mandatory Courses Grid -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Mandatory Courses') }}</div>
    <table class="grid-semestres">
        <tbody>
            @for($sem = 1; $sem <= ($dados->curriculo['curriculo']['duracao_ideal'] ?? 8); $sem++)
                <tr>
                    <th style="width: 5%">{{ $sem }}º</th>
                    @if(isset($dados->disciplinasPorSemestre[$sem]) && $dados->disciplinasPorSemestre[$sem]->isNotEmpty())
                        @php
                            // Ordenar disciplinas por status: A, EQ, D, MA, vazio
                            $disciplinasOrdenadas = $dados->disciplinasPorSemestre[$sem]->sortBy(function($disc) {
                                if ($disc['rstfim'] === 'A') return 1;
                                if (str_starts_with($disc['rstfim'] ?? '', 'EQ')) return 2;
                                if ($disc['rstfim'] === 'D') return 3;
                                if (($disc['rstfim'] === null || $disc['rstfim'] === '') && !empty($disc['codtur'])) return 4;
                                return 5; // pendente
                            });
                        @endphp
                        @foreach($disciplinasOrdenadas as $disc)
                            @php
                                $statusClass = 'pendente';
                                $statusLabel = '';

                                if ($disc['rstfim'] === 'A') {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'A';
                                } elseif ($disc['rstfim'] === 'D') {
                                    $statusClass = 'dispensada';
                                    $statusLabel = 'AE';
                                } elseif (($disc['rstfim'] === null || $disc['rstfim'] === '') && !empty($disc['codtur'])) {
                                    $statusClass = 'cursando';
                                    $statusLabel = 'MA';
                                } elseif (str_starts_with($disc['rstfim'], 'EQ')) {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'EQ';
                                }
                            @endphp
                            <td style="width: 15.83%">
                                <div class="disciplina-item {{ $statusClass }}">
                                    <div>
                                        <span class="disciplina-codigo">{{ $disc['coddis'] }}</span>
                                        <span class="disciplina-creditos">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</span>
                                    </div>
                                    @if($statusLabel || !empty($disc['codtur']) || !empty($disc['discrl']))
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['codtur']))
                                                {{ $disc['codtur'] }}
                                            @endif
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}]
                                            @endif
                                            @if($statusLabel)
                                                <span class="status-badge {{ $statusClass }}">{{ $statusLabel }}</span>
                                            @endif
                                        </div>
                                    @endif
                                </div>
                            </td>
                        @endforeach
                        {{-- Fill remaining cells --}}
                        @for($i = $disciplinasOrdenadas->count(); $i < 6; $i++)
                            <td style="width: 15.83%">&nbsp;</td>
                        @endfor
                    @else
                        {{-- Empty semester --}}
                        @for($i = 0; $i < 6; $i++)
                            <td style="width: 15.83%">&nbsp;</td>
                        @endfor
                    @endif
                </tr>
            @endfor
        </tbody>
    </table>
    </div>

    <!-- Elective Courses -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Elective Courses') }}</div>
    <table class="simple-table">
        <tbody>
            @if($dados->disciplinasEletivas->isNotEmpty())
                @php
                    // Ordenar por status: A, EQ, D, MA, vazio
                    $disciplinasOrdenadas = $dados->disciplinasEletivas->sortBy(function($disc) {
                        if ($disc['rstfim'] === 'A') return 1;
                        if (str_starts_with($disc['rstfim'] ?? '', 'EQ')) return 2;
                        if ($disc['rstfim'] === 'D') return 3;
                        if ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) return 4;
                        return 5; // pendente
                    });
                @endphp
                @foreach($disciplinasOrdenadas->chunk(6) as $chunk)
                    <tr>
                        @foreach($chunk as $disc)
                            @php
                                $statusClass = 'pendente';
                                $statusLabel = '';

                                if ($disc['rstfim'] === 'A') {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'A';
                                } elseif ($disc['rstfim'] === 'D') {
                                    $statusClass = 'dispensada';
                                    $statusLabel = 'D';
                                } elseif ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) {
                                    $statusClass = 'cursando';
                                    $statusLabel = 'MA';
                                } elseif (str_starts_with($disc['rstfim'] ?? '', 'EQ')) {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'EQ';
                                }
                            @endphp
                            <td style="width: 16.66%">
                                <div class="disciplina-item {{ $statusClass }}">
                                    <div>
                                        <span class="disciplina-codigo">{{ $disc['coddis'] }}</span>
                                        <span class="disciplina-creditos">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</span>
                                    </div>
                                    @if($statusLabel || !empty($disc['codtur']) || !empty($disc['discrl']))
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['codtur']))
                                                {{ $disc['codtur'] }}
                                            @endif
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}]
                                            @endif
                                            @if($statusLabel)
                                                <span class="status-badge {{ $statusClass }}">{{ $statusLabel }}</span>
                                            @endif
                                        </div>
                                    @endif
                                </div>
                            </td>
                        @endforeach
                        {{-- Fill remaining cells in this row --}}
                        @for($i = $chunk->count(); $i < 6; $i++)
                            <td style="width: 16.66%">&nbsp;</td>
                        @endfor
                    </tr>
                @endforeach
            @else
                <tr>
                    <td colspan="6" style="text-align: center; font-style: italic; padding: 6px;">{{ __('No elective courses completed') }}</td>
                </tr>
            @endif
        </tbody>
    </table>
    </div>

    <!-- Free Elective Courses -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Free Elective Courses') }}</div>
    <table class="simple-table">
        <tbody>
            @if($dados->disciplinasLivres->isNotEmpty())
                @php
                    // Ordenar por status: A, EQ, D, MA, vazio
                    $disciplinasOrdenadasLivres = $dados->disciplinasLivres->sortBy(function($disc) {
                        if ($disc['rstfim'] === 'A') return 1;
                        if (str_starts_with($disc['rstfim'] ?? '', 'EQ')) return 2;
                        if ($disc['rstfim'] === 'D') return 3;
                        if ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) return 4;
                        return 5; // pendente
                    });
                @endphp
                @foreach($disciplinasOrdenadasLivres->chunk(6) as $chunk)
                    <tr>
                        @foreach($chunk as $disc)
                            @php
                                $statusClass = 'pendente';
                                $statusLabel = '';

                                if ($disc['rstfim'] === 'A') {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'A';
                                } elseif ($disc['rstfim'] === 'D') {
                                    $statusClass = 'dispensada';
                                    $statusLabel = 'D';
                                } elseif ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) {
                                    $statusClass = 'cursando';
                                    $statusLabel = 'MA';
                                } elseif (str_starts_with($disc['rstfim'] ?? '', 'EQ')) {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'EQ';
                                }
                            @endphp
                            <td style="width: 16.66%">
                                <div class="disciplina-item {{ $statusClass }}">
                                    <div>
                                        <span class="disciplina-codigo">{{ $disc['coddis'] }}</span>
                                        <span class="disciplina-creditos">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</span>
                                    </div>
                                    @if($statusLabel || !empty($disc['codtur']) || !empty($disc['discrl']))
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['codtur']))
                                                {{ $disc['codtur'] }}
                                            @endif
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}]
                                            @endif
                                            @if($statusLabel)
                                                <span class="status-badge {{ $statusClass }}">{{ $statusLabel }}</span>
                                            @endif
                                        </div>
                                    @endif
                                </div>
                            </td>
                        @endforeach
                        {{-- Fill remaining cells in this row --}}
                        @for($i = $chunk->count(); $i < 6; $i++)
                            <td style="width: 16.66%">&nbsp;</td>
                        @endfor
                    </tr>
                @endforeach
            @else
                <tr>
                    <td colspan="6" style="text-align: center; font-style: italic; padding: 6px;">{{ __('No free elective courses completed') }}</td>
                </tr>
            @endif
        </tbody>
    </table>
    </div>

    <!-- Out of Curriculum Courses -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Out of Curriculum Courses') }}</div>
    <table class="simple-table">
        <tbody>
            @if($dados->disciplinasExtraCurriculares->isNotEmpty())
                @php
                    // Ordenar por status: A, EQ, D, MA, vazio
                    $disciplinasOrdenadasExtra = $dados->disciplinasExtraCurriculares->sortBy(function($disc) {
                        if ($disc['rstfim'] === 'A') return 1;
                        if (str_starts_with($disc['rstfim'] ?? '', 'EQ')) return 2;
                        if ($disc['rstfim'] === 'D') return 3;
                        if ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) return 4;
                        return 5; // pendente
                    });
                @endphp
                @foreach($disciplinasOrdenadasExtra->chunk(6) as $chunk)
                    <tr>
                        @foreach($chunk as $disc)
                            @php
                                $statusClass = 'pendente';
                                $statusLabel = '';

                                if ($disc['rstfim'] === 'A') {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'A';
                                } elseif ($disc['rstfim'] === 'D') {
                                    $statusClass = 'dispensada';
                                    $statusLabel = 'D';
                                } elseif ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) {
                                    $statusClass = 'cursando';
                                    $statusLabel = 'MA';
                                } elseif (str_starts_with($disc['rstfim'] ?? '', 'EQ')) {
                                    $statusClass = 'aprovada';
                                    $statusLabel = 'EQ';
                                }
                            @endphp
                            <td style="width: 16.66%">
                                <div class="disciplina-item {{ $statusClass }}">
                                    <div>
                                        <span class="disciplina-codigo">{{ $disc['coddis'] }}</span>
                                        <span class="disciplina-creditos">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</span>
                                    </div>
                                    @if($statusLabel || !empty($disc['codtur']) || !empty($disc['discrl']))
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['codtur']))
                                                {{ $disc['codtur'] }}
                                            @endif
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}]
                                            @endif
                                            @if($statusLabel)
                                                <span class="status-badge {{ $statusClass }}">{{ $statusLabel }}</span>
                                            @endif
                                        </div>
                                    @endif
                                </div>
                            </td>
                        @endforeach
                        {{-- Fill remaining cells in this row --}}
                        @for($i = $chunk->count(); $i < 6; $i++)
                            <td style="width: 16.66%">&nbsp;</td>
                        @endfor
                    </tr>
                @endforeach
            @else
                <tr>
                    <td colspan="6" style="text-align: center; font-style: italic; padding: 6px;">{{ __('No courses outside curriculum') }}</td>
                </tr>
            @endif
        </tbody>
    </table>
    </div>

    <!-- Blocos Section (specific to course 45024) -->
    @if($dados->blocos && $dados->blocos->isNotEmpty())
    <div class="section-with-content">
        <div class="section-title">{{ __('Course Requirement Blocks') }}</div>

        @foreach($dados->blocos as $bloco)
        <div class="bloco-container">
            <div class="bloco-title">{{ $bloco['nome'] }}</div>

            @if($bloco['disciplinas_cursadas']->isNotEmpty())
                <table class="bloco-disciplinas-table">
                    <tbody>
                        @foreach($bloco['disciplinas_cursadas']->chunk(3) as $chunk)
                            <tr>
                                @foreach($chunk as $disc)
                                    <td style="width: 33.33%">
                                        <div class="disciplina-item aprovada">
                                            <span class="disciplina-codigo">{{ $disc['coddis'] }}</span>
                                            <span class="disciplina-creditos">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</span>
                                        </div>
                                    </td>
                                @endforeach
                                {{-- Fill remaining cells in this row --}}
                                @for($i = $chunk->count(); $i < 3; $i++)
                                    <td style="width: 33.33%">&nbsp;</td>
                                @endfor
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            @else
                <div class="bloco-summary" style="font-style: italic; color: var(--gray-600);">
                    {{ __('No courses completed in this block') }}
                </div>
            @endif

            <div class="bloco-summary">
                <strong>{{ __('Credits Obtained') }}:</strong>
                {{ __('Class') }} {{ $bloco['creditos_obtidos']['aula'] }}/{{ $bloco['creditos_exigidos']['aula'] }},
                {{ __('Work') }} {{ $bloco['creditos_obtidos']['trabalho'] }}/{{ $bloco['creditos_exigidos']['trabalho'] }}
            </div>
        </div>
        @endforeach
    </div>
    @endif

    <!-- Credit Consolidation -->
    <div class="page-break-avoid">
    <div class="consolidacao-section">
        <div class="section-title" style="margin-top: 0;">{{ __('Credit Consolidation') }}</div>

        <table class="consolidacao-table">
            <thead>
                <tr>
                    <th rowspan="2" style="width: 15%;">{{ __('Credits') }}</th>
                    <th colspan="2">{{ __('Mandatory') }}</th>
                    <th colspan="2">{{ __('Elective') }}</th>
                    <th colspan="2">{{ __('Free Elective') }}</th>
                </tr>
                <tr>
                    <th>{{ __('Obtained') }}</th>
                    <th>{{ __('Required') }}</th>
                    <th>{{ __('Obtained') }}</th>
                    <th>{{ __('Required') }}</th>
                    <th>{{ __('Obtained') }}</th>
                    <th>{{ __('Required') }}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{{ __('Class') }}</td>
                    <td><span class="credit-value">{{ $dados->creditosObrigatorios['aula'] }}</span></td>
                    <td>{{ $dados->creditosObrigatorios['exigidos_aula'] }}</td>
                    <td><span class="credit-value">{{ $dados->creditosEletivos['aula'] }}</span></td>
                    <td>{{ $dados->creditosEletivos['exigidos_aula'] }}</td>
                    <td><span class="credit-value">{{ $dados->creditosLivres['aula'] }}</span></td>
                    <td>{{ $dados->creditosLivres['exigidos_aula'] }}</td>
                </tr>
                <tr>
                    <td>{{ __('Work') }}</td>
                    <td><span class="credit-value">{{ $dados->creditosObrigatorios['trabalho'] }}</span></td>
                    <td>{{ $dados->creditosObrigatorios['exigidos_trabalho'] }}</td>
                    <td><span class="credit-value">{{ $dados->creditosEletivos['trabalho'] }}</span></td>
                    <td>{{ $dados->creditosEletivos['exigidos_trabalho'] }}</td>
                    <td><span class="credit-value">{{ $dados->creditosLivres['trabalho'] }}</span></td>
                    <td>{{ $dados->creditosLivres['exigidos_trabalho'] }}</td>
                </tr>
            </tbody>
        </table>

    </div>
    </div>

    <!-- Course Coordination Review -->
    <div class="parecer">
        <div class="section-title" style="margin-top: 0;">{{ __('Course Coordination Review') }}</div>
        <div class="parecer-checkbox">
            {{ __('All requirements for course completion were met') }} ( ) {{ __('Yes') }} ( ) {{ __('No') }}
        </div>
        <div class="parecer-observacoes">
            <strong>{{ __('Observations') }}:</strong>
            <div class="parecer-input-area"></div>
        </div>
        <div class="parecer-assinatura">
            <strong>{{ __('Date and Signature') }}:</strong>
            <div class="assinatura-line"></div>
        </div>
    </div>

    <!-- NEW PAGE: Complementary Information (Blocos Details) -->
    @if($dados->blocos && $dados->blocos->isNotEmpty())
    <div class="page-break-before">
        <!-- Header repeated on new page -->
        <div class="header">
            <h1>{{ __('Complementary Information') }}</h1>
            <div class="header-info">
                <strong>{{ __('Student') }}:</strong> {{ $dados->aluno['codpes'] }} - {{ $dados->aluno['nompes'] }}
            </div>
        </div>

        @foreach($dados->blocos as $bloco)
        <!-- Supplementary Information Section for each Bloco -->
        <div class="supplementary-container">
            <div class="supplementary-title">{{ __('Block') }}: {{ $bloco['nome'] }}</div>
            <div class="supplementary-description">
                {{ __('Courses completed in this block by the student.') }}
            </div>

            <!-- Bloco Courses Detail -->
            @if($bloco['disciplinas_cursadas']->isNotEmpty())
                <table class="simple-table">
                    <thead>
                        <tr>
                            <th style="width: 15%">{{ __('Course Code') }}</th>
                            <th style="width: 45%">{{ __('Course Name') }}</th>
                            <th style="width: 12%">{{ __('Credits') }}</th>
                            <th style="width: 10%">{{ __('Period') }}</th>
                            <th style="width: 18%">{{ __('Status') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($bloco['disciplinas_cursadas'] as $disc)
                            @php
                                $statusClass = 'pendente';
                                $statusLabel = __('Pending');

                                if ($disc['rstfim'] === 'A') {
                                    $statusClass = 'aprovada';
                                    $statusLabel = __('Approved');
                                } elseif ($disc['rstfim'] === 'D') {
                                    $statusClass = 'dispensada';
                                    $statusLabel = __('Dispensed');
                                } elseif ($disc['rstfim'] === 'MA' || (empty($disc['rstfim']) && !empty($disc['codtur']))) {
                                    $statusClass = 'cursando';
                                    $statusLabel = __('Enrolled');
                                } elseif (str_starts_with($disc['rstfim'] ?? '', 'EQ')) {
                                    $statusClass = 'aprovada';
                                    $statusLabel = __('Equivalent');
                                }
                            @endphp
                            <tr>
                                <td style="font-weight: 600;">{{ $disc['coddis'] }}</td>
                                <td>{{ $disc['nomdis'] ?? '-' }}</td>
                                <td style="text-align: center;">{!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}</td>
                                <td style="text-align: center;">{{ $disc['codtur'] ?? '-' }}</td>
                                <td style="text-align: center;">
                                    <span class="status-badge {{ $statusClass }}">{{ $statusLabel }}</span>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            @else
                <div style="font-style: italic; color: var(--gray-600); font-size: 6pt; padding: 6px;">
                    {{ __('No courses completed in this block') }}
                </div>
            @endif

            <!-- Bloco Status Summary -->
            <div class="trilha-summary">
                <strong>{{ __('Credits Obtained') }}:</strong>
                {{ __('Class') }} {{ $bloco['creditos_obtidos']['aula'] }}/{{ $bloco['creditos_exigidos']['aula'] }},
                {{ __('Work') }} {{ $bloco['creditos_obtidos']['trabalho'] }}/{{ $bloco['creditos_exigidos']['trabalho'] }}
            </div>
        </div>
        @endforeach
    </div>
    @endif

    <!-- Footer -->
    <div class="footer">
        Sistema Europa • {{ now()->format('d/m/Y H:i') }}
    </div>
</body>
</html>
