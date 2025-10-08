# Documento de Mapeamento de Funcionalidades - Sistema Europa

## 1. Objetivo

Este documento detalha as funcionalidades essenciais do sistema Europa, com foco especial na geração de documentos acadêmicos em PDF. O objetivo é definir o escopo e os requisitos para um projeto de migração, garantindo que as funcionalidades críticas sejam compreendidas e priorizadas.

## 2. Perfis de Usuário

A análise do código (`br/usp/ime/auth/Auth.java` e `br/usp/ime/model/Usuario.java`) revela a existência de dois perfis principais de acesso, além do acesso geral de usuário.

*   **Administrador (ADM):** Possui acesso total ao sistema, incluindo funcionalidades de gestão de usuários, papéis, grupos e outras configurações sistêmicas.
*   **Operador (OPR):** Possui acesso às funcionalidades operacionais do dia a dia, como a geração de documentos para os alunos. Não tem acesso às telas de administração do sistema.

## 3. Funcionalidades Principais (Foco em PDF)

Estas são as funcionalidades centrais do sistema do ponto de vista do usuário final.

### 3.1. Evolução do Aluno

*   **Descrição:** Esta é a funcionalidade mais complexa e central do sistema. Permite gerar um relatório completo (PDF) da situação acadêmica de um aluno, comparando seu histórico escolar com uma grade curricular específica. O sistema aplica regras de negócio para classificar as disciplinas (obrigatórias, eletivas, livres, etc.) e calcular os créditos.
*   **Perfis Autorizados:** `Administrador (ADM)`, `Operador (OPR)`.
*   **Fluxo de Uso:**
    1.  **Acesso à Página:** O usuário acessa o menu "Evolução Aluno" (`evolucao.xhtml`).
    2.  **Busca do Aluno:** O sistema exibe um campo para que o usuário insira o Número USP do aluno e clique em "Buscar Aluno". A lógica é tratada pelo `MbComparativo.buscarAluno()`.
    3.  **Seleção do Currículo:** Após a busca, o sistema exibe os dados do aluno e uma lista de currículos (`Curriculogr`) aos quais ele esteve ou está vinculado. O usuário deve selecionar um dos currículos da lista para servir de base para a análise.
    4.  **Geração do Documento:** O usuário clica no botão "Evolução".
        *   O sistema invoca o método `MbComparativo.evolucao()`.
        *   Este método, por sua vez, carrega a `GradeCurricular` e o `Historico` do aluno através dos EJBs (`EuropaBean`).
        *   A lógica de negócio em `Aluno.evolucao()` é executada para classificar as disciplinas.
        *   Finalmente, uma classe específica de geração de documento é chamada. O sistema possui lógicas customizadas por curso, como `DocumentoEvolucao45052.java` (BCC) e `DocumentoEvolucaoMAP.java` (MAP), que são selecionadas com base no código do curso do aluno. O documento PDF é gerado usando a biblioteca **iTextPDF**.

### 3.2. Atestado de Matrícula

*   **Descrição:** Gera um atestado de matrícula simples em formato PDF para um aluno, confirmando que ele está regularmente matriculado no semestre letivo.
*   **Perfis Autorizados:** `Administrador (ADM)`, `Operador (OPR)`.
*   **Fluxo de Uso:**
    1.  O fluxo é idêntico ao da "Evolução do Aluno" até o passo 3 (Seleção do Currículo).
    2.  **Geração do Documento:** O usuário clica no botão "Atestado de Matrícula".
        *   O sistema invoca o método `MbComparativo.gerarAtestadoMatricula()`.
        *   A lógica de negócio para calcular o semestre do aluno é executada.
        *   A classe `DocumentoAtestadoMatricula.java` é chamada para gerar o PDF, utilizando um template (`timbrado.pdf`) sobre o qual as informações são escritas.

## 4. Funcionalidades de Administração

Estas funcionalidades são acessíveis apenas pelo perfil de Administrador e dão suporte à operação do sistema.

### 4.1. Gestão de Usuários

*   **Descrição:** Interface (`usuario.xhtml`) para criar, visualizar, editar e remover usuários do sistema. Permite também associar e desassociar Papéis e Grupos a um usuário específico. Inclui a funcionalidade de gerar uma nova senha para um usuário.
*   **Perfis Autorizados:** `Administrador (ADM)`.

### 4.2. Gestão de Papéis

*   **Descrição:** Interface (`papel.xhtml`) para gerenciar os papéis (perfis de acesso) do sistema, como "ADM" e "OPR". É uma funcionalidade de CRUD (Criar, Ler, Atualizar, Deletar) simples.
*   **Perfis Autorizados:** `Administrador (ADM)`.

### 4.3. Gestão de Grupos

*   **Descrição:** Interface (`grupo.xhtml`) para gerenciar grupos de usuários. Estes grupos podem ser associados a Unidades Organizacionais (OUs).
*   **Perfis Autorizados:** `Administrador (ADM)`.

### 4.4. Gestão de Unidades Organizacionais (OUs)

*   **Descrição:** Interface (`ou.xhtml`) para CRUD de Unidades Organizacionais, que representam setores, departamentos ou comissões.
*   **Perfis Autorizados:** `Administrador (ADM)`.

### 4.5. Gestão de Blocos de Disciplinas

*   **Descrição:** Os "Blocos" são agrupamentos de disciplinas eletivas usados para verificar se um aluno cumpriu os requisitos específicos de certas grades curriculares (ex: Licenciatura em Matemática, 45024). A análise do código (`teste/wildfly/DefinirBloco*.java`) revela que **não há uma interface web para gerenciar esses blocos**. Eles são inseridos e atualizados no banco de dados através da execução de classes Java com métodos `main`, ou seja, são "hardcoded" e gerenciados diretamente pela equipe de desenvolvimento/administração do sistema.
*   **Perfis Autorizados:** N/A (tarefa de desenvolvedor/administrador de sistema).