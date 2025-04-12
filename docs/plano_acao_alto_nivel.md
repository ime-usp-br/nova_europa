**Plano de Ação de Alto Nível**

**Objetivo:** Evoluir o Starter Kit de seu estado inicial (com dependências e estrutura básica configuradas) para um produto funcional e polido, conforme definido no Termo de Abertura do Projeto (TAP) e no Guia de Desenvolvimento.

**I. Implementação/Finalização de Funcionalidades Core:**
*(Baseado principalmente no TAP e no CHANGELOG "Não Lançado")*

1.  **Autenticação Dupla (Senha Única + Local):**
    *   **UI (TALL Stack):** Implementar/adaptar as views do Laravel Breeze (TALL Stack - Livewire/Alpine.js/Tailwind) para:
        *   Tela de Login com opções claras para "Senha Única USP" e "Email/Senha Local".
        *   Tela de Registro Único com lógica condicional para solicitar Número USP (se `*usp.br` ou checkbox marcado).
        *   Fluxos de "Esqueci Minha Senha" e "Verificação de Email" para contas locais.
    *   **Controllers:**
        *   Implementar a lógica completa no `SocialiteController` (ou similar) para `redirectToProvider` e `handleProviderCallback`, incluindo a busca/criação de usuário local via `codpes`.
        *   Implementar a lógica no Controller de Registro local para:
            *   Validar Número USP e Email via `ReplicadoService`.
            *   Atribuir roles `usp_user` ou `external_user` automaticamente.
    *   **Middlewares/Guards:** Garantir que os guards `web` e `senhaunica` estejam configurados e aplicados corretamente nas rotas necessárias.
2.  **Integração Replicado:**
    *   Desenvolver os métodos comuns (consultas de dados pessoais, vínculos) dentro do `ReplicadoService` proposto no TAP.
    *   Implementar o uso deste serviço na validação do registro local USP.
3.  **Gerenciamento de Permissões (Spatie):**
    *   **UI (TALL Stack):** Criar a interface administrativa (protegida por Gate `admin`) para:
        *   Listar/Visualizar usuários.
        *   Atribuir/Revogar roles e permissões do guard `web`.
        *   Visualizar permissões do guard `senhaunica` (obtidas via Senha Única).
    *   **Seeders/Migrations:** Refinar/criar seeders para popular roles/permissões iniciais (se necessário, além das migrations já existentes).
4.  **Componentes Visuais e Tema USP:**
    *   Desenvolver/Adaptar os componentes Blade/Livewire reutilizáveis (ex: header, form inputs, tabela de usuários, *componente de busca de pessoas no Replicado*).
    *   Aplicar as diretrizes visuais básicas da USP usando Tailwind CSS.
5.  **Ferramentas Auxiliares:**
    *   Desenvolver o comando `artisan usp:check-integrations` para verificar a saúde das conexões com Senha Única e Replicado.
    *   Integrar e configurar um pacote de LogViewer (`opcodesio/log-viewer`).

**II. Testes Automatizados:**

1.  **Implementar Testes para Integrações USP:** Criar testes de Feature/Integration que utilizem os `FakeReplicadoService` e `FakeSenhaUnicaSocialiteProvider` para simular interações com os serviços USP sem depender deles online.
2.  **Expandir Cobertura:** Escrever testes Unitários e de Feature para as funcionalidades implementadas na Fase I (Controllers, Services, Models, Form Requests). Focar em casos de uso críticos (login, registro, validação, permissões).
3.  **Testes de UI:** Criar testes de UI com Laravel Dusk para validar os fluxos principais nas interfaces TALL Stack, se a complexidade justificar.
4.  **Cobertura Mínima:** Monitorar e garantir que a cobertura de testes atinja a meta (ex: 90%) definida nos critérios de sucesso do TAP.

**III. Integração Contínua (CI/CD) e Qualidade de Código:**

1.  **Refinar Workflow CI:** Atualizar `.github/workflows/laravel.yml` para incluir:
    *   Verificação de formatação de código: `vendor/bin/pint --test`.
    *   Análise estática: `vendor/bin/phpstan analyse`.
    *   Verificação de build de assets: `npm run build`.
2.  **Code Style:** Garantir que todo o código siga estritamente o PSR-12 via Pint e as convenções definidas em `docs/padroes_codigo_boas_praticas.md`.
3.  **Análise Estática:** Corrigir quaisquer problemas reportados pelo Larastan no nível configurado (`level: 5` atualmente, considerar aumentar progressivamente).

**IV. Documentação:**

1.  **Criar e Popular a Wiki do GitHub:**
    *   Estruturar a Wiki conforme sugestões do `guia_de_desenvolvimento.md`.
    *   Detalhar a arquitetura (Services, Actions, etc.).
    *   Explicar o fluxo de autenticação dupla e o sistema de permissões (ambos os guards).
    *   Documentar como usar os `Fake*` providers para testes.
    *   Incluir guias de configuração avançada e como estender o kit.
2.  **Manter Documentação Versionada:** Assegurar que `README.md` (a ser atualizado/recriado), `docs/` e `CHANGELOG.md` sejam mantidos atualizados conforme a estratégia de versionamento (`docs/versionamento_documentacao.md`) e o ciclo de desenvolvimento.
3.  **DocBlocks:** Adicionar/Completar DocBlocks no código conforme as boas práticas.

**V. Mitigação de Riscos e Melhorias:**

1.  **Dependências Externas USP:** Implementar o comando `artisan usp:check-integrations` (Fase I) e documentar como lidar com possíveis indisponibilidades (ex: fallback, mensagens de erro claras).
2.  **Complexidade Auth/Permissões:** Focar em clareza na UI, documentação detalhada na Wiki e testes robustos para os fluxos de autenticação e autorização.
3.  **Usabilidade:** Realizar testes de usabilidade (mesmo que informais) nas interfaces de login/registro e gerenciamento de usuários.
4.  **Validação Replicado:** Implementar tratamento de erro robusto caso o Replicado esteja indisponível durante o registro de usuário USP local.
5.  **Helpers USP:** Criar helpers específicos para tarefas comuns relacionadas a dados ou lógicas da USP, se identificadas necessidades recorrentes.
6.  **Deploy:** Documentar considerações gerais para deploy em ambientes USP (ex: necessidade de `TrustedProxy`, configuração de workers de fila).

**VI. Revisão Geral e Lançamento (v0.1.0):**

1.  **Revisão Completa:** Realizar uma revisão final do código, testes e documentação.
2.  **Atualizar CHANGELOG:** Detalhar todas as mudanças implementadas desde o início.
3.  **Atualizar Versão nos Documentos:** Atualizar os cabeçalhos `**Versão:**` e `**Data:**` em todos os arquivos `.md` versionados para a versão do release.
4.  **Tagging:** Criar a tag Git correspondente (ex: `v0.1.0`).
5.  **GitHub Release:** Criar um Release no GitHub associado à tag, utilizando o conteúdo do `CHANGELOG.md`.

Este plano fornece uma estrutura para guiar o desenvolvimento, garantindo que as funcionalidades planejadas sejam implementadas, a qualidade seja mantida e a documentação seja robusta, tudo alinhado com as melhores práticas do Laravel 12 e as necessidades específicas do ambiente USP.
