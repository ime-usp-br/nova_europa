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
        $this->createAuditLog($permission, 'updated', $permission->getOriginal(), $permission->getAttributes());
    }

    /**
     * Handle the Permission "deleted" event.
     */
    public function deleted(Permission $permission): void
    {
        $this->createAuditLog($permission, 'deleted', $permission->getOriginal(), []);
    }

    /**
     * Create an audit log entry.
     */
    protected function createAuditLog($model, string $event, array $old = [], array $new = []): void
    {
        // Remove timestamps if they're the only changes
        if ($event === 'updated' && count(array_diff_key($old, $new)) === 0) {
            $oldFiltered = array_diff_key($old, array_flip(['updated_at', 'created_at']));
            $newFiltered = array_diff_key($new, array_flip(['updated_at', 'created_at']));

            if ($oldFiltered == $newFiltered) {
                return;
            }
        }

        Audit::create([
            'user_type' => auth()->check() ? get_class(auth()->user()) : null,
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
