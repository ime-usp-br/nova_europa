# Documentação de Regras de Negócio - Sistema Europa

## 1. Objetivo
O objetivo deste documento é formalizar a lógica de negócio do sistema Europa, extraída a partir da análise de seu código-fonte e do esquema de banco de dados. O foco principal é documentar as regras de cálculo da evolução do aluno em seu curso e a lógica para a geração condicional de diferentes relatórios PDF.

## 2. Regras de Negócio - Cálculo de Evolução do Aluno (`aluno.evolucao()`)

O método `aluno.evolucao()` é o responsável por processar o histórico acadêmico de um aluno (`HISTESCOLARGR`) contra a grade curricular (`GRADECURRICULAR`) à qual ele está vinculado. O processo classifica cada disciplina cursada em uma de quatro categorias.

### 2.1. Classificação de Disciplinas

A classificação de uma disciplina é determinada primeiramente pela sua presença na grade curricular do aluno.

1.  **Verificação Inicial:** O sistema verifica se a disciplina cursada pelo aluno (`HISTESCOLARGR.coddis`) existe na sua grade curricular (`GRADECURRICULAR`).
2.  **Classificação Direta:** Se a disciplina existe na grade, ela é classificada de acordo com o campo `tipobg` (Tipo de Obrigatoriedade) da tabela `GRADECURRICULAR`:

| Valor `tipobg` | Categoria no Sistema | Atribuída à Lista |
| :--- | :--- | :--- |
| `O` | Obrigatória | `disObg` |
| `C` | Optativa Complementar / Eletiva | `disOptCom` |
| `L` | Optativa Livre | `disOptLiv` |

3.  **Tratamento de Disciplinas Externas à Grade:** Se a disciplina cursada **não existe** na grade curricular, ela é inicialmente classificada como **Extra-curricular** (`disExtCur`). Em seguida, o sistema tenta promovê-la através das regras de equivalência.

### 2.2. Tratamento de Equivalências

Após a classificação inicial, o sistema reavalia as disciplinas categorizadas como "Extra-curriculares" para verificar se elas podem ser aproveitadas como equivalentes a disciplinas da grade curricular do aluno.

1.  **Busca por Grupos de Equivalência:** Para cada disciplina extra-curricular, o sistema consulta a tabela `GRUPOEQUIVGR` para verificar se ela pertence a um grupo de equivalência (`codeqv`) válido para o currículo do aluno (`codcrl`).
2.  **Verificação de Requisitos:** O sistema então consulta a tabela `EQUIVALENCIAGR` para identificar todas as disciplinas que compõem aquele grupo de equivalência (os pré-requisitos para a equivalência).
3.  **Validação e Promoção:** Se o aluno foi aprovado em **todas** as disciplinas que compõem o grupo de equivalência, o sistema considera a disciplina-alvo da grade curricular como "cumprida".
    *   A disciplina-alvo (que está na grade, mas não foi cursada diretamente) é adicionada à lista de classificação correspondente (Obrigatória, Eletiva, etc.).
    *   O resultado (`rstfim`) dessa disciplina é marcado internamente como `"EQUIVALENTE"`.
    *   As disciplinas extra-curriculares que foram usadas para compor a equivalência são removidas da lista de extra-curriculares (`disExtCur`) para não serem contabilizadas duas vezes.

### 2.3. Cálculo do "Semestre para Estágio"

O "semestre para estágio" é um cálculo específico para determinar em que semestre o aluno se encontra para fins de elegibilidade de estágio, podendo ser diferente do semestre ideal calculado de outras formas.

1.  **Cálculo do Semestre Base (`getSemestreCursando()`):** Primeiro, calcula-se um semestre de referência com base na proporção de créditos concluídos.
    *   **Créditos Concluídos:** Soma de todos os créditos-aula e créditos-trabalho de todas as categorias (Obrigatórias, Eletivas e Livres).
    *   **Créditos Exigidos:** Soma de todos os créditos-aula e créditos-trabalho exigidos pela grade curricular.
    *   **Fórmula:** `Semestre Base = ((Créditos Concluídos / Créditos Exigidos) * Duração Ideal do Curso) + 1`
    *   O resultado é arredondado para baixo e limitado à duração ideal do curso.

2.  **Ajuste para Estágio (`getSemestreCursandoEstagio()`):** O semestre base é então ajustado com base em regras adicionais se o aluno já estiver próximo do final do curso.
    *   **Condição de Ajuste:** A regra é aplicada se o progresso do aluno for igual ou superior a 87,5% (`Semestre Base / Duração Ideal >= 0.875`).
    *   **Regra de Redução:** O semestre calculado é **reduzido em 1** se as seguintes condições forem verdadeiras:
        *   Se o semestre letivo atual for o **primeiro semestre** (Janeiro a Junho) e o aluno **não estiver matriculado em alguma disciplina obrigatória de semestre ímpar** que ainda precisa cursar.
        *   Se o semestre letivo atual for o **segundo semestre** (Julho a Dezembro) e o aluno **não estiver matriculado em alguma disciplina obrigatória de semestre par** que ainda precisa cursar.
    *   **Regra Final:** Se o semestre calculado for igual à duração ideal do curso, ele será reduzido em 1 caso o aluno ainda tenha qualquer disciplina obrigatória a cursar (de semestre par ou ímpar).

## 3. Regras de Negócio - Geração de Documentos (PDF)

O sistema gera diferentes versões do PDF de evolução do aluno com base no código de seu curso.

### 3.1. Geração Condicional de PDF

A classe Java utilizada para gerar o PDF é determinada por uma estrutura condicional no método `MbComparativo.evolucao()`, baseada no código do curso (`codcur`) do aluno.

| Código do Curso (`codcur`) | Classe Java Responsável | Observações |
| :--- | :--- | :--- |
| `45052` | `DocumentoEvolucao45052.java` | Adiciona a seção de "Trilhas". |
| `45024` | `DocumentoEvolucao45024.java` | Adiciona a seção de "Blocos". |
| `45070` ou `45042` | `DocumentoEvolucaoMAP.java`| Adiciona uma seção de "Informações Complementares" para as eletivas do IB. |
| *Outros* | `DocumentoEvolucao.java` | Template padrão, sem seções adicionais. |

### 3.2. Regras Específicas por Curso/Currículo

#### 3.2.1. Blocos de Disciplinas (Licenciatura em Matemática - 45024)

Para os currículos do curso de Licenciatura em Matemática, o sistema valida o cumprimento de "Blocos" de disciplinas. A definição de cada bloco (nome, créditos exigidos, disciplinas) está persistida na base de dados local do sistema Europa (tabela `BLOCO` e `DISCIPLINA_BLOCO`) e associada a um código de currículo (`codcrl`).

O PDF de evolução para este curso exibe uma tabela adicional detalhando:
*   O nome de cada bloco.
*   As disciplinas que o aluno cursou e que pertencem àquele bloco.
*   O total de créditos-aula e créditos-trabalho obtidos pelo aluno no bloco.
*   O total de créditos-aula e créditos-trabalho exigidos pelo bloco.

#### 3.2.2. Trilhas de Conhecimento (Ciência da Computação - 45052)

Para o currículo do Bacharelado em Ciência da Computação, o sistema valida o cumprimento de "Trilhas" de conhecimento. As regras para cada trilha estão **hardcoded** nas classes Java correspondentes.

O PDF de evolução para este curso exibe uma seção adicional detalhando, para cada trilha:
*   As disciplinas que o aluno cursou e que pertencem àquela trilha.
*   Um status indicando se o núcleo da trilha e/ou a trilha completa foram cumpridos.

Abaixo estão as regras extraídas do código:

##### Trilha Ciência de Dados
*   **Disciplinas do Núcleo (Obrigatórias):** `MAC0317`, `MAC0426`, `MAC0431`, `MAC0460`, `MAE0221`
*   **Disciplinas Eletivas:** `MAC0315`, `MAC0325`, `MAC0427`, `MAE0312`, `MAE0228`
*   **Regra de Conclusão (Núcleo):** O aluno deve ser aprovado em **todas** as 5 disciplinas do núcleo **E** em pelo menos **2** disciplinas da lista de eletivas (totalizando 7 disciplinas).

##### Trilha Inteligência Artificial
*   **Módulo 1 - IA Intro:**
    *   **Obrigatória:** `MAC0425`
    *   **Eletivas:** `MAC0444`, `MAC0459`, `MAC0460`
    *   **Regra:** Cursar a obrigatória e mais 2 eletivas (total 3).
*   **Módulo 2 - IA Sistemas:**
    *   **Eletivas:** `MAC0218`, `MAC0332`, `MAC0413`, `MAC0472`
    *   **Regra:** Cursar 2 disciplinas desta lista.
*   **Módulo 3 - IA Teoria:**
    *   **Eletivas:** `MAC0414`, `MAE0320`, `MAE0399`, `MAE0515`, `MAT0359`
    *   **Regra:** Cursar 1 disciplina desta lista.
*   **Regra de Conclusão (Trilha):** O aluno deve cumprir as regras dos três módulos.

##### Trilha Sistemas de Software
*   **Módulo 1 - Desenvolvimento de Software:**
    *   **Obrigatórias:** `MAC0218`, `MAC0332`, `MAC0413`, `MAC0472`
    *   **Regra:** Cursar as 4 disciplinas.
*   **Módulo 2 - Banco de Dados:**
    *   **Eletivas:** `MAC0426`, `MAC0439`, `MAC0459`
    *   **Regra:** Cursar 2 disciplinas desta lista.
*   **Módulo 3 - Sistemas Paralelos e Distribuídos:**
    *   **Eletivas:** `MAC0219`, `MAC0344`, `MAC0352`, `MAC0463`, `MAC0469`, `MAC0471`
    *   **Regra:** Cursar 3 disciplinas desta lista.
*   **Regra de Conclusão (Trilha):** O aluno deve cumprir as regras dos três módulos.

##### Trilha Teoria da Computação
*   **Módulo 1 - Algoritmos:**
    *   **Obrigatórias:** `MAC0328`, `MAC0414`
*   **Módulo 2 - Matemática Discreta:**
    *   **Obrigatórias:** `MAC0320`, `MAT0206`, `MAT0264`
*   **Módulo 3 - Otimização:**
    *   **Obrigatórias:** `MAC0315`, `MAC0325`
*   **Regra de Conclusão (Trilha):** O aluno deve cursar um total de **7 disciplinas** da lista geral da trilha, **E** deve ter cumprido **todas as disciplinas obrigatórias de pelo menos 2 dos 3 módulos** acima.