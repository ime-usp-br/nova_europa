<?php

namespace App\Observers;

use App\Models\Role;
use OwenIt\Auditing\Models\Audit;

class RoleObserver
{
    /**
     * Handle the Role "created" event.
     */
    public function created(Role $role): void
    {
        $this->createAuditLog($role, 'created', [], $role->getAttributes());
    }

    /**
     * Handle the Role "updated" event.
     */
    public function updated(Role $role): void
    {
        $this->createAuditLog($role, 'updated', $role->getOriginal(), $role->getAttributes());
    }

    /**
     * Handle the Role "deleted" event.
     */
    public function deleted(Role $role): void
    {
        $this->createAuditLog($role, 'deleted', $role->getOriginal(), []);
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
