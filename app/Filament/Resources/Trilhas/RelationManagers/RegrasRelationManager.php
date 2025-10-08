<?php

namespace App\Filament\Resources\Trilhas\RelationManagers;

use Filament\Actions\CreateAction;
use Filament\Actions\DeleteAction;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Forms\Components\TextInput;
use Filament\Resources\RelationManagers\RelationManager;
use Filament\Schemas\Schema;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class RegrasRelationManager extends RelationManager
{
    protected static string $relationship = 'regras';

    protected static ?string $title = 'Regras da Trilha';

    protected static ?string $modelLabel = 'regra';

    protected static ?string $pluralModelLabel = 'regras';

    public function form(Schema $schema): Schema
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

    public function table(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('nome_regra')
                    ->label(__('Rule Name'))
                    ->searchable()
                    ->sortable()
                    ->wrap(),

                TextColumn::make('num_disciplinas_exigidas')
                    ->label(__('Required Courses'))
                    ->numeric()
                    ->sortable(),

                TextColumn::make('disciplinas_count')
                    ->counts('disciplinas')
                    ->label(__('Available Courses'))
                    ->badge()
                    ->color('success')
                    ->sortable(),

                TextColumn::make('created_at')
                    ->label(__('Created At'))
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                //
            ])
            ->headerActions([
                CreateAction::make()
                    ->label(__('Add Rule')),
            ])
            ->recordActions([
                EditAction::make()
                    ->url(fn ($record): string => route('filament.admin.resources.trilha-regras.edit', ['record' => $record])),
                DeleteAction::make(),
            ])
            ->toolbarActions([
                DeleteBulkAction::make(),
            ])
            ->defaultSort('nome_regra');
    }
}
