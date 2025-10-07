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
        /** @var array<string, mixed> $original */
        $original = $role->getOriginal();
        $this->createAuditLog($role, 'updated', $original, $role->getAttributes());
    }

    /**
     * Handle the Role "deleted" event.
     */
    public function deleted(Role $role): void
    {
        /** @var array<string, mixed> $original */
        $original = $role->getOriginal();
        $this->createAuditLog($role, 'deleted', $original, []);
    }

    /**
     * Create an audit log entry.
     *
     * @param  array<string, mixed>  $old
     * @param  array<string, mixed>  $new
     */
    protected function createAuditLog(Role $model, string $event, array $old = [], array $new = []): void
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
