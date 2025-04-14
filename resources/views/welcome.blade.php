<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        {{-- Título da Página - Pode usar o nome da aplicação do .env --}}
        <title>{{ config('app.name', 'Laravel') }} - Bem-vindo(a)</title>

        <!-- Fonts -->
        <link rel="preconnect" href="https://fonts.bunny.net">
        <link href="https://fonts.bunny.net/css?family=figtree:400,600&display=swap" rel="stylesheet" />

        <!-- Scripts e Estilos via Vite -->
        @vite(['resources/css/app.css', 'resources/js/app.js'])
    </head>
    <body class="font-sans antialiased dark:bg-black dark:text-white/50">

        {{-- Cabeçalho USP --}}
        <x-usp.header />

        {{-- Container Geral Flexível Verticalmente --}}
        <div class="relative min-h-screen flex flex-col bg-gray-100 dark:bg-gray-900">

            {{-- Container do Conteúdo Principal (Controla largura e cresce verticalmente) --}}
            {{-- Adicionado mx-auto para centralizar, max-w-7xl para largura, flex-grow para altura --}}
            <div class="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col flex-grow py-8 md:py-12"> {{-- Adicionado padding vertical aqui --}}

                {{-- Área principal (O card em si) --}}
                {{-- Removido <main>, o card agora é o elemento principal que cresce --}}
                <div class="p-6 lg:p-8 bg-white dark:bg-gray-800/50 dark:bg-gradient-to-bl from-gray-700/50 via-transparent dark:ring-1 dark:ring-inset dark:ring-white/5 rounded-lg shadow-2xl shadow-gray-500/20 dark:shadow-none flex flex-col flex-grow"> {{-- Adicionado flex-grow aqui --}}
                    <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
                        Bem-vindo(a) ao {{ config('app.name', 'Laravel') }} Starter Kit!
                    </h1>

                    <p class="mt-4 text-gray-500 dark:text-gray-400 leading-relaxed">
                        Esta é uma página de exemplo provisória para visualizar o cabeçalho padrão da USP integrado
                        acima. O restante do conteúdo pode ser personalizado conforme a necessidade da sua aplicação.
                    </p>

                    <p class="mt-4 text-gray-500 dark:text-gray-400 leading-relaxed">
                        A partir daqui, você pode:
                    </p>
                    <ul class="mt-2 list-disc list-inside text-gray-500 dark:text-gray-400">
                        {{-- Links para as rotas de autenticação --}}
                        @guest
                            <li><a href="{{ route('login.local') }}" class="underline hover:text-gray-900 dark:hover:text-white">Fazer login local</a></li>
                            <li><a href="{{ route('login') }}" class="underline hover:text-gray-900 dark:hover:text-white">Fazer login com Senha Única USP</a></li>
                            <li><a href="{{ route('register') }}" class="underline hover:text-gray-900 dark:hover:text-white">Registrar-se</a></li>
                        @endguest
                        @auth
                            <li><a href="{{ route('dashboard') }}" class="underline hover:text-gray-900 dark:hover:text-white">Acessar seu Dashboard</a></li>
                            <li>
                                <form method="POST" action="{{ route('logout') }}">
                                    @csrf
                                    <a href="{{ route('logout') }}"
                                       onclick="event.preventDefault(); this.closest('form').submit();"
                                       class="underline hover:text-gray-900 dark:hover:text-white">
                                        Fazer Logout
                                    </a>
                                </form>
                            </li>
                        @endauth
                    </ul>

                    {{-- Empurrar o texto para o final do card --}}
                    <div class="mt-auto">
                        <p class="pt-6 text-xs text-gray-400 dark:text-gray-500">
                            O cabeçalho acima foi gerado pelo componente <code><x-usp.header /></code>.
                            Verifique os caminhos das imagens e as cores no componente e no `tailwind.config.js` se necessário.
                        </p>
                    </div>
                </div> {{-- Fim do Card Principal --}}

            </div> {{-- Fim do Container do Conteúdo Principal --}}

            {{-- Rodapé padrão (agora fora do container que cresce) --}}
            <footer class="py-8 text-center text-sm text-black dark:text-white/70 bg-gray-100 dark:bg-gray-900">
                Laravel v{{ Illuminate\Foundation\Application::VERSION }} (PHP v{{ PHP_VERSION }})
            </footer>

        </div> {{-- Fim do Container Geral --}}
    </body>
</html>