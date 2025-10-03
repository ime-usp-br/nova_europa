{{-- Header USP otimizado para Filament --}}
<header style="background-color: white; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);">
    <style>
        .dark header {
            background-color: #1f2937 !important;
        }
    </style>
    {{-- Parte Superior com Logos --}}
    <div style="max-width: 80rem; margin-left: auto; margin-right: auto; padding-left: 1rem; padding-right: 1rem;">
        <div style="display: flex; align-items: center; padding-top: 0.75rem; padding-bottom: 0.75rem; gap: 1rem;">
            {{-- Logo USP Imagem --}}
            <a href="http://www.usp.br" target="_blank" title="Portal da USP" style="flex-shrink: 0;">
                <img src="{{ Vite::asset('resources/images/usp/usp-logo.png') }}"
                     width="122" height="49" alt="Logotipo da Universidade de São Paulo"
                     style="height: 3rem; width: auto;">
            </a>

            {{-- Logo USP Texto --}}
            <a href="http://www.usp.br" target="_blank" title="Universidade de São Paulo" style="flex-shrink: 0;">
                <img src="{{ Vite::asset('resources/images/usp/usp-logo-texto.png') }}"
                     alt="Universidade de São Paulo"
                     style="height: 2.75rem; width: auto;">
            </a>
        </div>
    </div>

    {{-- Container para as Faixas Coloridas --}}
    <div class="w-full">
        @php
            $faixaHeightPx = 8;
            $faixaInferiorHeightPx = $faixaHeightPx + 8;
        @endphp

        {{-- Faixa 1 (Superior) - Amarela --}}
        <div class="w-full" style="height: {{ $faixaHeightPx }}px; background-color: #FCB421;"></div>
        {{-- Faixa 2 (Meio) - Azul Secundário --}}
        <div class="w-full" style="height: {{ $faixaHeightPx }}px; background-color: #64C4D2;"></div>
        {{-- Faixa 3 (Inferior) - Azul Primário (Mais alta) --}}
        <div class="w-full" style="height: {{ $faixaInferiorHeightPx }}px; background-color: #1094AB;"></div>
    </div>
</header>
