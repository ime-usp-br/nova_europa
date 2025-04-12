# Controle de Versão da Documentação do Repositório

**Versão:** 0.1.0<br>
**Data:** 2025-04-12

## 1. Introdução

Este documento descreve a estratégia adotada para o controle de versão dos arquivos de documentação em formato Markdown (`.md`) que residem **dentro deste repositório Git**. O objetivo é garantir que a documentação reflita de forma clara e consistente a versão do código do **Laravel 12 USP Starter Kit** a que se refere.

**Nota:** Esta estratégia **NÃO SE APLICA** à Wiki do GitHub, que possui seu próprio histórico de revisões.

## 2. Princípios Fundamentais

1.  **Alinhamento com o Código:** A versão de um documento `.md` no repositório **DEVE** corresponder à versão da tag Git (release) do Starter Kit que ele descreve.
2.  **Versionamento Semântico Adaptado:** Utilizamos o [Versionamento Semântico 2.0.0 (SemVer)](https://semver.org/lang/pt-BR/) como base, adaptando seu significado para o contexto da documentação:
    *   **MAJOR:** Incrementada para mudanças drásticas na estrutura da documentação, remoção de seções principais, ou quando a documentação reflete uma mudança incompatível (MAJOR) no código do Starter Kit.
    *   **MINOR:** Incrementada quando se adiciona documentação para novas funcionalidades (MINOR) do Starter Kit, se adicionam novas seções significativas, ou se realizam grandes reescritas/reorganizações que mantêm a compatibilidade informacional.
    *   **PATCH:** Incrementada para correções de erros de digitação, links quebrados, pequenos esclarecimentos, melhorias em exemplos, ajustes de formatação, ou quando a documentação é atualizada para refletir correções de bugs (PATCH) no código.
3.  **Clareza na Identificação:** A versão e a data da última atualização daquela versão **DEVEM** ser claramente indicadas no início de cada documento versionado.

## 3. Formato e Localização da Versão

Todo arquivo `.md` sujeito a este versionamento (veja Seção 6 - Escopo) **DEVE** incluir o seguinte bloco de cabeçalho logo após o título principal (linha 1 ou 2):

```markdown
**Versão:** X.Y.Z
**Data:** YYYY-MM-DD
```

*   `X.Y.Z`: Representa a tag de versão SemVer do release correspondente (ex: `0.1.0`, `1.0.0`).
*   `YYYY-MM-DD`: Representa a data em que a tag de release `X.Y.Z` foi criada.

## 4. Processo de Atualização

*   A `Versão` e a `Data` nos cabeçalhos dos documentos **DEVEM** ser atualizadas como parte do processo de criação de um novo release do Starter Kit.
*   O commit que contém essas atualizações nos cabeçalhos dos arquivos `.md` **DEVE** ser o commit que será marcado com a nova tag de release (ex: `git tag v0.2.0 <commit_sha>`).
*   **Correções entre Releases:** Se uma correção menor (typo, link quebrado) for necessária na documentação entre dois releases oficiais, ela **PODE** ser commitada diretamente no branch principal (ou via PR). No entanto, a `Versão` e `Data` no cabeçalho do documento **NÃO PRECISAM** ser atualizadas nesse momento. Elas só serão atualizadas para a próxima versão quando o próximo release for efetivamente preparado e tagueado. O conteúdo do documento no branch principal deve sempre refletir o estado mais atual, mas o cabeçalho reflete a *última versão lançada* que contém aquele conteúdo (ou suas correções).

## 5. Versionamento Inicial

*   Considerando que este é o início do projeto, a versão inicial estabelecida para todos os documentos `.md` versionáveis no repositório é **`0.1.0`**.
*   A data associada a esta versão inicial é **`2025-04-12`**.

## 6. Escopo do Versionamento

Esta estratégia de versionamento **SE APLICA** aos seguintes arquivos `.md` dentro do repositório:

*   `README.md`
*   `docs/guia_de_desenvolvimento.md`
*   `docs/termo_abertura_projeto.md`
*   `docs/versionamento_documentacao.md` (este arquivo)
*   `docs/adr/*.md` (Todos os Arquivos de Decisão de Arquitetura)
*   `padroes_codigo_boas_praticas.md`

Esta estratégia **NÃO SE APLICA** a:

*   `LICENSE` (O conteúdo da licença geralmente não muda e não requer versionamento SemVer).
*   Conteúdo da Wiki do GitHub.
*   Arquivos de código (`.php`, `.js`, `.css`, etc.).
*   Arquivos de configuração (`.env`, `.neon`, `.xml`, etc.).

## 7. Rastreamento de Mudanças (Changelog)

É **RECOMENDÁVEL** manter um registro das mudanças significativas entre as versões do Starter Kit (e, consequentemente, da documentação versionada). Isso pode ser feito através de:

*   Um arquivo `CHANGELOG.md` na raiz do repositório, seguindo um formato como o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
*   Utilizando o recurso "Releases" do GitHub para detalhar as mudanças em cada tag criada.

Manter um changelog ajuda os usuários a entenderem rapidamente o que foi alterado, adicionado ou corrigido em cada nova versão do Starter Kit e de sua documentação.