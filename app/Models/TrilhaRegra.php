<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use OwenIt\Auditing\Contracts\Auditable;

class TrilhaRegra extends Model implements Auditable
{
    use \OwenIt\Auditing\Auditable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'trilha_id',
        'nome_regra',
        'num_disciplinas_exigidas',
    ];

    /**
     * Get the trilha that owns this regra.
     *
     * @return BelongsTo<Trilha, $this>
     */
    public function trilha(): BelongsTo
    {
        return $this->belongsTo(Trilha::class);
    }

    /**
     * Get the disciplinas associated with this regra.
     *
     * @return HasMany<TrilhaDisciplina, $this>
     */
    public function disciplinas(): HasMany
    {
        return $this->hasMany(TrilhaDisciplina::class, 'regra_id');
    }
}
