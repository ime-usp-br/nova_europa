<?php

namespace App\Filament\Resources\Trilhas\Schemas;

use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class TrilhaForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('nome')
                    ->label(__('Name'))
                    ->required()
                    ->maxLength(255)
                    ->helperText(__('Name of the track (e.g., "Data Science", "Artificial Intelligence")')),

                TextInput::make('codcrl')
                    ->label(__('Curriculum Code'))
                    ->required()
                    ->maxLength(255)
                    ->helperText(__('Curriculum code this track applies to')),
            ]);
    }
}
