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
        Schema::create('bloco_disciplinas', function (Blueprint $table) {
            $table->id();
            $table->foreignId('bloco_id')->constrained('blocos')->cascadeOnDelete();
            $table->string('coddis');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('bloco_disciplinas');
    }
};
