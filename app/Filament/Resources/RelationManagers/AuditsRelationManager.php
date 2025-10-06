<?php

namespace App\Filament\Resources\RelationManagers;

use Filament\Resources\RelationManagers\RelationManager;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;
use OwenIt\Auditing\Models\Audit;

class AuditsRelationManager extends RelationManager
{
    protected static string $relationship = 'audits';

    protected static ?string $title = 'Histórico de Auditoria';

    protected static ?string $modelLabel = 'auditoria';

    protected static ?string $pluralModelLabel = 'auditorias';

    public function table(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('user.name')
                    ->label('Usuário')
                    ->default('Sistema')
                    ->searchable()
                    ->sortable(),

                TextColumn::make('event')
                    ->label('Evento')
                    ->badge()
                    ->color(fn (string $state): string => match ($state) {
                        'created' => 'success',
                        'updated' => 'info',
                        'deleted' => 'danger',
                        'restored' => 'warning',
                        default => 'gray',
                    })
                    ->formatStateUsing(fn (string $state): string => match ($state) {
                        'created' => 'Criado',
                        'updated' => 'Atualizado',
                        'deleted' => 'Excluído',
                        'restored' => 'Restaurado',
                        default => ucfirst($state),
                    }),

                TextColumn::make('old_values')
                    ->label('Alterações')
                    ->formatStateUsing(function (Audit $record): string {
                        $changes = [];

                        if ($record->old_values && $record->new_values) {
                            $old = $record->old_values;
                            $new = $record->new_values;

                            foreach ($new as $key => $value) {
                                if (isset($old[$key]) && $old[$key] != $value) {
                                    $changes[] = "{$key}: {$old[$key]} → {$value}";
                                } elseif (!isset($old[$key])) {
                                    $changes[] = "{$key}: {$value}";
                                }
                            }
                        } elseif ($record->new_values) {
                            foreach ($record->new_values as $key => $value) {
                                $changes[] = "{$key}: {$value}";
                            }
                        }

                        return $changes ? implode("\n", array_slice($changes, 0, 3)) : 'Nenhuma alteração';
                    })
                    ->wrap()
                    ->limit(100),

                TextColumn::make('created_at')
                    ->label('Data/Hora')
                    ->dateTime('d/m/Y H:i:s')
                    ->sortable(),
            ])
            ->defaultSort('created_at', 'desc')
            ->headerActions([
                // Sem ações de criar, pois é somente leitura
            ])
            ->paginated([10, 25, 50]);
    }

    public function isReadOnly(): bool
    {
        return true;
    }
}
