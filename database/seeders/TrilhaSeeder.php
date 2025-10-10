<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

class TrilhaSeeder extends Seeder
{
    /**
     * Seed trilhas, trilha_regras, and trilha_disciplinas tables with data from legacy system.
     *
     * Course: 45052 (Computer Science - Bacharelado em Ciência da Computação)
     * Sources: TrilhaCienciaDados.java, TrilhaInteligenciaArtificial.java,
     *          TrilhaSistemasSoftware.java, TrilhaTeoriaComputacao.java
     */
    public function run(): void
    {
        $codcur = '45052'; // Computer Science course code

        // ===========================
        // Trilha: Ciência de Dados
        // ===========================
        $trilhaId = DB::table('trilhas')->insertGetId([
            'nome' => 'Ciência de Dados',
            'codcur' => $codcur,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        // Núcleo: 5 obrigatórias + 2 eletivas = 7 disciplinas total
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Núcleo',
            'num_disciplinas_exigidas' => 7,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $obrigatorias = ['MAC0317', 'MAC0426', 'MAC0431', 'MAC0460', 'MAE0221'];
        foreach ($obrigatorias as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'obrigatoria',
            ]);
        }

        $eletivas = ['MAC0315', 'MAC0325', 'MAC0427', 'MAE0312', 'MAE0228'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // ===========================
        // Trilha: Inteligência Artificial
        // ===========================
        $trilhaId = DB::table('trilhas')->insertGetId([
            'nome' => 'Inteligência Artificial',
            'codcur' => $codcur,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        // Regra 1: IA Intro (1 obrigatória + 2 eletivas = 3 disciplinas)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'IA Intro',
            'num_disciplinas_exigidas' => 3,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        DB::table('trilha_disciplinas')->insert([
            'regra_id' => $regraId,
            'coddis' => 'MAC0425',
            'tipo' => 'obrigatoria',
        ]);

        $eletivas = ['MAC0444', 'MAC0459', 'MAC0460'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // Regra 2: IA Sistemas (2 eletivas)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'IA Sistemas',
            'num_disciplinas_exigidas' => 2,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $eletivas = ['MAC0218', 'MAC0332', 'MAC0413', 'MAC0472'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // Regra 3: IA Teoria (1 eletiva)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'IA Teoria',
            'num_disciplinas_exigidas' => 1,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $eletivas = ['MAC0414', 'MAE0320', 'MAE0399', 'MAE0515', 'MAT0359'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // ===========================
        // Trilha: Sistemas de Software
        // ===========================
        $trilhaId = DB::table('trilhas')->insertGetId([
            'nome' => 'Sistemas de Software',
            'codcur' => $codcur,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        // Regra 1: Desenvolvimento de Software (4 obrigatórias)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Desenvolvimento de Software',
            'num_disciplinas_exigidas' => 4,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $obrigatorias = ['MAC0218', 'MAC0332', 'MAC0413', 'MAC0472'];
        foreach ($obrigatorias as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'obrigatoria',
            ]);
        }

        // Regra 2: Banco de Dados (2 eletivas)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Banco de Dados',
            'num_disciplinas_exigidas' => 2,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $eletivas = ['MAC0426', 'MAC0439', 'MAC0459'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // Regra 3: Sistemas Paralelos e Distribuídos (3 eletivas)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Sistemas Paralelos e Distribuídos',
            'num_disciplinas_exigidas' => 3,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $eletivas = ['MAC0219', 'MAC0344', 'MAC0352', 'MAC0463', 'MAC0469', 'MAC0471'];
        foreach ($eletivas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }

        // ===========================
        // Trilha: Teoria da Computação
        // ===========================
        $trilhaId = DB::table('trilhas')->insertGetId([
            'nome' => 'Teoria da Computação',
            'codcur' => $codcur,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        // Regra 1: Obrigatórias de Algoritmos (2 obrigatórias)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Obrigatórias de Algoritmos',
            'num_disciplinas_exigidas' => 2,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $obrigatorias = ['MAC0328', 'MAC0414'];
        foreach ($obrigatorias as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'obrigatoria',
            ]);
        }

        // Regra 2: Obrigatórias de Matemática (3 obrigatórias)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Obrigatórias de Matemática',
            'num_disciplinas_exigidas' => 3,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $obrigatorias = ['MAC0320', 'MAT0206', 'MAT0264'];
        foreach ($obrigatorias as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'obrigatoria',
            ]);
        }

        // Regra 3: Obrigatórias de Otimização (2 obrigatórias)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Obrigatórias de Otimização',
            'num_disciplinas_exigidas' => 2,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $obrigatorias = ['MAC0315', 'MAC0325'];
        foreach ($obrigatorias as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'obrigatoria',
            ]);
        }

        // Regra 4: Total de 7 Disciplinas (todas as da trilha como eletivas)
        $regraId = DB::table('trilha_regras')->insertGetId([
            'trilha_id' => $trilhaId,
            'nome_regra' => 'Total de 7 Disciplinas',
            'num_disciplinas_exigidas' => 7,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $todasDisciplinas = [
            'MAC0328', 'MAC0414', 'MAC0325', 'MAC0327', 'MAC0331', 'MAC0336', 'MAC0450', 'MAC0465',
            'MAC0466', 'MAC0320', 'MAT0206', 'MAT0264', 'MAC0414', 'MAC0436', 'MAE0221', 'MAE0224',
            'MAE0228', 'MAE0326', 'MAT0225', 'MAT0234', 'MAT0265', 'MAT0311', 'MAC0315', 'MAC0325',
            'MAC0300', 'MAC0343', 'MAC0418', 'MAC0419', 'MAC0427', 'MAC0450', 'MAC0452', 'MAC0461',
            'MAC0473',
        ];
        foreach ($todasDisciplinas as $coddis) {
            DB::table('trilha_disciplinas')->insert([
                'regra_id' => $regraId,
                'coddis' => $coddis,
                'tipo' => 'eletiva',
            ]);
        }
    }
}
