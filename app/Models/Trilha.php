<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Trilha extends Model
{
    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'nome',
        'codcrl',
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
