<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('trilha_regras', function (Blueprint $table) {
            $table->id();
            $table->foreignId('trilha_id')->constrained('trilhas')->cascadeOnDelete();
            $table->string('nome_regra');
            $table->unsignedSmallInteger('num_disciplinas_exigidas');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('trilha_regras');
    }
};
