<?php

namespace App\Observers;

use App\Models\Permission;
use OwenIt\Auditing\Models\Audit;

class PermissionObserver
{
    /**
     * Handle the Permission "created" event.
     */
    public function created(Permission $permission): void
    {
        $this->createAuditLog($permission, 'created', [], $permission->getAttributes());
    }

    /**
     * Handle the Permission "updated" event.
     */
    public function updated(Permission $permission): void
    {
        /** @var array<string, mixed> $original */
        $original = $permission->getOriginal();
        $this->createAuditLog($permission, 'updated', $original, $permission->getAttributes());
    }

    /**
     * Handle the Permission "deleted" event.
     */
    public function deleted(Permission $permission): void
    {
        /** @var array<string, mixed> $original */
        $original = $permission->getOriginal();
        $this->createAuditLog($permission, 'deleted', $original, []);
    }

    /**
     * Create an audit log entry.
     *
     * @param  array<string, mixed>  $old
     * @param  array<string, mixed>  $new
     */
    protected function createAuditLog(Permission $model, string $event, array $old = [], array $new = []): void
    {
        // Remove timestamps if they're the only changes
        if ($event === 'updated' && count(array_diff_key($old, $new)) === 0) {
            $oldFiltered = array_diff_key($old, array_flip(['updated_at', 'created_at']));
            $newFiltered = array_diff_key($new, array_flip(['updated_at', 'created_at']));

            if ($oldFiltered == $newFiltered) {
                return;
            }
        }

        $user = auth()->user();
        Audit::create([
            'user_type' => $user !== null ? get_class($user) : null,
            'user_id' => auth()->id(),
            'event' => $event,
            'auditable_type' => get_class($model),
            'auditable_id' => $model->id,
            'old_values' => $old,
            'new_values' => $new,
            'url' => request()->fullUrl(),
            'ip_address' => request()->ip(),
            'user_agent' => request()->userAgent(),
            'tags' => null,
        ]);
    }
}
