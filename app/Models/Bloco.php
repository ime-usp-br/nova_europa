<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use OwenIt\Auditing\Contracts\Auditable;

class Bloco extends Model implements Auditable
{
    use \OwenIt\Auditing\Auditable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'nome',
        'codcrl',
        'creditos_aula_exigidos',
        'creditos_trabalho_exigidos',
        'num_disciplinas_exigidas',
    ];

    /**
     * Get the disciplines associated with this bloco.
     *
     * @return HasMany<BlocoDisciplina, $this>
     */
    public function disciplinas(): HasMany
    {
        return $this->hasMany(BlocoDisciplina::class);
    }
}
