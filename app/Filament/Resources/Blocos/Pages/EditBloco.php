<?php

namespace App\Filament\Resources\Blocos\Pages;

use App\Filament\Resources\Blocos\BlocoResource;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditBloco extends EditRecord
{
    protected static string $resource = BlocoResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }
}
