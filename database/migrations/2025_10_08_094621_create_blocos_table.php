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
        Schema::create('blocos', function (Blueprint $table) {
            $table->id();
            $table->string('nome');
            $table->string('codcrl')->index();
            $table->unsignedSmallInteger('creditos_aula_exigidos');
            $table->unsignedSmallInteger('creditos_trabalho_exigidos');
            $table->unsignedSmallInteger('num_disciplinas_exigidas');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('blocos');
    }
};
