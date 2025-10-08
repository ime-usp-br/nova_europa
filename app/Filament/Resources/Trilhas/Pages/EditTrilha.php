<?php

namespace App\Filament\Resources\Trilhas\Pages;

use App\Filament\Resources\Trilhas\TrilhaResource;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditTrilha extends EditRecord
{
    protected static string $resource = TrilhaResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }
}
