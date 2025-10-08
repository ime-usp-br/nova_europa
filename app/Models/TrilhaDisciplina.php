<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TrilhaDisciplina extends Model
{
    /**
     * Indicates if the model should be timestamped.
     *
     * @var bool
     */
    public $timestamps = false;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'regra_id',
        'coddis',
        'tipo',
    ];

    /**
     * Get the regra that owns this disciplina.
     *
     * @return BelongsTo<TrilhaRegra, $this>
     */
    public function regra(): BelongsTo
    {
        return $this->belongsTo(TrilhaRegra::class);
    }
}
