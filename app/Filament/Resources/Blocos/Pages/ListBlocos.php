<?php

namespace App\Filament\Resources\Blocos\Pages;

use App\Filament\Resources\Blocos\BlocoResource;
use Filament\Actions\Action;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;

class ListBlocos extends ListRecords
{
    protected static string $resource = BlocoResource::class;

    protected function getHeaderActions(): array
    {
        return [
            Action::make('backToDashboard')
                ->label(__('Back to Dashboard'))
                ->icon('heroicon-o-arrow-left')
                ->url(url('/admin'))
                ->color('gray'),
            CreateAction::make(),
        ];
    }
}
