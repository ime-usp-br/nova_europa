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

        body {
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: 8pt;
            line-height: 1.2;
            color: #000;
        }

        .header {
            margin-bottom: 10px;
        }

        .header h1 {
            font-size: 11pt;
            font-weight: bold;
            margin-bottom: 3px;
        }

        .header-info {
            font-size: 8pt;
            margin-bottom: 2px;
        }

        .header-info strong {
            font-weight: bold;
        }

        .section-title {
            font-size: 9pt;
            font-weight: bold;
            margin-top: 8px;
            margin-bottom: 4px;
        }

        /* Grid for mandatory courses (semesters) */
        .grid-semestres {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }

        .grid-semestres th {
            border: 1px solid #000;
            padding: 2px;
            text-align: center;
            font-weight: bold;
            font-size: 8pt;
            background-color: #fff;
        }

        .grid-semestres td {
            border: 1px solid #000;
            padding: 3px;
            vertical-align: top;
            font-size: 7pt;
            min-height: 40px;
        }

        .disciplina-item {
            margin-bottom: 4px;
        }

        .disciplina-codigo {
            font-weight: bold;
            font-size: 7.5pt;
        }

        .disciplina-creditos {
            font-size: 7pt;
        }

        .disciplina-turma {
            font-size: 6.5pt;
            color: #333;
        }

        /* Simple tables for electives/free/extra */
        .simple-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }

        .simple-table th {
            border: 1px solid #000;
            padding: 3px;
            text-align: center;
            font-weight: normal;
            font-size: 8pt;
            background-color: #fff;
        }

        .simple-table td {
            border: 1px solid #000;
            padding: 3px;
            vertical-align: top;
            font-size: 7pt;
            min-height: 30px;
        }

        /* Credit consolidation table */
        .consolidacao-table {
            width: 70%;
            border-collapse: collapse;
            margin: 10px 0;
        }

        .consolidacao-table th {
            border: 1px solid #000;
            padding: 4px;
            text-align: center;
            font-weight: bold;
            font-size: 8pt;
        }

        .consolidacao-table td {
            border: 1px solid #000;
            padding: 4px;
            text-align: center;
            font-size: 8pt;
        }

        /* Parecer section */
        .parecer {
            margin-top: 10px;
            font-size: 8pt;
        }

        .parecer-checkbox {
            margin: 5px 0;
        }

        .parecer-observacoes {
            margin-top: 5px;
        }

        .parecer-assinatura {
            margin-top: 10px;
        }

        /* Footer */
        .footer {
            position: fixed;
            bottom: 5px;
            right: 10px;
            font-size: 7pt;
            color: #666;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{{ __('Student Evolution in Course') }}</h1>
        <div class="header-info">
            <strong>{{ __('Student') }}:</strong> {{ $dados->aluno['codpes'] }} {{ $dados->aluno['nompes'] }}
            <strong>{{ __('Program') }}:</strong> {{ $dados->aluno['codpgm'] ?? '' }}
            <strong>{{ __('Admission') }}:</strong> {{ $dados->aluno['dtainivin'] ? \Carbon\Carbon::parse($dados->aluno['dtainivin'])->format('d/m/Y') : '' }}
            <strong>{{ __('Status') }}:</strong> {{ $dados->aluno['stapgm'] ?? '' }}
        </div>
        <div class="header-info">
            <strong>{{ __('Course') }}:</strong> {{ $dados->aluno['codcur'] }} {{ $dados->aluno['nomcur'] }}
            <strong>{{ __('Qualification') }}:</strong> {{ $dados->aluno['codhab'] ?? 0 }} {{ $dados->aluno['nomhab'] ?? '' }}
        </div>
        <div class="header-info">
            <strong>{{ __('Curriculum') }}:</strong> {{ $dados->curriculo['codcrl'] }}
            <strong>{{ __('Validity') }}:</strong>
            @if(isset($dados->curriculo['curriculo']['dtainicrl']))
                {{ \Carbon\Carbon::parse($dados->curriculo['curriculo']['dtainicrl'])->format('d/m/Y') }}
            @endif
            -
            @if(isset($dados->curriculo['curriculo']['dtafimcrl']))
                {{ \Carbon\Carbon::parse($dados->curriculo['curriculo']['dtafimcrl'])->format('d/m/Y') }}
            @endif
            <strong>{{ __('Studying') }}:</strong> {{ __(':period period (:internship for internship purposes)', ['period' => $dados->semestreEstagio, 'internship' => $dados->semestreEstagio]) }}
        </div>
    </div>

    <!-- Mandatory Courses Grid -->
    <div class="section-title">{{ __('Mandatory Courses') }}</div>
    <table class="grid-semestres">
        <tbody>
            @for($sem = 1; $sem <= 8; $sem++)
                <tr>
                    <th style="width: 5%">{{ $sem }}</th>
                    @if(isset($dados->disciplinasPorSemestre[$sem]) && $dados->disciplinasPorSemestre[$sem]->isNotEmpty())
                        @foreach($dados->disciplinasPorSemestre[$sem] as $disc)
                            @php
                                // DEBUG: Log discipline data in template
                                if ($disc['rstfim'] === null) {
                                    \Log::info('Blade template - cursando discipline', [
                                        'coddis' => $disc['coddis'],
                                        'codtur' => $disc['codtur'] ?? 'NULL',
                                        'discrl' => $disc['discrl'] ?? 'NULL',
                                        'rstfim' => $disc['rstfim'] ?? 'NULL',
                                        'codtur_empty' => empty($disc['codtur']),
                                    ]);
                                }
                            @endphp
                            <td style="width: 15.83%">
                                <div class="disciplina-item">
                                    <div class="disciplina-codigo">
                                        {{ $disc['coddis'] }} {!! '{' !!}{{ $disc['creaul'] }},{{ $disc['cretrb'] }}{!! '}' !!}
                                    </div>
                                    @if($disc['rstfim'] === null)
                                        {{-- rstfim = null: Currently enrolled OR pending --}}
                                        @if(!empty($disc['codtur']))
                                            {{-- Has codtur = currently enrolled (cursando) --}}
                                            <div class="disciplina-turma">
                                                {{ $disc['codtur'] }}
                                                @if(!empty($disc['discrl']))
                                                    [{{ $disc['discrl'] }}]
                                                @endif
                                                (Cursando)
                                            </div>
                                        @endif
                                        {{-- No codtur = pending course, no second line --}}
                                    @elseif($disc['rstfim'] === 'D')
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}] (AE)
                                            @else
                                                (AE)
                                            @endif
                                        </div>
                                    @elseif(str_starts_with($disc['rstfim'], 'EQ'))
                                        <div class="disciplina-turma">
                                            {{ $disc['rstfim'] }} (A)
                                        </div>
                                    @else
                                        {{-- A or MA - show codtur --}}
                                        <div class="disciplina-turma">
                                            @if(!empty($disc['codtur']))
                                                {{ $disc['codtur'] }}
                                            @endif
                                            @if(!empty($disc['discrl']))
                                                [{{ $disc['discrl'] }}]
                                            @endif
                                            ({{ $disc['rstfim'] }})
                                        </div>
                                    @endif
                                </div>
                            </td>
                        @endforeach
                        {{-- Fill remaining cells to complete 6 columns --}}
                        @for($i = $dados->disciplinasPorSemestre[$sem]->count(); $i < 6; $i++)
                            <td style="width: 15.83%">&nbsp;</td>
                        @endfor
                    @else
                        {{-- Empty semester - 6 empty cells --}}
                        @for($i = 0; $i < 6; $i++)
                            <td style="width: 15.83%">&nbsp;</td>
                        @endfor
                    @endif
                </tr>
            @endfor
        </tbody>
    </table>

    <!-- Elective Courses -->
    <div class="section-title">{{ __('Elective Courses') }}</div>
    <table class="simple-table">
        <thead>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <th style="width: 16.66%">&nbsp;</th>
                @endfor
            </tr>
        </thead>
        <tbody>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td>&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>

    <!-- Free Elective Courses -->
    <div class="section-title">{{ __('Free Elective Courses') }}</div>
    <table class="simple-table">
        <thead>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <th style="width: 16.66%">&nbsp;</th>
                @endfor
            </tr>
        </thead>
        <tbody>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td>&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>

    <!-- Out of Curriculum Courses -->
    <div class="section-title">{{ __('Out of Curriculum Courses') }}</div>
    <table class="simple-table">
        <thead>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <th style="width: 16.66%">&nbsp;</th>
                @endfor
            </tr>
        </thead>
        <tbody>
            <tr>
                @for($i = 0; $i < 6; $i++)
                    <td>&nbsp;</td>
                @endfor
            </tr>
        </tbody>
    </table>

    <!-- Credit Consolidation -->
    <table class="consolidacao-table">
        <thead>
            <tr>
                <th rowspan="2">{{ __('Credits') }}</th>
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
                <td><strong>{{ __('Class') }}</strong></td>
                <td>{{ $dados->creditosObrigatorios['aula'] }}</td>
                <td>{{ $dados->creditosObrigatorios['exigidos_aula'] }}</td>
                <td>{{ $dados->creditosEletivos['aula'] }}</td>
                <td>{{ $dados->creditosEletivos['exigidos_aula'] }}</td>
                <td>{{ $dados->creditosLivres['aula'] }}</td>
                <td>{{ $dados->creditosLivres['exigidos_aula'] }}</td>
            </tr>
            <tr>
                <td><strong>{{ __('Work') }}</strong></td>
                <td>{{ $dados->creditosObrigatorios['trabalho'] }}</td>
                <td>{{ $dados->creditosObrigatorios['exigidos_trabalho'] }}</td>
                <td>{{ $dados->creditosEletivos['trabalho'] }}</td>
                <td>{{ $dados->creditosEletivos['exigidos_trabalho'] }}</td>
                <td>{{ $dados->creditosLivres['trabalho'] }}</td>
                <td>{{ (int) ($dados->creditosLivres['exigidos_trabalho']) }}</td>
            </tr>
        </tbody>
    </table>

    <!-- Course Coordination Review -->
    <div class="parecer">
        <div class="section-title">{{ __('Course Coordination Review') }}</div>
        <div class="parecer-checkbox">
            {{ __('All requirements for course completion were met') }} ( ) {{ __('Yes') }} ( ) {{ __('No') }}
        </div>
        <div class="parecer-observacoes">
            <strong>{{ __('Observations') }}:</strong>
            <div style="border-bottom: 1px solid #000; height: 40px;"></div>
        </div>
        <div class="parecer-assinatura">
            <strong>{{ __('Date and Signature') }}:</strong>
            <div style="border-bottom: 1px solid #000; height: 20px; width: 300px;"></div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        Sistema Europa - {{ now()->format('d/m/Y H:i:s') }}
    </div>
</body>
</html>
