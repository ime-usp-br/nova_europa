<x-app-layout>
    <x-slot name="header">
        <h2 class="font-semibold text-xl text-gray-800 dark:text-gray-200 leading-tight">
            {{ __('Nova Europa System') }}
        </h2>
    </x-slot>

    <div class="py-6">
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">

            {{-- Card de Apresentação do Sistema --}}
            <div class="bg-white dark:bg-gray-800 overflow-hidden shadow-sm sm:rounded-lg">
                <div class="p-8 lg:p-12 text-gray-900 dark:text-gray-100">

                    {{-- Título Principal --}}
                    <div class="text-center mb-8">
                        <h2 class="text-4xl font-bold text-gray-900 dark:text-white mb-3">
                            {{ __('Nova Europa System') }}
                        </h2>
                        <p class="text-lg text-gray-600 dark:text-gray-300">
                            {{ __('Academic Document Generation Platform') }}
                        </p>
                    </div>

                    {{-- Descrição do Sistema --}}
                    <div class="prose dark:prose-invert max-w-none mb-8">
                        <p class="text-gray-700 dark:text-gray-300 leading-relaxed text-center">
                            {{ __('The Nova Europa system is a comprehensive platform for generating academic documents for students at the Institute of Mathematics, Statistics and Computer Science (IME-USP). The system analyzes student academic history against curriculum requirements to produce detailed reports and certificates.') }}
                        </p>
                    </div>

                    {{-- Funcionalidades Principais --}}
                    <div class="grid md:grid-cols-2 gap-6 mb-8">
                        {{-- Evolução do Aluno --}}
                        <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 border border-gray-200 dark:border-gray-600">
                            <div class="flex items-start">
                                <div class="flex-shrink-0">
                                    <svg class="h-8 w-8 text-usp-blue-pri dark:text-usp-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                </div>
                                <div class="ml-4">
                                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                                        {{ __('Student Evolution Report') }}
                                    </h3>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">
                                        {{ __('Generates comprehensive academic reports comparing student course completion against curriculum requirements, including mandatory, elective, and free courses with credit calculations.') }}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {{-- Atestado de Matrícula --}}
                        <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 border border-gray-200 dark:border-gray-600">
                            <div class="flex items-start">
                                <div class="flex-shrink-0">
                                    <svg class="h-8 w-8 text-usp-blue-pri dark:text-usp-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                </div>
                                <div class="ml-4">
                                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                                        {{ __('Enrollment Certificate') }}
                                    </h3>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">
                                        {{ __('Issues official enrollment attestation documents confirming student registration status for the current academic semester.') }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {{-- Call to Action --}}
                    <div class="text-center mt-8">
                        <a href="{{ route('dashboard') }}" class="inline-flex items-center px-6 py-3 bg-usp-blue-pri hover:bg-usp-blue-sec text-white font-semibold rounded-lg shadow-md transition duration-150 ease-in-out">
                            {{ __('Access Dashboard') }}
                            <svg class="ml-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                            </svg>
                        </a>
                    </div>

                </div> {{-- Fim do Card Principal --}}
            </div>
        </div>
    </div>
</x-app-layout>