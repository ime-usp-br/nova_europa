{{-- resources/views/components/usp/header.blade.php --}}
<header class="bg-white dark:bg-gray-800 shadow-sm">
    {{-- Parte Superior com Logos --}}
    <div class="max-w-7xl mx-auto px-4 hidden sm:block lg:px-8">
        <div class="flex justify-between items-center py-3">
            {{-- Logo USP Imagem --}}
            <div class="flex-shrink-0 hidden sm:block">
                {{-- AC8: Adicionado seletor dusk --}}
                <a href="http://www.usp.br" target="_blank" title="Portal da USP" dusk="usp-logo">
                    <img src="{{ Vite::asset('resources/images/usp/usp-logo.png') }}"
                         width="122" height="49" alt="Logotipo da Universidade de São Paulo"
                         class="h-12 w-auto">
                </a>
            </div>

            {{-- Logo USP Texto --}}
            <div class="hidden sm:block flex-shrink-0 ml-4">
                <a href="http://www.usp.br" target="_blank" title="Universidade de São Paulo">
                    <img src="{{ Vite::asset('resources/images/usp/usp-logo-texto.png') }}"
                         alt="Universidade de São Paulo"
                         class="h-11 w-auto">
                </a>
            </div>

            {{-- Espaço Flexível --}}
            <div class="flex-grow"></div>

            {{-- Conteúdo Adicional Direita (Links Usuário, etc.) --}}
            <div class="flex items-center">
                {{-- Links de usuário aqui, se houver --}}
            </div>
        </div>
    </div>


    {{-- Container para as Faixas Coloridas e Nome da Aplicação --}}
    <div class="relative w-full"> {{-- Adicionado 'relative' aqui --}}
        @php
            $faixaHeightPx = 8; // <<< Pode ser maior que 7 agora
            $faixaInferiorHeightPx = $faixaHeightPx + 8;
        @endphp

        {{-- Faixa 1 (Superior) - Amarela --}}
        <div class="w-full bg-usp-yellow" style="height: {{ $faixaHeightPx }}px;"></div> {{-- Usando style --}}
        {{-- Faixa 2 (Meio) - Azul Secundário --}}
        <div class="w-full bg-usp-blue-sec" style="height: {{ $faixaHeightPx }}px;"></div> {{-- Usando style --}}
        {{-- Faixa 3 (Inferior) - Azul Primário (Mais alta) --}}
        <div class="w-full bg-usp-blue-pri" style="height: {{ $faixaInferiorHeightPx }}px;"></div> {{-- Usando style --}}

        {{-- Nome da Aplicação Posicionado Absolutamente --}}
        <div class="absolute bottom-0 right-4 sm:right-6 lg:right-8">
             <span class="font-sans text-xs text-white">
                 {{ config('app.name', 'Laravel') }}
             </span>
        </div>
    </div>

</header>