<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use OwenIt\Auditing\Contracts\Auditable;

class BlocoDisciplina extends Model implements Auditable
{
    use \OwenIt\Auditing\Auditable;

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
     * @return BelongsTo<Bloco, $this>
     */
    public function bloco(): BelongsTo
    {
        return $this->belongsTo(Bloco::class);
    }
}
