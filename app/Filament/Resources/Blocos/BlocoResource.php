<?php

namespace App\Filament\Resources\Blocos;

use App\Filament\Resources\Blocos\Pages\CreateBloco;
use App\Filament\Resources\Blocos\Pages\EditBloco;
use App\Filament\Resources\Blocos\Pages\ListBlocos;
use App\Filament\Resources\Blocos\RelationManagers\DisciplinasRelationManager;
use App\Filament\Resources\Blocos\Schemas\BlocoForm;
use App\Filament\Resources\Blocos\Tables\BlocosTable;
use App\Filament\Resources\RelationManagers\AuditsRelationManager;
use App\Models\Bloco;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;
use UnitEnum;

class BlocoResource extends Resource
{
    protected static ?string $model = Bloco::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedAcademicCap;

    protected static UnitEnum|string|null $navigationGroup = 'Gerenciamento';

    protected static ?int $navigationSort = 3;

    protected static ?string $navigationLabel = 'Blocos';

    protected static ?string $modelLabel = 'bloco';

    protected static ?string $pluralModelLabel = 'blocos';

    public static function form(Schema $schema): Schema
    {
        return BlocoForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return BlocosTable::configure($table);
    }

    public static function getRelations(): array
    {
        return [
            DisciplinasRelationManager::class,
            AuditsRelationManager::class,
        ];
    }

    public static function getPages(): array
    {
        return [
            'index' => ListBlocos::route('/'),
            'create' => CreateBloco::route('/create'),
            'edit' => EditBloco::route('/{record}/edit'),
        ];
    }

    public static function canViewAny(): bool
    {
        return auth()->check() && auth()->user()?->hasRole('Admin') === true;
    }
}
