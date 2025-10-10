{{-- Header USP otimizado para Filament --}}
<header style="background-color: white; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);">
    <style>
        .dark header {
            background-color: #1f2937 !important;
        }

        /* Container dos logos */
        .usp-logos-container {
            max-width: 80rem;
            margin-left: auto;
            margin-right: auto;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Padding responsivo igual ao header da home: px-4 (1rem) padrão, px-8 (2rem) em telas lg+ */
        @media (min-width: 1024px) {
            .usp-logos-container {
                padding-left: 2rem;
                padding-right: 2rem;
            }
        }

        /* Responsividade: esconde logos em telas menores que 640px (sm breakpoint) */
        @media (max-width: 639px) {
            .usp-logos-container {
                display: none !important;
            }
        }
    </style>
    {{-- Parte Superior com Logos --}}
    <div class="usp-logos-container">
        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.75rem; padding-bottom: 0.75rem;">
            {{-- Logo USP Imagem --}}
            <div style="flex-shrink: 0;">
                <a href="http://www.usp.br" target="_blank" title="Portal da USP">
                    <img src="{{ Vite::asset('resources/images/usp/usp-logo.png') }}"
                         width="122" height="49" alt="Logotipo da Universidade de São Paulo"
                         style="height: 3rem; width: auto;">
                </a>
            </div>

            {{-- Logo USP Texto --}}
            <div style="flex-shrink: 0; margin-left: 1rem;">
                <a href="http://www.usp.br" target="_blank" title="Universidade de São Paulo">
                    <img src="{{ Vite::asset('resources/images/usp/usp-logo-texto.png') }}"
                         alt="Universidade de São Paulo"
                         style="height: 2.75rem; width: auto;">
                </a>
            </div>

            {{-- Espaço Flexível - Centraliza os logos --}}
            <div style="flex-grow: 1;"></div>

            {{-- Conteúdo Adicional Direita (Links Usuário, etc.) --}}
            <div style="display: flex; align-items: center;">
                {{-- Links de usuário aqui, se houver --}}
            </div>
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

    {{-- Barra de Navegação IME + User Menu --}}
    <nav style="border-bottom: 1px solid rgb(229 231 235); background-color: white;">
        <style>
            .dark nav {
                background-color: #1f2937 !important;
                border-bottom-color: rgb(55 65 81) !important;
            }
        </style>

        <div style="max-width: 80rem; margin-left: auto; margin-right: auto; padding-left: 1rem; padding-right: 1rem;">
            <div style="display: flex; justify-content: space-between; height: 4rem;">
                {{-- Logo IME e Nome do Sistema --}}
                <div style="flex-shrink: 0; display: flex; align-items: center; gap: 0.75rem;">
                    <a href="{{ route('dashboard') }}" style="display: flex; align-items: center; gap: 0.75rem; text-decoration: none;">
                        <img src="{{ Vite::asset('resources/images/ime/logo-horizontal-simplificada-padrao.png') }}"
                             alt="Logo IME-USP"
                             style="width: 56px; height: auto; display: block;"
                             class="dark-hidden">
                        <img src="{{ Vite::asset('resources/images/ime/logo-horizontal-simplificada-branca.png') }}"
                             alt="Logo IME-USP"
                             style="width: 56px; height: auto; display: none;"
                             class="dark-block">
                        <span style="font-size: 1.125rem; font-weight: 600; color: rgb(20, 45, 105);" class="app-name-light">
                            {{ config('app.name', 'Nova Europa') }}
                        </span>
                        <span style="font-size: 1.125rem; font-weight: 600; color: white; display: none;" class="app-name-dark">
                            {{ config('app.name', 'Nova Europa') }}
                        </span>
                    </a>
                    <style>
                        .dark .dark-hidden { display: none !important; }
                        .dark .dark-block { display: block !important; }
                        .dark .app-name-light { display: none !important; }
                        .dark .app-name-dark { display: block !important; }
                    </style>
                </div>

                {{-- User Menu Dropdown --}}
                <div style="display: flex; align-items: center; margin-left: 1.5rem;" x-data="{ open: false }">
                    <div style="position: relative;">
                        <button @click="open = ! open"
                                type="button"
                                style="display: inline-flex; align-items: center; padding: 0.5rem 0.75rem; border: 1px solid transparent; font-size: 0.875rem; line-height: 1.25rem; font-weight: 500; border-radius: 0.375rem; color: rgb(107 114 128); background-color: white; transition: all 0.15s ease-in-out;">
                            <style>
                                .dark button {
                                    color: rgb(156 163 175) !important;
                                    background-color: #1f2937 !important;
                                }
                                button:hover {
                                    color: rgb(55 65 81);
                                }
                                .dark button:hover {
                                    color: rgb(209 213 219) !important;
                                }
                            </style>
                            <div>{{ auth()->user()->name }}</div>
                            <div style="margin-left: 0.25rem;">
                                <svg style="fill: currentColor; height: 1rem; width: 1rem;" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                </svg>
                            </div>
                        </button>

                        <div x-show="open"
                             @click.outside="open = false"
                             x-transition:enter="transition ease-out duration-200"
                             x-transition:enter-start="opacity-0 scale-95"
                             x-transition:enter-end="opacity-100 scale-100"
                             x-transition:leave="transition ease-in duration-75"
                             x-transition:leave-start="opacity-100 scale-100"
                             x-transition:leave-end="opacity-0 scale-95"
                             style="position: absolute; right: 0; z-index: 50; margin-top: 0.5rem; width: 12rem; border-radius: 0.375rem; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1); display: none;"
                             x-cloak>
                            <style>
                                [x-cloak] { display: none !important; }
                            </style>
                            <div style="border-radius: 0.375rem; border: 1px solid rgba(0, 0, 0, 0.05); padding: 0.25rem 0; background-color: white;">
                                <style>
                                    .dark div[style*="background-color: white"] {
                                        background-color: #374151 !important;
                                    }
                                </style>

                                <a href="{{ route('profile') }}"
                                   style="display: block; width: 100%; padding: 0.5rem 1rem; text-align: left; font-size: 0.875rem; line-height: 1.25rem; color: rgb(55 65 81); transition: all 0.15s ease-in-out;">
                                    <style>
                                        .dark a {
                                            color: rgb(209 213 219) !important;
                                        }
                                        a:hover {
                                            background-color: rgb(243 244 246);
                                        }
                                        .dark a:hover {
                                            background-color: rgb(75 85 99) !important;
                                        }
                                    </style>
                                    Profile
                                </a>

                                <a href="{{ route('dashboard') }}"
                                   style="display: block; width: 100%; padding: 0.5rem 1rem; text-align: left; font-size: 0.875rem; line-height: 1.25rem; color: rgb(55 65 81); transition: all 0.15s ease-in-out;">
                                    Dashboard
                                </a>

                                <form method="POST" action="{{ route('logout') }}">
                                    @csrf
                                    <button type="submit"
                                            style="display: block; width: 100%; padding: 0.5rem 1rem; text-align: left; font-size: 0.875rem; line-height: 1.25rem; color: rgb(55 65 81); background: transparent; border: none; cursor: pointer; transition: all 0.15s ease-in-out;">
                                        Log Out
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {{-- Padding responsivo em lg+ --}}
        <style>
            @media (min-width: 1024px) {
                nav > div:first-of-type {
                    padding-left: 2rem !important;
                    padding-right: 2rem !important;
                }
            }
        </style>
    </nav>
</header>
