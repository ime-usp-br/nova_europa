<?php

namespace App\Filament\Resources\Blocos\Tables;

use Filament\Actions\BulkActionGroup;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class BlocosTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('nome')
                    ->label(__('Name'))
                    ->searchable()
                    ->sortable()
                    ->wrap(),

                TextColumn::make('codcrl')
                    ->label(__('Curriculum Code'))
                    ->searchable()
                    ->sortable(),

                TextColumn::make('disciplinas_count')
                    ->counts('disciplinas')
                    ->label(__('Courses'))
                    ->badge()
                    ->color('info')
                    ->sortable(),

                TextColumn::make('creditos_aula_exigidos')
                    ->label(__('Lecture Credits'))
                    ->numeric()
                    ->sortable()
                    ->toggleable(),

                TextColumn::make('creditos_trabalho_exigidos')
                    ->label(__('Work Credits'))
                    ->numeric()
                    ->sortable()
                    ->toggleable(),

                TextColumn::make('num_disciplinas_exigidas')
                    ->label(__('Required Courses'))
                    ->numeric()
                    ->sortable()
                    ->toggleable(),

                TextColumn::make('created_at')
                    ->label(__('Created At'))
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),

                TextColumn::make('updated_at')
                    ->label(__('Updated At'))
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                //
            ])
            ->recordActions([
                EditAction::make(),
            ])
            ->toolbarActions([
                BulkActionGroup::make([
                    DeleteBulkAction::make(),
                ]),
            ])
            ->defaultSort('nome');
    }
}
