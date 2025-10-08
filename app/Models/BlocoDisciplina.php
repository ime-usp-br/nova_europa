<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class BlocoDisciplina extends Model
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
        'bloco_id',
        'coddis',
    ];

    /**
     * Get the bloco that owns this disciplina.
     *
     * @return BelongsTo<Bloco, BlocoDisciplina>
     */
    public function bloco(): BelongsTo
    {
        return $this->belongsTo(Bloco::class);
    }
}
