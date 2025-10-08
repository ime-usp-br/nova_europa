# Arquitetura de Dados do Novo Sistema (TO-BE)

## 1. Objetivo

Este documento define a arquitetura de dados para o novo sistema Europa, construído sobre o **Laravel 12 USP Starter Kit**. O principal objetivo deste design é migrar a lógica de negócio, atualmente "hardcoded" em classes Java no sistema legado (ex: `teste/wildfly/DefinirBloco*.java`, `Trilha*.java`), para uma estrutura de banco de dados flexível e manutenível.

Esta abordagem permitirá que administradores do sistema gerenciem regras de negócio complexas, como os "Blocos" da Licenciatura em Matemática (45024) e as "Trilhas" do Bacharelado em Ciência da Computação (45052), sem a necessidade de modificar o código-fonte ou realizar um novo deploy da aplicação.

## 2. Visão Geral do Esquema

O esquema proposto introduz novas tabelas no banco de dados local da aplicação para modelar as regras de currículos específicos. As tabelas de usuários, papéis e permissões (`users`, `roles`, `permissions`, etc.) serão herdadas do Starter Kit e do pacote `spatie/laravel-permission`, não sendo detalhadas aqui.

O foco está nas entidades que representam as regras de negócio: `Blocos`, `Trilhas` e suas associações.

## 3. Novas Tabelas de Domínio

As seguintes tabelas serão criadas através de *migrations* do Laravel para armazenar a lógica de negócio.

### 3.1. Tabela `blocos`

Armazena as regras gerais para um "Bloco" de disciplinas, como os utilizados na Licenciatura em Matemática.

| Coluna | Tipo | Chave | Comentário |
| :--- | :--- | :--- | :--- |
| `id` | `bigIncrements` | PK | Identificador único do bloco. |
| `nome` | `string` | | Nome descritivo do bloco (ex: "Psicologia da Educação"). |
| `codcrl` | `string` | Index | Código do currículo ao qual este bloco se aplica. |
| `creditos_aula_exigidos` | `unsignedSmallInteger` | | Mínimo de créditos-aula a serem cumpridos no bloco. |
| `creditos_trabalho_exigidos`| `unsignedSmallInteger` | | Mínimo de créditos-trabalho a serem cumpridos no bloco. |
| `num_disciplinas_exigidas` | `unsignedSmallInteger` | | Mínimo de disciplinas a serem cursadas dentro do bloco. |
| `timestamps` | `timestamp` | | `created_at` e `updated_at`. |

### 3.2. Tabela `bloco_disciplinas`

Tabela de associação (pivô) que define quais disciplinas pertencem a um determinado `bloco`.

| Coluna | Tipo | Chave | Comentário |
| :--- | :--- | :--- | :--- |
| `id` | `bigIncrements` | PK | Identificador único da associação. |
| `bloco_id` | `foreignId` | FK (`blocos`) | Referência ao bloco. |
| `coddis` | `string` | | Código da disciplina (ex: "EDF0290"). |

### 3.3. Tabela `trilhas`

Define uma "Trilha" de conhecimento, como as existentes no Bacharelado em Ciência da Computação.

| Coluna | Tipo | Chave | Comentário |
| :--- | :--- | :--- | :--- |
| `id` | `bigIncrements` | PK | Identificador único da trilha. |
| `nome` | `string` | | Nome da trilha (ex: "Ciência de Dados"). |
| `codcrl` | `string` | Index | Código do currículo ao qual esta trilha se aplica. |
| `timestamps`| `timestamp` | | `created_at` e `updated_at`. |

### 3.4. Tabela `trilha_regras`

Armazena as regras de cumprimento para cada `trilha` (ex: "cursar 2 disciplinas do Módulo IA Sistemas").

| Coluna | Tipo | Chave | Comentário |
| :--- | :--- | :--- | :--- |
| `id` | `bigIncrements` | PK | Identificador único da regra. |
| `trilha_id`| `foreignId` | FK (`trilhas`) | Referência à trilha. |
| `nome_regra`| `string` | | Nome descritivo da regra (ex: "Núcleo da Trilha"). |
| `num_disciplinas_exigidas` | `unsignedSmallInteger` | | Mínimo de disciplinas a serem cursadas para cumprir esta regra. |
| `timestamps`| `timestamp` | | `created_at` e `updated_at`. |

### 3.5. Tabela `trilha_disciplinas`

Tabela de associação que define quais disciplinas pertencem a uma `trilha_regra` e qual o seu tipo (obrigatória ou eletiva dentro daquela regra).

| Coluna | Tipo | Chave | Comentário |
| :--- | :--- | :--- | :--- |
| `id` | `bigIncrements` | PK | Identificador único da associação. |
| `regra_id` | `foreignId` | FK (`trilha_regras`) | Referência à regra da trilha. |
| `coddis` | `string` | | Código da disciplina. |
| `tipo` | `enum('obrigatoria', 'eletiva')` | | Tipo da disciplina dentro do contexto da regra. |

## 4. Estratégia de Migração de Dados

Para popular as tabelas recém-criadas com os dados existentes no sistema legado, será adotada a seguinte estratégia:

1.  **Criação de Seeders:** Serão desenvolvidos *Seeders* do Laravel para cada uma das novas estruturas de dados (`BlocosSeeder`, `TrilhasSeeder`, etc.).
2.  **Extração da Lógica:** Os dados para popular os seeders serão extraídos diretamente do código-fonte do sistema Java legado, especificamente das classes que atualmente contêm essa lógica de forma "hardcoded" (ex: `DefinirBloco2018.java`, `TrilhaCienciaDados.java`, `TrilhaInteligenciaArtificial.java`, etc.).
3.  **Execução:** Os seeders serão executados durante o processo de deploy inicial da aplicação (`php artisan db:seed`) para garantir que o sistema inicie com todas as regras de negócio corretamente configuradas.

## 5. Conclusão

A arquitetura de dados proposta move a lógica de negócio de um formato estático e de difícil manutenção (código-fonte Java) para uma estrutura de banco de dados relacional e dinâmica. Esta abordagem trará os seguintes benefícios:

*   **Manutenibilidade:** As regras de negócio poderão ser atualizadas diretamente no banco de dados, sem a necessidade de intervenção no código ou de um novo deploy.
*   **Flexibilidade:** A criação de novas trilhas ou blocos para futuros currículos será simplificada, bastando inserir novos registros nas tabelas.
*   **Clareza:** A lógica de negócio se torna mais explícita e fácil de consultar, em vez de estar distribuída em múltiplas classes Java.