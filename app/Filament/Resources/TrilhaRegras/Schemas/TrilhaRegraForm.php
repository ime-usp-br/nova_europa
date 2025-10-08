<?php

namespace App\Filament\Resources\TrilhaRegras\Schemas;

use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class TrilhaRegraForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('nome_regra')
                    ->label(__('Rule Name'))
                    ->required()
                    ->maxLength(255)
                    ->helperText(__('Name of the rule (e.g., "Core Courses", "Elective Courses")')),

                TextInput::make('num_disciplinas_exigidas')
                    ->label(__('Required Number of Courses'))
                    ->numeric()
                    ->required()
                    ->minValue(0)
                    ->default(0)
                    ->helperText(__('Minimum number of courses the student must complete from this rule')),
            ]);
    }
}
