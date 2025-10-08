<?php

namespace App\Filament\Resources\TrilhaRegras\RelationManagers;

use Filament\Actions\CreateAction;
use Filament\Actions\DeleteAction;
use Filament\Actions\DeleteBulkAction;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Resources\RelationManagers\RelationManager;
use Filament\Schemas\Schema;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class DisciplinasRelationManager extends RelationManager
{
    protected static string $relationship = 'disciplinas';

    protected static ?string $title = 'Disciplinas da Regra';

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
                    ->helperText(__('USP course code (e.g., "MAC0110", "MAE0212")')),

                Select::make('tipo')
                    ->label(__('Type'))
                    ->required()
                    ->options([
                        'obrigatoria' => __('Required'),
                        'eletiva' => __('Elective'),
                    ])
                    ->default('obrigatoria')
                    ->helperText(__('Course type within this rule')),
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

                TextColumn::make('tipo')
                    ->label(__('Type'))
                    ->badge()
                    ->color(fn (string $state): string => match ($state) {
                        'obrigatoria' => 'danger',
                        'eletiva' => 'success',
                        default => 'gray',
                    })
                    ->formatStateUsing(fn (string $state): string => match ($state) {
                        'obrigatoria' => __('Required'),
                        'eletiva' => __('Elective'),
                        default => $state,
                    })
                    ->sortable(),
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
