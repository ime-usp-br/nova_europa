<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use OwenIt\Auditing\Contracts\Auditable;

class Trilha extends Model implements Auditable
{
    use \OwenIt\Auditing\Auditable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'nome',
        'codcur',
    ];

    /**
     * Get the regras associated with this trilha.
     *
     * @return HasMany<TrilhaRegra, $this>
     */
    public function regras(): HasMany
    {
        return $this->hasMany(TrilhaRegra::class);
    }
}
