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
        Schema::create('trilha_disciplinas', function (Blueprint $table) {
            $table->id();
            $table->foreignId('regra_id')->constrained('trilha_regras')->cascadeOnDelete();
            $table->string('coddis');
            $table->enum('tipo', ['obrigatoria', 'eletiva']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('trilha_disciplinas');
    }
};
