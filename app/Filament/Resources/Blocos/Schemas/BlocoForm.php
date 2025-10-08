<?php

namespace App\Filament\Resources\Blocos\Schemas;

use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class BlocoForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('nome')
                    ->label(__('Name'))
                    ->required()
                    ->maxLength(255)
                    ->helperText(__('Name of the block (e.g., "Introduction to Education Studies")')),

                TextInput::make('codcrl')
                    ->label(__('Curriculum Code'))
                    ->required()
                    ->maxLength(255)
                    ->helperText(__('Curriculum code this block applies to')),

                TextInput::make('creditos_aula_exigidos')
                    ->label(__('Required Lecture Credits'))
                    ->numeric()
                    ->required()
                    ->minValue(0)
                    ->default(0)
                    ->helperText(__('Number of lecture credits required for this block')),

                TextInput::make('creditos_trabalho_exigidos')
                    ->label(__('Required Work Credits'))
                    ->numeric()
                    ->required()
                    ->minValue(0)
                    ->default(0)
                    ->helperText(__('Number of work credits required for this block')),

                TextInput::make('num_disciplinas_exigidas')
                    ->label(__('Required Number of Courses'))
                    ->numeric()
                    ->required()
                    ->minValue(0)
                    ->default(0)
                    ->helperText(__('Minimum number of courses the student must complete from this block')),
            ]);
    }
}
