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

        /* Progress Bar for Credits */
        .progress-container {
            margin-top: 4px;
        }

        .progress-label {
            font-size: 6pt;
            color: var(--gray-700);
            margin-bottom: 2px;
            display: flex;
            justify-content: space-between;
        }

        .progress-bar {
            height: 8px;
            background: var(--gray-200);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
        }

        .progress-fill {
            height: 100%;
            background: var(--accent-green);
            border-radius: 4px;
            transition: width 0.3s;
        }

        .progress-fill.warning {
            background: var(--accent-orange);
        }

        .progress-fill.danger {
            background: var(--accent-red);
        }

        /* Parecer section - Enhanced Card */
        .parecer {
            background: white;
            border: 1px solid var(--gray-300);
            border-radius: 6px;
            padding: 8px;
            margin-top: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
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
            @for($sem = 1; $sem <= 8; $sem++)
                <tr>
                    <th style="width: 5%">{{ $sem }}º</th>
                    @if(isset($dados->disciplinasPorSemestre[$sem]) && $dados->disciplinasPorSemestre[$sem]->isNotEmpty())
                        @foreach($dados->disciplinasPorSemestre[$sem] as $disc)
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
                        @for($i = $dados->disciplinasPorSemestre[$sem]->count(); $i < 6; $i++)
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
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td style="width: 16.66%">&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>
    </div>

    <!-- Free Elective Courses -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Free Elective Courses') }}</div>
    <table class="simple-table">
        <tbody>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td style="width: 16.66%">&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>
    </div>

    <!-- Out of Curriculum Courses -->
    <div class="section-with-content">
    <div class="section-title">{{ __('Out of Curriculum Courses') }}</div>
    <table class="simple-table">
        <tbody>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td style="width: 16.66%">&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>
    </div>

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

        @php
            $percObrigatorios = $dados->porcentagensConsolidacao['obrigatorios'] ?? 0;
            $percEletivos = $dados->porcentagensConsolidacao['eletivos'] ?? 0;
            $percLivres = $dados->porcentagensConsolidacao['livres'] ?? 0;
        @endphp

        <!-- Progress Bars -->
        <div class="progress-container">
            <div class="progress-label">
                <span><strong>{{ __('Mandatory') }}:</strong> {{ number_format($percObrigatorios, 1) }}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {{ $percObrigatorios >= 75 ? '' : ($percObrigatorios >= 50 ? 'warning' : 'danger') }}"
                     style="width: {{ min($percObrigatorios, 100) }}%"></div>
            </div>
        </div>

        <div class="progress-container">
            <div class="progress-label">
                <span><strong>{{ __('Elective') }}:</strong> {{ number_format($percEletivos, 1) }}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {{ $percEletivos >= 75 ? '' : ($percEletivos >= 50 ? 'warning' : 'danger') }}"
                     style="width: {{ min($percEletivos, 100) }}%"></div>
            </div>
        </div>

        <div class="progress-container">
            <div class="progress-label">
                <span><strong>{{ __('Free Elective') }}:</strong> {{ number_format($percLivres, 1) }}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {{ $percLivres >= 75 ? '' : ($percLivres >= 50 ? 'warning' : 'danger') }}"
                     style="width: {{ min($percLivres, 100) }}%"></div>
            </div>
        </div>
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

    <!-- Footer -->
    <div class="footer">
        Sistema Europa • {{ now()->format('d/m/Y H:i') }}
    </div>
</body>
</html>
