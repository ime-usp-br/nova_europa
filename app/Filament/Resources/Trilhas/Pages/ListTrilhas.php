<?php

namespace App\Filament\Resources\Trilhas\Pages;

use App\Filament\Resources\Trilhas\TrilhaResource;
use Filament\Actions\Action;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;

class ListTrilhas extends ListRecords
{
    protected static string $resource = TrilhaResource::class;

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
