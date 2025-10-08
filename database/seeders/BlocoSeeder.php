<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

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
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Introdução aos Estudos da Educação',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 4,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 1,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = ['EDF0285', 'EDF0287', 'EDF0289', 'PSA5100', 'PSA5201', 'PSE5142', 'FLH0423'];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: Psicologia da Educação
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Psicologia da Educação',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 4,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 1,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = ['EDF0290', 'EDF0292', 'EDF0294', 'EDF0296', 'EDF0298'];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: Eletivas de Estágio da FE
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Eletivas de Estágio da FE',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 8,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 1,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = ['EDM0425', 'EDM0426', 'EDM0685'];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: Libras
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Libras',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 4,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 1,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = ['FLL1024', 'EDM0400'];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: Aprof. Licenciatura
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Aprof. Licenciatura',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 8,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 2,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = [
                'MAT0130', 'MAT0320', 'MAT0349', 'MAT0223', 'MAT0233', 'MAC0228', 'MAT0419', 'MAT0430',
                'MAC0228', 'MAC0122', 'MAP0335', 'MAC0212', 'MAE0221', 'MAE0311', 'MAE0217', 'MAE0228',
                '4300254', '4300255', '4300271', '4300357', '4300372', '4300373', '4300374', '4300259',
                '4300405', '4300266', '4300351', 'AGA0105', '4300356', '4300358', 'EDM0425', 'EDM0426',
            ];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: Aprof. Licenciatura (Prática)
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'Aprof. Licenciatura (Prática) ',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 8,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 2,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = ['MAT0412', 'MAT0450', 'MAE1514', 'MAC0118'];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }

            // Bloco: AACC (Atividades Acadêmico Científico Culturais)
            $blocoId = DB::table('blocos')->insertGetId([
                'nome' => 'AACC',
                'codcrl' => $codcrl,
                'creditos_aula_exigidos' => 0,
                'creditos_trabalho_exigidos' => 0,
                'num_disciplinas_exigidas' => 0,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            $disciplinas = [
                '4502401', '4502402', '4502403', '4502404', '4502405', '4502406', '4502407', '4502408',
                '4502409', '4502410', '4810001', '4810002', '4810003', '4810004', '4810005',
            ];
            foreach ($disciplinas as $coddis) {
                DB::table('bloco_disciplinas')->insert([
                    'bloco_id' => $blocoId,
                    'coddis' => $coddis,
                ]);
            }
        }
    }
}
