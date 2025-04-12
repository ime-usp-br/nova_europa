**Termo de Abertura do Projeto: Laravel 12 USP Starter Kit**

**Versão:** 0.1.0<br>
**Data:** 2025-04-12

**1. Título do Projeto:**
Laravel 12 USP Starter Kit

**2. Introdução/Visão Geral:**
Este projeto visa criar um "Starter Kit" baseado no Laravel 12, especificamente adaptado para as necessidades de desenvolvimento de aplicações web dentro da Universidade de São Paulo (USP). O kit fornecerá uma base de código padronizada e pré-configurada, integrando soluções comuns do ecossistema USP, como autenticação via Senha Única e um sistema de login/registro local flexível, além de acesso facilitado aos dados do Replicado. O propósito principal é acelerar o início de novos projetos, promover boas práticas e garantir consistência entre os sistemas desenvolvidos na universidade.

**3. Justificativa e Objetivos:**
A criação deste Starter Kit justifica-se pela necessidade de padronizar e agilizar o desenvolvimento de aplicações Laravel na USP. Frequentemente, equipes e desenvolvedores recriam configurações básicas para autenticação USP (Senha Única e local), gerenciamento de permissões e integração com sistemas corporativos. Este kit visa eliminar essa redundância.

**Objetivos:**

*   **Reduzir o tempo de configuração inicial:** Fornecer uma base funcional com Laravel 12, autenticação dupla (Senha Única USP e Local) e gerenciamento de permissões básicas pré-configurados.
*   **Promover Padronização:** Estabelecer uma estrutura de projeto comum, facilitando a manutenção e a colaboração entre diferentes equipes/projetos na USP.
*   **Facilitar a Integração USP:** Incluir e configurar as bibliotecas `uspdev/senhaunica-socialite` e `uspdev/replicado`, oferecendo um `ReplicadoService` robusto para consultas comuns e validação de usuários USP no registro local.
*   **Fornecer uma Base Visual:** Oferecer um tema visual básico (via TALL Stack/Livewire) e componentes Blade reutilizáveis, alinhados com a identidade visual da USP, adaptando os componentes do Breeze.
*   **Incentivar Boas Práticas:** Incorporar testes automatizados básicos (PHPUnit/Pest), análise de estilo de código (Pint/Larastan), configuração `.editorconfig` e uma metodologia de desenvolvimento ágil/Kanban documentada.
*   **Melhorar a Experiência do Desenvolvedor:** Oferecer uma base de código limpa, extensível, manutenível e com documentação clara (README e Wiki), incluindo facilitadores de teste para dependências USP.

**4. Escopo do Projeto:**

**4.1. Inclusões:**

*   **Base Tecnológica:** Laravel 12, PHP >= 8.2, Vite, Tailwind CSS.
*   **Autenticação:**
    *   Integração completa e funcional com `uspdev/senhaunica-socialite` (OAuth1) para usuários USP.
    *   Sistema de login/registro local baseado em email/senha, utilizando Laravel Breeze como base.
    *   Formulário de registro único com campo condicional para Número USP (codpes).
    *   Identificação de usuários USP no registro local via email (`*usp.br`) e checkbox "Sou da USP".
    *   Obrigatoriedade do Número USP (codpes) para registro local de usuários USP.
    *   Validação do Número USP e do email correspondente contra o Replicado (`uspdev/replicado`) durante o registro local USP.
    *   Interface de login com botões distintos para "Entrar com Senha Única USP" e "Entrar com Email/Senha".
    *   Fluxo padrão do Laravel Breeze para "Esqueci Minha Senha" para contas locais.
    *   Verificação de email obrigatória (via Laravel/Breeze) para todos os registros locais.
    *   Clareza na interface sobre as opções de login/registro.
    *   Aplicação das regras de senha padrão do Laravel (`Password::defaults()`, min 8 chars) para contas locais.
*   **Gerenciamento de Permissões:**
    *   Integração com `spatie/laravel-permission` (guard `web`).
    *   Roles básicos pré-definidos: `Admin`, `User`.
    *   Roles atribuídos automaticamente no registro local: `usp_user` (para USP validados), `external_user` (para externos).
    *   Permissões hierárquicas (`admin`, `boss`, `manager`, `poweruser`, `user`) e de vínculo (`Servidor`, `Docente`, `Alunogr`, etc., com sufixo `usp` para externos) gerenciadas via `senhaunica-socialite` no guard `senhaunica`.
    *   Interface básica (customizada TALL) para gerenciamento de usuários, Roles e Permissões da aplicação (guard `web`). Atribuição manual de permissões além dos roles.
*   **Integração Replicado:**
    *   Inclusão e configuração da biblioteca `uspdev/replicado`.
    *   Fornecimento de um `ReplicadoService` robusto com métodos pré-implementados para consultas frequentes (dados pessoais, vínculos ativos).
*   **Frontend Stack:** Baseado no preset Laravel Breeze com Livewire (TALL Stack), utilizando Alpine.js. Adaptação visual dos componentes Breeze.
*   **Interface de Usuário (UI):**
    *   Tema visual básico seguindo diretrizes USP.
    *   Componentes Blade reutilizáveis (incluindo um para busca de pessoas no Replicado - admin only).
    *   UI básica customizada (TALL) para gerenciamento de usuários/permissões.
    *   Página de perfil básica com áreas designadas para customização.
*   **Testes Automatizados:**
    *   Testes unitários e de feature básicos (PHPUnit/Dusk) para a estrutura inicial.
    *   Facilitadores para testes de integrações USP (`FakeReplicadoService`, `FakeSenhaUnicaSocialiteProvider`).
    *   Factories básicas para `User` e simulação de vínculos Replicado.
*   **Documentação:**
    *   `README.md` detalhado (visão geral, instalação, uso básico).
    *   Wiki no GitHub (guias, estrutura, padrões, testes, requisitos, metodologia).
    *   Uso de arquivos de tradução (`pt_BR` como padrão) para strings do kit.
*   **Ferramentas Auxiliares:**
    *   Comando `artisan` para verificar saúde das integrações USP.
    *   Configuração de filas com driver `database` por padrão e migrations incluídas.
    *   Configuração `supervisor.conf` de exemplo para worker.
    *   Larastan pré-configurado para análise estática.
    *   Laravel Pint e `.editorconfig` para estilo de código.
*   **Logging:** Configuração padrão do Laravel e LogViewer básico integrado.

**4.2. Exclusões:**

*   Funcionalidades de negócio específicas.
*   Integrações avançadas com outras APIs/sistemas USP.
*   Suporte otimizado para bancos de dados específicos (além de SQLite para testes e recomendação geral).
*   Funcionalidades primárias de API (Tokens, autenticação API).
*   Módulos opcionais instaláveis.
*   Foco aprofundado em acessibilidade web (WCAG).
*   Garantia de atualização fácil entre *major versions* do Laravel/pacotes.
*   Scripts de deploy específicos para ambientes USP.
*   Ferramentas de anonimização de banco de dados.
*   Configuração avançada de Headers de Segurança HTTP.
*   Geração automática de documentação API.
*   Configuração explícita para proxies reversos (documentar necessidade de `TrustedProxy`).
*   Habilitação de permissões `spatie` baseadas em wildcard por padrão.
*   Detecção automática de indisponibilidade da Senha Única.
*   Cache pré-configurado para dados do Replicado (apenas documentar estratégias).
*   Helper functions específicas da USP.
*   Pré-preenchimento de dados do Replicado no registro local.

**5. Principais Entregáveis:**

*   Repositório Git com código-fonte funcional do Laravel 12 USP Starter Kit.
*   Conjunto inicial de testes automatizados (PHPUnit/Dusk).
*   Documentação (README.md, Wiki GitHub).
*   Template básico CI/CD para GitHub Actions.

**6. Critérios de Sucesso:**

*   Redução no tempo de setup para novos projetos Laravel na USP.
*   Feedback positivo de desenvolvedores USP (facilidade, clareza, utilidade).
*   Cobertura de testes mínima de 90% para o código do kit.
*   Ausência de vulnerabilidades de segurança conhecidas nas configurações padrão.
*   Código seguindo convenções e com baixa complexidade.

**7. Stakeholders:**

*   **Usuários Principais:** Desenvolvedores júnior/estagiários USP, Desenvolvedores experientes USP, Equipes de sistemas departamentais/centrais.
*   **Mantenedor Principal:** SVAPIN-IME-USP.
*   **Potenciais Interessados:** Outros departamentos de TI USP, Comunidade de desenvolvedores USP.

**8. Requisitos de Alto Nível:**

*   **8.1. Funcionalidade:**
    *   Prover Laravel 12 funcional.
    *   Autenticação dupla: Senha Única USP (`uspdev/senhaunica-socialite`) e Local (Breeze adaptado: email/senha, registro, reset de senha, verificação de email).
    *   Registro local único, diferenciando USP (com validação NUSP+email via Replicado) e Externos.
    *   Gerenciamento básico de permissões (`spatie/laravel-permission`) com roles padrão (`Admin`, `User`, `usp_user`, `external_user`) e interface TALL.
    *   Permissões de vínculo USP (guard `senhaunica`) e hierárquicas (`admin` a `user`) aplicadas via `senhaunica-socialite`.
    *   Configuração para acesso ao Replicado (`uspdev/replicado`) com `ReplicadoService`.
    *   Interface web básica para gerenciamento de usuários e suas permissões (`web` e `senhaunica`).
    *   Comando `artisan` para verificar saúde das integrações USP.
*   **8.2. Interfaces:**
    *   **Interface Web (UI):** Tema visual básico TALL Stack (Livewire/Alpine.js), adaptado do Breeze, seguindo diretrizes USP. Interface de gerenciamento. Página de perfil básica. Telas de login/registro/reset/verificação locais e aviso de verificação Senha Única. Botões distintos para login Senha Única e Local.
    *   **Interface de Linha de Comando (CLI):** Comandos `artisan` padrão e customizados.
*   **8.3. Atributos de Qualidade:**
    *   **Facilidade de Uso:** Simples de instalar, configurar e usar para devs com conhecimento básico de Laravel.
    *   **Extensibilidade:** Arquitetura (Services/Repositories) facilitando adição de módulos.
    *   **Manutenibilidade:** Código limpo (PSR-12, Pint), documentado (código e Wiki), com testes.
    *   **Segurança:** Configurações padrão (CSRF, XSS), validação de entrada, permissões `spatie`, regras de senha (`Password::defaults()`).
    *   **Performance:** Otimizações básicas (caching config/route), sem sobrecarga.
    *   **Conformidade:** Seguir padrões Laravel e diretrizes USP.
*   **8.4. Restrições:**
    *   Laravel 12, PHP >= 8.2.
    *   Dependência das bibliotecas USP.
    *   Stack frontend TALL Stack.
    *   Foco em aplicações web.

**9. Metodologia e Padrões:**

*   **Gerenciamento de Projeto:** Ágil/Kanban.
*   **Gerenciamento de Tarefas:** GitHub Issues (atômicas, bem definidas, com templates). GitHub CLI (`gh`) para automação.
*   **Visualização do Fluxo:** GitHub Projects (Kanban: Backlog, A Fazer, Em Progresso, Concluído).
*   **Versionamento:** Git com GitHub. Commits atômicos, frequentes, vinculados a Issues (`#<id>`), padrão Conventional Commits. Branches por feature/issue. PRs para revisão.
*   **Qualidade de Código:** Laravel Pint (automático/CI), Larastan (análise estática).
*   **Testes:** PHPUnit/Pest (Unit/Feature), fakes/mocks para dependências USP.
*   **Documentação:** README, Wiki GitHub, inspirada em boas práticas (IEEE 830). Arquivos de tradução `pt_BR`.

**10. Premissas:**

*   Bibliotecas USP (`senhaunica-socialite`, `replicado`) disponíveis e funcionais.
*   Serviço Senha Única USP operacional.
*   Acesso ao Replicado disponível.
*   Desenvolvedores com conhecimento básico de Laravel, Git, CLI.

**11. Restrições:**

*   Escopo limitado ao definido na Seção 4.
*   Orçamento/tempo limitados à versão inicial.
*   Funcionalidade depende da estabilidade dos serviços USP.
*   Stack TALL definida.
*   Tratamento de indisponibilidade da Senha Única é manual pelo usuário.

**12. Riscos Iniciais:**

*   **Dependências Externas:** Mudanças/Indisponibilidade nas APIs/libs USP.
*   **Adoção:** Baixa aceitação pela comunidade USP.
*   **Manutenção:** Dificuldade em manter atualizado.
*   **Complexidade:** Kit se tornar complexo para iniciantes.
*   **Escopo:** "Scope creep".
*   **Fluxo Duplo Auth:** Complexidade adicional na gestão/experiência do usuário com dois métodos de login.
*   **Validação Replicado:** Indisponibilidade do Replicado pode bloquear registros locais USP.

**13. Equipe do Projeto e Responsabilidades:**

*   **Responsável Principal:** SVAPIN-IME-USP.
*   **Contribuições:** Abertas à comunidade USP via PRs após lançamento.
