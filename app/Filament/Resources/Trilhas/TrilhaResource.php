<?php

namespace App\Filament\Resources\Trilhas;

use App\Filament\Resources\RelationManagers\AuditsRelationManager;
use App\Filament\Resources\Trilhas\Pages\CreateTrilha;
use App\Filament\Resources\Trilhas\Pages\EditTrilha;
use App\Filament\Resources\Trilhas\Pages\ListTrilhas;
use App\Filament\Resources\Trilhas\RelationManagers\RegrasRelationManager;
use App\Filament\Resources\Trilhas\Schemas\TrilhaForm;
use App\Filament\Resources\Trilhas\Tables\TrilhasTable;
use App\Models\Trilha;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;
use UnitEnum;

class TrilhaResource extends Resource
{
    protected static ?string $model = Trilha::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedMapPin;

    protected static UnitEnum|string|null $navigationGroup = 'Gerenciamento';

    protected static ?int $navigationSort = 4;

    protected static ?string $navigationLabel = 'Trilhas';

    protected static ?string $modelLabel = 'trilha';

    protected static ?string $pluralModelLabel = 'trilhas';

    public static function form(Schema $schema): Schema
    {
        return TrilhaForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return TrilhasTable::configure($table);
    }

    public static function getRelations(): array
    {
        return [
            RegrasRelationManager::class,
            AuditsRelationManager::class,
        ];
    }

    public static function getPages(): array
    {
        return [
            'index' => ListTrilhas::route('/'),
            'create' => CreateTrilha::route('/create'),
            'edit' => EditTrilha::route('/{record}/edit'),
        ];
    }

    public static function canViewAny(): bool
    {
        return auth()->check() && auth()->user()?->hasRole('Admin') === true;
    }
}
