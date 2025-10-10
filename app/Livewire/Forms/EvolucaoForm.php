<?php

namespace App\Livewire\Forms;

use Livewire\Attributes\Validate;
use Livewire\Form;

class EvolucaoForm extends Form
{
    #[Validate('nullable|integer|min:1')]
    public ?int $nusp = null;

    #[Validate('nullable|string')]
    public string $codcrl = '';

    /**
     * Get validated data for evolution processing.
     *
     * @return array{nusp: int|null, codcrl: string}
     */
    public function getData(): array
    {
        return [
            'nusp' => $this->nusp,
            'codcrl' => $this->codcrl,
        ];
    }

    /**
     * Reset form to initial state.
     */
    public function resetForm(): void
    {
        $this->nusp = null;
        $this->codcrl = '';
        $this->resetValidation();
    }
}
