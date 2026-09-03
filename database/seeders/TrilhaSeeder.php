<?php

namespace Database\Seeders;

use App\Models\Trilha;
use App\Models\TrilhaDisciplina;
use App\Models\TrilhaRegra;
use Illuminate\Database\Seeder;

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
        $trilha = Trilha::firstOrCreate(['nome' => 'Ciência de Dados', 'codcur' => $codcur]);

        // Núcleo: 5 obrigatórias + 2 eletivas = 7 disciplinas total
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Núcleo'],
            ['num_disciplinas_exigidas' => 7]
        );

        foreach (['MAC0317', 'MAC0426', 'MAC0431', 'MAC0460', 'MAE0221'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'obrigatoria']);
        }

        foreach (['MAC0315', 'MAC0325', 'MAC0427', 'MAE0312', 'MAE0228'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // ===========================
        // Trilha: Inteligência Artificial
        // ===========================
        $trilha = Trilha::firstOrCreate(['nome' => 'Inteligência Artificial', 'codcur' => $codcur]);

        // Regra 1: IA Intro (1 obrigatória + 2 eletivas = 3 disciplinas)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'IA Intro'],
            ['num_disciplinas_exigidas' => 3]
        );

        TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => 'MAC0425', 'tipo' => 'obrigatoria']);

        foreach (['MAC0444', 'MAC0459', 'MAC0460'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // Regra 2: IA Sistemas (2 eletivas)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'IA Sistemas'],
            ['num_disciplinas_exigidas' => 2]
        );

        foreach (['MAC0218', 'MAC0332', 'MAC0413', 'MAC0472'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // Regra 3: IA Teoria (1 eletiva)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'IA Teoria'],
            ['num_disciplinas_exigidas' => 1]
        );

        foreach (['MAC0414', 'MAE0320', 'MAE0399', 'MAE0515', 'MAT0359'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // ===========================
        // Trilha: Sistemas de Software
        // ===========================
        $trilha = Trilha::firstOrCreate(['nome' => 'Sistemas de Software', 'codcur' => $codcur]);

        // Regra 1: Desenvolvimento de Software (4 obrigatórias)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Desenvolvimento de Software'],
            ['num_disciplinas_exigidas' => 4]
        );

        foreach (['MAC0218', 'MAC0332', 'MAC0413', 'MAC0472'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'obrigatoria']);
        }

        // Regra 2: Banco de Dados (2 eletivas)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Banco de Dados'],
            ['num_disciplinas_exigidas' => 2]
        );

        foreach (['MAC0426', 'MAC0439', 'MAC0459'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // Regra 3: Sistemas Paralelos e Distribuídos (3 eletivas)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Sistemas Paralelos e Distribuídos'],
            ['num_disciplinas_exigidas' => 3]
        );

        foreach (['MAC0219', 'MAC0344', 'MAC0352', 'MAC0463', 'MAC0469', 'MAC0471'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }

        // ===========================
        // Trilha: Teoria da Computação
        // ===========================
        $trilha = Trilha::firstOrCreate(['nome' => 'Teoria da Computação', 'codcur' => $codcur]);

        // Regra 1: Obrigatórias de Algoritmos (2 obrigatórias)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Obrigatórias de Algoritmos'],
            ['num_disciplinas_exigidas' => 2]
        );

        foreach (['MAC0328', 'MAC0414'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'obrigatoria']);
        }

        // Regra 2: Obrigatórias de Matemática (3 obrigatórias)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Obrigatórias de Matemática'],
            ['num_disciplinas_exigidas' => 3]
        );

        foreach (['MAC0320', 'MAT0206', 'MAT0264'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'obrigatoria']);
        }

        // Regra 3: Obrigatórias de Otimização (2 obrigatórias)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Obrigatórias de Otimização'],
            ['num_disciplinas_exigidas' => 2]
        );

        foreach (['MAC0315', 'MAC0325'] as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'obrigatoria']);
        }

        // Regra 4: Total de 7 Disciplinas (todas as da trilha como eletivas)
        $regra = TrilhaRegra::firstOrCreate(
            ['trilha_id' => $trilha->id, 'nome_regra' => 'Total de 7 Disciplinas'],
            ['num_disciplinas_exigidas' => 7]
        );

        $todasDisciplinas = [
            'MAC0328', 'MAC0414', 'MAC0325', 'MAC0327', 'MAC0331', 'MAC0336', 'MAC0450', 'MAC0465',
            'MAC0466', 'MAC0320', 'MAT0206', 'MAT0264', 'MAC0414', 'MAC0436', 'MAE0221', 'MAE0224',
            'MAE0228', 'MAE0326', 'MAT0225', 'MAT0234', 'MAT0265', 'MAT0311', 'MAC0315', 'MAC0325',
            'MAC0300', 'MAC0343', 'MAC0418', 'MAC0419', 'MAC0427', 'MAC0450', 'MAC0452', 'MAC0461',
            'MAC0473',
        ];
        foreach ($todasDisciplinas as $coddis) {
            TrilhaDisciplina::firstOrCreate(['regra_id' => $regra->id, 'coddis' => $coddis, 'tipo' => 'eletiva']);
        }
    }
}