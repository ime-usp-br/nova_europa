<?php

namespace App\Filament\Widgets;

use App\Filament\Resources\AuditResource;
use App\Filament\Resources\Blocos\BlocoResource;
use App\Filament\Resources\Permissions\PermissionResource;
use App\Filament\Resources\Roles\RoleResource;
use App\Filament\Resources\Trilhas\TrilhaResource;
use App\Filament\Resources\Users\UserResource;
use Filament\Widgets\Widget;

class NavigationCardsWidget extends Widget
{
    protected string $view = 'filament.widgets.navigation-cards-widget';

    protected int|string|array $columnSpan = 'full';

    /**
     * @return array<int, array{title: string, description: string, icon: string, url: string, color: string, stats: int}>
     */
    public function getNavigationCards(): array
    {
        return [
            [
                'title' => 'Usuários',
                'description' => 'Gerenciar usuários do sistema',
                'icon' => 'heroicon-o-users',
                'url' => UserResource::getUrl('index'),
                'color' => 'primary',
                'stats' => \App\Models\User::count(),
            ],
            [
                'title' => 'Perfis',
                'description' => 'Gerenciar perfis e permissões',
                'icon' => 'heroicon-o-shield-check',
                'url' => RoleResource::getUrl('index'),
                'color' => 'success',
                'stats' => \Spatie\Permission\Models\Role::count(),
            ],
            [
                'title' => 'Blocos',
                'description' => 'Gerenciar blocos de disciplinas',
                'icon' => 'heroicon-o-cube',
                'url' => BlocoResource::getUrl('index'),
                'color' => 'info',
                'stats' => \App\Models\Bloco::count(),
            ],
            [
                'title' => 'Trilhas',
                'description' => 'Gerenciar trilhas de conhecimento',
                'icon' => 'heroicon-o-map-pin',
                'url' => TrilhaResource::getUrl('index'),
                'color' => 'success',
                'stats' => \App\Models\Trilha::count(),
            ],
            [
                'title' => 'Permissões',
                'description' => 'Gerenciar permissões do sistema',
                'icon' => 'heroicon-o-key',
                'url' => PermissionResource::getUrl('index'),
                'color' => 'warning',
                'stats' => \Spatie\Permission\Models\Permission::count(),
            ],
            [
                'title' => 'Logs de Auditoria',
                'description' => 'Visualizar histórico de alterações',
                'icon' => 'heroicon-o-document-text',
                'url' => AuditResource::getUrl('index'),
                'color' => 'info',
                'stats' => \OwenIt\Auditing\Models\Audit::count(),
            ],
        ];
    }
}
