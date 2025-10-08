<?php

namespace App\Filament\Resources\TrilhaRegras\Pages;

use App\Filament\Resources\TrilhaRegras\TrilhaRegraResource;
use App\Filament\Resources\Trilhas\TrilhaResource;
use App\Models\TrilhaRegra;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditTrilhaRegra extends EditRecord
{
    protected static string $resource = TrilhaRegraResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }

    protected function getRedirectUrl(): string
    {
        /** @var TrilhaRegra $record */
        $record = $this->getRecord();

        return TrilhaResource::getUrl('edit', ['record' => $record->trilha_id]);
    }
}
