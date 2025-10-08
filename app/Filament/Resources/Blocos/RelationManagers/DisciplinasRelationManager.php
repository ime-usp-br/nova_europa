<?php

namespace App\Filament\Resources\Blocos\RelationManagers;

use Filament\Actions\CreateAction;
use Filament\Actions\DeleteAction;
use Filament\Actions\DeleteBulkAction;
use Filament\Forms\Components\TextInput;
use Filament\Resources\RelationManagers\RelationManager;
use Filament\Schemas\Schema;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class DisciplinasRelationManager extends RelationManager
{
    protected static string $relationship = 'disciplinas';

    protected static ?string $title = 'Disciplinas do Bloco';

    protected static ?string $modelLabel = 'disciplina';

    protected static ?string $pluralModelLabel = 'disciplinas';

    public function form(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('coddis')
                    ->label(__('Course Code'))
                    ->required()
                    ->maxLength(7)
                    ->helperText(__('USP course code (e.g., "EDF0285", "MAT0130")')),
            ]);
    }

    public function table(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('coddis')
                    ->label(__('Course Code'))
                    ->searchable()
                    ->sortable(),

                TextColumn::make('created_at')
                    ->label(__('Added At'))
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                //
            ])
            ->headerActions([
                CreateAction::make()
                    ->label(__('Add Course')),
            ])
            ->recordActions([
                DeleteAction::make(),
            ])
            ->toolbarActions([
                DeleteBulkAction::make(),
            ])
            ->defaultSort('coddis');
    }
}
