{{-- resources/views/livewire/pages/evolucao.blade.php --}}
<?php

use App\Exceptions\ReplicadoServiceException;
use App\Livewire\Forms\EvolucaoForm;
use App\Services\EvolucaoService;
use App\Services\PdfGenerationService;
use App\Services\ReplicadoService;
use Illuminate\Support\Facades\Log;
use Livewire\Attributes\Layout;
use Livewire\Volt\Component;

new #[Layout('layouts.app')] class extends Component
{
    public EvolucaoForm $form;

    public ?array $aluno = null;

    /** @var array<int, array{codcrl: string, dtainicrl: string, dtafimcrl: string|null}> */
    public array $curriculos = [];

    public ?string $selectedCurriculo = null;

    /**
     * Busca os dados do aluno pelo NUSP.
     */
    public function buscarAluno(ReplicadoService $replicadoService): void
    {
        $this->validate([
            'form.nusp' => 'required|integer|min:1',
        ]);

        try {
            $this->aluno = $replicadoService->buscarAluno($this->form->nusp);
            $this->curriculos = $this->buscarCurriculosAluno($replicadoService, $this->aluno);
            $this->selectedCurriculo = null;
            $this->form->codcrl = '';

            session()->flash('status', __('Student found successfully.'));
        } catch (ReplicadoServiceException $e) {
            $this->aluno = null;
            $this->curriculos = [];
            $this->selectedCurriculo = null;

            $this->addError('form.nusp', $e->getMessage());

            Log::warning(__('Error searching for student'), [
                'nusp' => $this->form->nusp,
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Busca os currículos disponíveis do aluno.
     *
     * @param  array<string, mixed>|null  $aluno
     * @return array<int, array{codcrl: string, dtainicrl: string, dtafimcrl: string|null}>
     */
    protected function buscarCurriculosAluno(ReplicadoService $replicadoService, ?array $aluno): array
    {
        if ($aluno === null || ! isset($aluno['codpes'])) {
            return [];
        }

        try {
            // Busca currículos através do relacionamento correto:
            // PROGRAMAGR -> HABILPROGGR -> CURRICULOGR
            //
            // Lógica: Mostrar currículos de TODAS as habilitações (atuais e passadas)
            // do programa ATIVO do aluno, desde seu ingresso no programa.
            //
            // Por que todas as habilitações?
            // - O aluno pode ter mudado de habilitação durante o curso
            // - Pode ter planejado a vida acadêmica pelo currículo da habilitação original
            // - Disciplinas da habilitação antiga contam na nova
            //
            // Filtros aplicados:
            // - Apenas programa ATIVO do aluno (P.stapgm = 'A')
            // - Todas as habilitações deste programa (atuais e passadas)
            // - Currículos que estavam vigentes no ingresso OU criados depois
            // - EXCLUIR ciclo básico (codhab 0, 1, 4) pois será incluído automaticamente pelo sistema
            //
            // Lógica de datas:
            // Mostra currículos que fazem sentido para o período acadêmico do aluno.
            //
            // Condição: (início <= hoje) E (fim IS NULL OU fim >= ingresso)
            //
            // Isso significa:
            // - Currículo começou até hoje (não é futuro demais)
            // - E não encerrou antes do ingresso do aluno
            //
            // Exemplos (ingresso = 2020-01-31):
            // ✅ Currículo 2020-2020 (vigente no ingresso)
            // ✅ Currículo 2024-null (criado depois, habilitação nova)
            // ✅ Currículo 2025-2025 (futuro próximo)
            // ❌ Currículo 2015-2019 (encerrou antes do ingresso)
            // ❌ Currículo com codhab 0, 1 ou 4 (ciclo básico, será incluído automaticamente)
            $query = '
                SELECT DISTINCT
                    C.codcrl,
                    C.dtainicrl,
                    C.dtafimcrl
                FROM PROGRAMAGR P
                JOIN HABILPROGGR H ON P.codpes = H.codpes AND P.codpgm = H.codpgm
                JOIN CURRICULOGR C ON H.codcur = C.codcur AND H.codhab = C.codhab
                WHERE P.codpes = CONVERT(int, :codpes)
                    AND P.stapgm = :stapgmAtivo
                    AND C.codhab NOT IN (0, 1, 4)
                    AND C.dtainicrl <= GETDATE()
                    AND (C.dtafimcrl IS NULL OR C.dtafimcrl >= P.dtaini)
                ORDER BY C.dtainicrl DESC
            ';

            $params = [
                'codpes' => $aluno['codpes'],
                'stapgmAtivo' => 'A', // Programa Ativo
            ];

            /** @var array<int, array{codcrl: string, dtainicrl: string, dtafimcrl: string|null}> */
            $result = \Uspdev\Replicado\DB::fetchAll($query, $params);

            return $result;
        } catch (\Exception $e) {
            Log::warning(__('Error fetching student curricula'), [
                'codpes' => $aluno['codpes'] ?? null,
                'error' => $e->getMessage(),
            ]);

            return [];
        }
    }

    /**
     * Atualiza o currículo selecionado.
     */
    public function selecionarCurriculo(string $codcrl): void
    {
        $this->selectedCurriculo = $codcrl;
        $this->form->codcrl = $codcrl;
    }

    /**
     * Gera o relatório de evolução do aluno.
     */
    public function gerarEvolucao(EvolucaoService $evolucaoService, PdfGenerationService $pdfService): mixed
    {
        if ($this->aluno === null) {
            $this->addError('form.nusp', __('Please search for a student first.'));

            return null;
        }

        $this->validate([
            'form.codcrl' => 'required|string',
        ]);

        if (empty($this->form->codcrl)) {
            $this->addError('form.codcrl', __('Please select a curriculum.'));

            return null;
        }

        try {
            // Busca o usuário autenticado (operador que está gerando o relatório)
            /** @var \App\Models\User $operador */
            $operador = auth()->user();

            // Cria um objeto User temporário para o aluno (para compatibilidade com o serviço)
            $alunoModel = new \App\Models\User;
            $alunoModel->codpes = $this->aluno['codpes'];
            $alunoModel->name = $this->aluno['nompes'] ?? '';

            // Processa a evolução do aluno
            $evolucaoData = $evolucaoService->processarEvolucao($alunoModel, $this->form->codcrl);

            // Gera o PDF
            return $pdfService->gerarEvolucaoPdf($evolucaoData);

        } catch (\Exception $e) {
            Log::error(__('Error generating evolution report'), [
                'nusp' => $this->form->nusp,
                'codcrl' => $this->form->codcrl,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            session()->flash('error', __('Error generating evolution report: :message', ['message' => $e->getMessage()]));

            return null;
        }
    }

    /**
     * Gera o atestado de matrícula do aluno.
     */
    public function gerarAtestado(PdfGenerationService $pdfService): mixed
    {
        if ($this->aluno === null) {
            $this->addError('form.nusp', __('Please search for a student first.'));

            return null;
        }

        try {
            // TODO: Implementar geração de atestado de matrícula
            // Isso será implementado em uma issue futura
            session()->flash('status', __('Enrollment certificate generation will be implemented soon.'));

            return null;

        } catch (\Exception $e) {
            Log::error(__('Error generating enrollment certificate'), [
                'nusp' => $this->form->nusp,
                'error' => $e->getMessage(),
            ]);

            session()->flash('error', __('Error generating enrollment certificate: :message', ['message' => $e->getMessage()]));

            return null;
        }
    }
}; ?>

<div class="py-12">
    <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
        <div class="bg-white dark:bg-gray-800 overflow-hidden shadow-sm sm:rounded-lg">
            <div class="p-6 text-gray-900 dark:text-gray-100">
                <h2 class="text-2xl font-semibold mb-6">{{ __('Student Evolution Report') }}</h2>

                {{-- Session Status Messages --}}
                @if (session('status'))
                    <div class="mb-4 p-4 bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300 rounded">
                        {{ session('status') }}
                    </div>
                @endif

                @if (session('error'))
                    <div class="mb-4 p-4 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 rounded">
                        {{ session('error') }}
                    </div>
                @endif

                {{-- Formulário de Busca de Aluno --}}
                <form wire:submit.prevent="buscarAluno" class="mb-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <x-input-label for="nusp" :value="__('USP Number (NUSP)')" />
                            <x-text-input
                                wire:model="form.nusp"
                                id="nusp"
                                class="block mt-1 w-full"
                                type="text"
                                name="nusp"
                                required
                                autofocus
                                placeholder="{{ __('Enter student NUSP') }}"
                                aria-describedby="nusp-error"
                                pattern="[0-9]*"
                                inputmode="numeric"
                            />
                            <x-input-error :messages="$errors->get('form.nusp')" class="mt-2" id="nusp-error" />
                        </div>

                        <div class="flex items-end">
                            <x-primary-button type="submit" wire:loading.attr="disabled" wire:target="buscarAluno">
                                <span wire:loading.remove wire:target="buscarAluno">{{ __('Search Student') }}</span>
                                <span wire:loading wire:target="buscarAluno">{{ __('Searching...') }}</span>
                            </x-primary-button>
                        </div>
                    </div>
                </form>

                {{-- Dados do Aluno --}}
                @if ($aluno)
                    <div class="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <h3 class="text-lg font-semibold mb-3">{{ __('Student Information') }}</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <p class="text-sm text-gray-600 dark:text-gray-400">{{ __('Name') }}</p>
                                <p class="font-medium">{{ $aluno['nompes'] }}</p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-600 dark:text-gray-400">{{ __('NUSP') }}</p>
                                <p class="font-medium">{{ $aluno['codpes'] }}</p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-600 dark:text-gray-400">{{ __('Course') }}</p>
                                <p class="font-medium">{{ $aluno['nomcur'] }}</p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-600 dark:text-gray-400">{{ __('Qualification') }}</p>
                                <p class="font-medium">{{ $aluno['nomhab'] }}</p>
                            </div>
                        </div>
                    </div>

                    {{-- Seleção de Currículo --}}
                    @if (count($curriculos) > 0)
                        <div class="mb-6">
                            <h3 class="text-lg font-semibold mb-3">{{ __('Select Curriculum') }}</h3>
                            <div class="space-y-2">
                                @foreach ($curriculos as $curriculo)
                                    <label class="flex items-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition">
                                        <input
                                            type="radio"
                                            name="curriculo"
                                            value="{{ $curriculo['codcrl'] }}"
                                            wire:click="selecionarCurriculo('{{ $curriculo['codcrl'] }}')"
                                            class="mr-3 text-indigo-600 focus:ring-indigo-500"
                                            {{ $selectedCurriculo === $curriculo['codcrl'] ? 'checked' : '' }}
                                        >
                                        <div class="flex-1">
                                            <p class="font-medium">{{ $curriculo['codcrl'] }}</p>
                                            <p class="text-sm text-gray-600 dark:text-gray-400">
                                                {{ __('Start Date') }}: {{ \Carbon\Carbon::parse($curriculo['dtainicrl'])->format('d/m/Y') }}
                                                @if ($curriculo['dtafimcrl'])
                                                    | {{ __('End Date') }}: {{ \Carbon\Carbon::parse($curriculo['dtafimcrl'])->format('d/m/Y') }}
                                                @endif
                                            </p>
                                        </div>
                                    </label>
                                @endforeach
                            </div>
                            <x-input-error :messages="$errors->get('form.codcrl')" class="mt-2" />
                        </div>

                        {{-- Botões de Ação --}}
                        <div class="flex gap-4">
                            <x-primary-button
                                wire:click="gerarEvolucao"
                                :disabled="!$selectedCurriculo"
                                wire:loading.attr="disabled"
                                wire:target="gerarEvolucao"
                            >
                                <span wire:loading.remove wire:target="gerarEvolucao">{{ __('Generate Evolution Report') }}</span>
                                <span wire:loading wire:target="gerarEvolucao">{{ __('Generating...') }}</span>
                            </x-primary-button>

                            <x-secondary-button
                                wire:click="gerarAtestado"
                                :disabled="!$selectedCurriculo"
                                wire:loading.attr="disabled"
                                wire:target="gerarAtestado"
                            >
                                <span wire:loading.remove wire:target="gerarAtestado">{{ __('Generate Enrollment Certificate') }}</span>
                                <span wire:loading wire:target="gerarAtestado">{{ __('Generating...') }}</span>
                            </x-secondary-button>
                        </div>
                    @else
                        <div class="p-4 bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 dark:border-yellow-700 text-yellow-700 dark:text-yellow-300 rounded">
                            {{ __('No curricula found for this student.') }}
                        </div>
                    @endif
                @endif
            </div>
        </div>
    </div>
</div>
