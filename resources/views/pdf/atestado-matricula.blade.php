<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atestado de Matrícula</title>
    <style>
        @page {
            margin: 0;
        }
        body {
            font-family: "Times New Roman", Times, serif;
            margin: 0;
            padding: 0;
        }
        .container {
            padding: 2.5cm;
            position: relative;
            min-height: 29.7cm; /* A4 height */
            box-sizing: border-box;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-bottom: 2cm;
        }
        .header .logo-ime {
            width: 150px;
        }
        .header .logo-usp {
            width: 100px;
        }
        .content {
            text-align: center;
        }
        .title {
            font-size: 17pt;
            font-weight: bold;
            letter-spacing: 3px;
            text-align: center;
            margin-bottom: 3cm;
        }
        .body-text {
            font-size: 14pt;
            text-align: justify;
            line-height: 1.5;
            margin-left: 25px;
            margin-right: 25px;
            text-indent: 3cm;
        }
        .body-text .bold {
            font-weight: bold;
        }
        .body-text .italic {
            font-style: italic;
        }
        .date-section {
            text-align: center;
            font-size: 14pt;
            margin-top: 5cm;
        }
        .footer {
            position: absolute;
            bottom: 1cm;
            left: 2.5cm;
            right: 2.5cm;
            text-align: left;
            font-size: 8pt;
            color: rgb(20, 45, 105);
            border-top: none;
            padding-top: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{ Vite::asset('resources/images/ime/logo-horizontal-simplificada-padrao2.png') }}" alt="IME Logo" class="logo-ime">
            <img src="{{ Vite::asset('resources/images/usp/usp-logo-azul.png') }}" alt="USP Logo" class="logo-usp">
        </div>

        <div class="content">
            <div class="title">A&nbsp;&nbsp;T&nbsp;&nbsp;E&nbsp;&nbsp;S&nbsp;&nbsp;T&nbsp;&nbsp;A&nbsp;&nbsp;D&nbsp;&nbsp;O</div>

            <div class="body-text">
                ATESTO, para os devidos fins, que <span class="bold">{{ $aluno->nompes }}</span>,
                {{ $aluno->tipdocidf }} {{ $aluno->numdocidf }} ({{ $aluno->sglorgexdidf }}-{{ $aluno->sglorgexdidf }})
                e Nº USP {{ $aluno->codpes }} é aluno regularmente matriculado neste semestre letivo,
                cursando o {{ $semestreEstagio }}º período do curso
                <span class="italic">{{ $aluno->nomcur }}</span>,
                com duração ideal de {{ $aluno->duridlcur }} semestres.
            </div>

            <div class="date-section">
                São Paulo, {{ $dataPorExtenso }}
            </div>
        </div>

        <div class="footer">
            SERVIÇO DE ALUNOS DE GRADUAÇÃO<br>
            Instituto de Matemática, Estatística e Ciência da Computação<br>
            Universidade de São Paulo<br>
            Rua do Matão, 1010, Cidade Universitária, São Paulo/SP - 05508-090<br>
            Telefone: (11) 3091.6191 / 6149 / 6279 / 6256 / 6260 / 6175 | saol@ime.usp.br | www.ime.usp.br
        </div>
    </div>
</body>
</html>
