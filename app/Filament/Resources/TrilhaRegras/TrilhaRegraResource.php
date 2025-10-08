<?php

namespace App\Filament\Resources\TrilhaRegras;

use App\Filament\Resources\TrilhaRegras\Pages\EditTrilhaRegra;
use App\Filament\Resources\TrilhaRegras\RelationManagers\DisciplinasRelationManager;
use App\Filament\Resources\TrilhaRegras\Schemas\TrilhaRegraForm;
use App\Models\TrilhaRegra;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;

class TrilhaRegraResource extends Resource
{
    protected static ?string $model = TrilhaRegra::class;

    protected static bool $shouldRegisterNavigation = false;

    public static function form(Schema $schema): Schema
    {
        return TrilhaRegraForm::configure($schema);
    }

    public static function getRelations(): array
    {
        return [
            DisciplinasRelationManager::class,
        ];
    }

    public static function getPages(): array
    {
        return [
            'edit' => EditTrilhaRegra::route('/{record}/edit'),
        ];
    }

    public static function canViewAny(): bool
    {
        return auth()->check() && auth()->user()?->hasRole('Admin') === true;
    }

    public static function getIndexUrl(array $parameters = [], bool $isAbsolute = true, ?string $panel = null, ?\Illuminate\Database\Eloquent\Model $tenant = null, bool $shouldGuessMissingParameters = false): string
    {
        return \App\Filament\Resources\Trilhas\TrilhaResource::getUrl('index', $parameters, $isAbsolute, $panel, $tenant);
    }
}
