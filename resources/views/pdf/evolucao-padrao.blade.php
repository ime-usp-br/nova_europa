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
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }

        .header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #333;
        }

        .header h1 {
            font-size: 16pt;
            margin-bottom: 5px;
        }

        .header h2 {
            font-size: 12pt;
            font-weight: normal;
            color: #666;
        }

        .info-section {
            margin-bottom: 15px;
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 5px;
        }

        .info-label {
            font-weight: bold;
        }

        .section-title {
            font-size: 11pt;
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 8px;
            padding: 5px;
            background-color: #f0f0f0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }

        table th {
            background-color: #e0e0e0;
            padding: 5px;
            text-align: center;
            font-size: 9pt;
            font-weight: bold;
            border: 1px solid #999;
        }

        table td {
            padding: 5px;
            text-align: center;
            font-size: 8pt;
            border: 1px solid #ccc;
        }

        /* Color coding for courses */
        @if($colorido)
        .aprovado {
            background-color: #d6f5d6; /* Light green */
        }

        .devendo {
            background-color: #ffe6e6; /* Light red */
        }

        .cursando {
            background-color: #ffffe6; /* Light yellow */
        }
        @else
        .aprovado {
            background-color: #ffffff;
        }

        .devendo {
            background-color: #e6e6e6;
        }

        .cursando {
            background-color: #e6e6e6;
        }
        @endif

        .consolidacao {
            margin-top: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border: 1px solid #999;
        }

        .consolidacao-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            text-align: center;
        }

        .consolidacao-item {
            padding: 10px;
            border: 1px solid #ccc;
        }

        .consolidacao-item strong {
            display: block;
            font-size: 11pt;
            margin-bottom: 5px;
        }

        .consolidacao-item .percentage {
            font-size: 14pt;
            font-weight: bold;
            color: #0066cc;
        }

        .legenda {
            margin-top: 15px;
            font-size: 8pt;
            padding: 10px;
            background-color: #f9f9f9;
            border: 1px solid #ccc;
        }

        .legenda-item {
            display: inline-block;
            margin-right: 15px;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{{ __('Student Academic Evolution') }}</h1>
        <h2>{{ __('University of São Paulo - Institute of Mathematics and Statistics') }}</h2>
    </div>

    <!-- Student Information -->
    <div class="info-section">
        <div class="info-label">{{ __('Student Name') }}:</div>
        <div>{{ $dados->aluno['nompes'] }}</div>

        <div class="info-label">{{ __('USP Number') }}:</div>
        <div>{{ $dados->aluno['codpes'] }}</div>

        <div class="info-label">{{ __('Course') }}:</div>
        <div>{{ $dados->aluno['codcur'] }} - {{ $dados->aluno['nomcur'] }}</div>

        <div class="info-label">{{ __('Curriculum') }}:</div>
        <div>{{ $dados->curriculo['codcrl'] }}</div>

        <div class="info-label">{{ __('Report Date') }}:</div>
        <div>{{ now()->format('d/m/Y H:i') }}</div>
    </div>

    <!-- Mandatory Courses -->
    <div class="section-title">{{ __('Mandatory Courses') }}</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%">{{ __('Code') }}</th>
                <th style="width: 45%">{{ __('Course Name') }}</th>
                <th style="width: 10%">{{ __('Class Credits') }}</th>
                <th style="width: 10%">{{ __('Work Credits') }}</th>
                <th style="width: 20%">{{ __('Status') }}</th>
            </tr>
        </thead>
        <tbody>
            @forelse($dados->disciplinasObrigatorias as $disciplina)
            <tr class="{{ $disciplina['rstfim'] === 'A' || $disciplina['rstfim'] === 'D' ? 'aprovado' : ($disciplina['rstfim'] === 'MA' ? 'cursando' : 'devendo') }}">
                <td>{{ $disciplina['coddis'] }}</td>
                <td style="text-align: left;">{{ $disciplina['nomdis'] }}</td>
                <td>{{ $disciplina['creaul'] }}</td>
                <td>{{ $disciplina['cretrb'] }}</td>
                <td>{{ $disciplina['rstfim'] }}</td>
            </tr>
            @empty
            <tr>
                <td colspan="5">{{ __('No mandatory courses completed') }}</td>
            </tr>
            @endforelse
        </tbody>
    </table>

    <!-- Elective Courses -->
    <div class="section-title">{{ __('Elective Courses') }}</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%">{{ __('Code') }}</th>
                <th style="width: 45%">{{ __('Course Name') }}</th>
                <th style="width: 10%">{{ __('Class Credits') }}</th>
                <th style="width: 10%">{{ __('Work Credits') }}</th>
                <th style="width: 20%">{{ __('Status') }}</th>
            </tr>
        </thead>
        <tbody>
            @forelse($dados->disciplinasEletivas as $disciplina)
            <tr class="{{ $disciplina['rstfim'] === 'A' || $disciplina['rstfim'] === 'D' ? 'aprovado' : ($disciplina['rstfim'] === 'MA' ? 'cursando' : 'devendo') }}">
                <td>{{ $disciplina['coddis'] }}</td>
                <td style="text-align: left;">{{ $disciplina['nomdis'] }}</td>
                <td>{{ $disciplina['creaul'] }}</td>
                <td>{{ $disciplina['cretrb'] }}</td>
                <td>{{ $disciplina['rstfim'] }}</td>
            </tr>
            @empty
            <tr>
                <td colspan="5">{{ __('No elective courses completed') }}</td>
            </tr>
            @endforelse
        </tbody>
    </table>

    <!-- Free Elective Courses -->
    <div class="section-title">{{ __('Free Elective Courses') }}</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%">{{ __('Code') }}</th>
                <th style="width: 45%">{{ __('Course Name') }}</th>
                <th style="width: 10%">{{ __('Class Credits') }}</th>
                <th style="width: 10%">{{ __('Work Credits') }}</th>
                <th style="width: 20%">{{ __('Status') }}</th>
            </tr>
        </thead>
        <tbody>
            @forelse($dados->disciplinasLivres as $disciplina)
            <tr class="{{ $disciplina['rstfim'] === 'A' || $disciplina['rstfim'] === 'D' ? 'aprovado' : ($disciplina['rstfim'] === 'MA' ? 'cursando' : 'devendo') }}">
                <td>{{ $disciplina['coddis'] }}</td>
                <td style="text-align: left;">{{ $disciplina['nomdis'] }}</td>
                <td>{{ $disciplina['creaul'] }}</td>
                <td>{{ $disciplina['cretrb'] }}</td>
                <td>{{ $disciplina['rstfim'] }}</td>
            </tr>
            @empty
            <tr>
                <td colspan="5">{{ __('No free elective courses completed') }}</td>
            </tr>
            @endforelse
        </tbody>
    </table>

    <!-- Extra-curricular Courses -->
    @if($dados->disciplinasExtraCurriculares->isNotEmpty())
    <div class="section-title">{{ __('Extra-curricular Courses') }}</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%">{{ __('Code') }}</th>
                <th style="width: 45%">{{ __('Course Name') }}</th>
                <th style="width: 10%">{{ __('Class Credits') }}</th>
                <th style="width: 10%">{{ __('Work Credits') }}</th>
                <th style="width: 20%">{{ __('Status') }}</th>
            </tr>
        </thead>
        <tbody>
            @foreach($dados->disciplinasExtraCurriculares as $disciplina)
            <tr class="aprovado">
                <td>{{ $disciplina['coddis'] }}</td>
                <td style="text-align: left;">{{ $disciplina['nomdis'] }}</td>
                <td>{{ $disciplina['creaul'] }}</td>
                <td>{{ $disciplina['cretrb'] }}</td>
                <td>{{ $disciplina['rstfim'] }}</td>
            </tr>
            @endforeach
        </tbody>
    </table>
    @endif

    <!-- Consolidation -->
    <div class="consolidacao">
        <div class="section-title" style="margin-top: 0;">{{ __('Credit Consolidation') }}</div>
        <div class="consolidacao-grid">
            <div class="consolidacao-item">
                <strong>{{ __('Mandatory') }}</strong>
                <div>{{ __('Obtained') }}: {{ $dados->creditosObrigatorios['total'] }}</div>
                <div>{{ __('Required') }}: {{ $dados->creditosObrigatorios['exigidos_total'] }}</div>
                <div class="percentage">{{ number_format($dados->porcentagensConsolidacao['obrigatorios'], 1) }}%</div>
            </div>
            <div class="consolidacao-item">
                <strong>{{ __('Elective') }}</strong>
                <div>{{ __('Obtained') }}: {{ $dados->creditosEletivos['total'] }}</div>
                <div>{{ __('Required') }}: {{ $dados->creditosEletivos['exigidos_total'] }}</div>
                <div class="percentage">{{ number_format($dados->porcentagensConsolidacao['eletivos'], 1) }}%</div>
            </div>
            <div class="consolidacao-item">
                <strong>{{ __('Free Elective') }}</strong>
                <div>{{ __('Obtained') }}: {{ $dados->creditosLivres['total'] }}</div>
                <div>{{ __('Required') }}: {{ $dados->creditosLivres['exigidos_total'] }}</div>
                <div class="percentage">{{ number_format($dados->porcentagensConsolidacao['livres'], 1) }}%</div>
            </div>
            <div class="consolidacao-item">
                <strong>{{ __('Total') }}</strong>
                <div>{{ __('Overall Completion') }}</div>
                <div class="percentage" style="font-size: 16pt; margin-top: 5px;">{{ number_format($dados->porcentagensConsolidacao['total'], 1) }}%</div>
            </div>
        </div>
    </div>

    <!-- Legend -->
    <div class="legenda">
        <strong>{{ __('Legend') }}:</strong>
        <span class="legenda-item">A = {{ __('Approved') }}</span>
        <span class="legenda-item">D = {{ __('Waived') }}</span>
        <span class="legenda-item">MA = {{ __('Enrolled') }}</span>
        <span class="legenda-item">{{ __('EQUIVALENTE') }} = {{ __('Fulfilled by equivalence') }}</span>
    </div>
</body>
</html>
