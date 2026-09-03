<?php

namespace Database\Seeders;

use App\Models\Bloco;
use App\Models\BlocoDisciplina;
use Illuminate\Database\Seeder;

class BlocoSeeder extends Seeder
{
    /**
     * Seed blocos and bloco_disciplinas tables with data from legacy system (DefinirBloco2018.java).
     *
     * Course: 45024 (Math Education - Licenciatura em Matemática)
     * Curriculum codes: 450240001181, 450240004181
     */
    public function run(): void
    {
        $codcrls = ['450240001181', '450240004181'];

        foreach ($codcrls as $codcrl) {
            // Bloco: Introdução aos Estudos da Educação
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Introdução aos Estudos da Educação', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 4,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 1,
                ]
            );

            foreach (['EDF0285', 'EDF0287', 'EDF0289', 'PSA5100', 'PSA5201', 'PSE5142', 'FLH0423'] as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: Psicologia da Educação
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Psicologia da Educação', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 4,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 1,
                ]
            );

            foreach (['EDF0290', 'EDF0292', 'EDF0294', 'EDF0296', 'EDF0298'] as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: Eletivas de Estágio da FE
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Eletivas de Estágio da FE', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 8,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 1,
                ]
            );

            foreach (['EDM0425', 'EDM0426', 'EDM0685'] as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: Libras
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Libras', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 4,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 1,
                ]
            );

            foreach (['FLL1024', 'EDM0400'] as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: Aprof. Licenciatura
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Aprof. Licenciatura', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 8,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 2,
                ]
            );

            $disciplinas = [
                'MAT0130', 'MAT0320', 'MAT0349', 'MAT0223', 'MAT0233', 'MAC0228', 'MAT0419', 'MAT0430',
                'MAC0228', 'MAC0122', 'MAP0335', 'MAC0212', 'MAE0221', 'MAE0311', 'MAE0217', 'MAE0228',
                '4300254', '4300255', '4300271', '4300357', '4300372', '4300373', '4300374', '4300259',
                '4300405', '4300266', '4300351', 'AGA0105', '4300356', '4300358', 'EDM0425', 'EDM0426',
            ];
            foreach ($disciplinas as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: Aprof. Licenciatura (Prática)
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'Aprof. Licenciatura (Prática) ', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 8,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 2,
                ]
            );

            foreach (['MAT0412', 'MAT0450', 'MAE1514', 'MAC0118'] as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }

            // Bloco: AACC (Atividades Acadêmico Científico Culturais)
            $bloco = Bloco::firstOrCreate(
                ['nome' => 'AACC', 'codcrl' => $codcrl],
                [
                    'creditos_aula_exigidos' => 0,
                    'creditos_trabalho_exigidos' => 0,
                    'num_disciplinas_exigidas' => 0,
                ]
            );

            $disciplinas = [
                '4502401', '4502402', '4502403', '4502404', '4502405', '4502406', '4502407', '4502408',
                '4502409', '4502410', '4810001', '4810002', '4810003', '4810004', '4810005',
            ];
            foreach ($disciplinas as $coddis) {
                BlocoDisciplina::firstOrCreate(['bloco_id' => $bloco->id, 'coddis' => $coddis]);
            }
        }
    }
}