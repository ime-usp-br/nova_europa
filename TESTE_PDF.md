# Guia de Teste - Geração de PDF de Evolução

## ⚠️ IMPORTANTE: Rota de Teste Temporária

Este arquivo contém instruções para testar a geração de PDF usando uma **rota temporária**.

**LEMBRE-SE:** Antes de fazer commit/deploy, **REMOVA** os arquivos:
- `routes/web-test.php`
- `TESTE_PDF.md` (este arquivo)

E **reverta** as mudanças em `bootstrap/app.php` (remoção do bloco de rotas de teste).

---

## Pré-requisitos

1. ✅ Credenciais do Replicado configuradas em `.env`:
   ```env
   REPLICADO_HOST=
   REPLICADO_DATABASE=
   REPLICADO_USERNAME=
   REPLICADO_PASSWORD=
   REPLICADO_PORT=
   ```

2. ✅ Node.js/Puppeteer instalado no container Sail (já incluído no Browsershot)

3. ✅ Servidor rodando: `./vendor/bin/sail up -d`

---

## Opção 1: Teste via Rota HTTP (Mais Fácil)

### Passo 1: Acesse a URL de teste

Abra no navegador ou use curl:

```bash
# Substitua 123456 pelo número USP real do aluno
# Substitua 45052001 pelo código do currículo real
http://localhost:8000/test-pdf?codpes=123456&codcrl=45052001
```

### Exemplos de Códigos de Currículo:
- `45052001` - Ciência da Computação (com Trilhas)
- `45024001` - Licenciatura em Matemática (com Blocos)
- `45070001` - Ciências Biológicas
- Outros currículos disponíveis no Replicado

### Passo 2: Verificar o resultado

**Sucesso:** PDF será baixado automaticamente com nome `evolucao_123456.pdf`

**Erro:** JSON com detalhes do erro será retornado:
```json
{
    "error": "mensagem de erro",
    "trace": "stack trace completo"
}
```

---

## Opção 2: Teste via Tinker (Mais Controle)

### Passo 1: Entre no Tinker

```bash
./vendor/bin/sail artisan tinker
```

### Passo 2: Execute o teste

```php
// Importar classes
use App\Services\EvolucaoService;
use App\Services\PdfGenerationService;
use App\Models\User;

// Criar user fake (ou buscar um real)
$user = new User();
$user->codpes = 123456; // Substitua pelo número USP real
$user->name = "Teste";
$user->email = "teste@test.com";

// Instanciar serviços
$evolucaoService = app(EvolucaoService::class);
$pdfService = app(PdfGenerationService::class);

// Processar evolução
$evolucaoDTO = $evolucaoService->processarEvolucao($user, '45052001');

// Gerar PDF e salvar em arquivo
$response = $pdfService->gerarEvolucaoPdf($evolucaoDTO);

// Salvar PDF em arquivo para visualizar
file_put_contents('/var/www/html/storage/app/evolucao_teste.pdf', $response->getContent());

echo "PDF salvo em: storage/app/evolucao_teste.pdf\n";
```

### Passo 3: Visualizar o PDF

```bash
# Copiar do container para sua máquina
docker cp $(docker ps -qf "name=laravel.test"):/var/www/html/storage/app/evolucao_teste.pdf ~/Downloads/

# Ou abrir diretamente no projeto
open storage/app/evolucao_teste.pdf
```

---

## Opção 3: Teste com Dados Mockados (Sem Replicado)

Se você não tem acesso ao Replicado ou quer testar sem depender dele:

```bash
./vendor/bin/sail artisan tinker
```

```php
use App\DTOs\EvolucaoDTO;
use App\Services\PdfGenerationService;

// Criar dados de teste manualmente
$dados = new EvolucaoDTO(
    aluno: [
        'codpes' => 123456,
        'nompes' => 'João Silva da Costa',
        'codcur' => 45052,
        'nomcur' => 'Ciência da Computação',
    ],
    curriculo: [
        'codcrl' => '45052001',
        'curriculo' => [],
        'disciplinas' => collect(),
    ],
    disciplinasObrigatorias: collect([
        [
            'coddis' => 'MAC0110',
            'verdis' => 3,
            'nomdis' => 'Introdução à Computação',
            'creaul' => 4,
            'cretra' => 0,
            'rstfim' => 'A',
            'notfim' => 8.5,
        ],
        [
            'coddis' => 'MAT0120',
            'verdis' => 2,
            'nomdis' => 'Cálculo I',
            'creaul' => 6,
            'cretra' => 0,
            'rstfim' => 'A',
            'notfim' => 7.0,
        ],
    ]),
    disciplinasEletivas: collect([
        [
            'coddis' => 'MAC0439',
            'verdis' => 1,
            'nomdis' => 'Laboratório de Banco de Dados',
            'creaul' => 2,
            'cretra' => 2,
            'rstfim' => 'A',
            'notfim' => 9.0,
        ],
    ]),
    disciplinasLivres: collect([
        [
            'coddis' => 'FLF0114',
            'verdis' => 1,
            'nomdis' => 'Ética',
            'creaul' => 4,
            'cretra' => 0,
            'rstfim' => 'A',
            'notfim' => 8.0,
        ],
    ]),
    disciplinasExtraCurriculares: collect([
        [
            'coddis' => 'FIS0001',
            'verdis' => 1,
            'nomdis' => 'Física I',
            'creaul' => 4,
            'cretra' => 0,
            'rstfim' => 'A',
            'notfim' => 6.5,
        ],
    ]),
    creditosObrigatorios: [
        'aula' => 10,
        'trabalho' => 0,
        'total' => 10,
        'exigidos_aula' => 80,
        'exigidos_trabalho' => 0,
        'exigidos_total' => 80,
    ],
    creditosEletivos: [
        'aula' => 2,
        'trabalho' => 2,
        'total' => 4,
        'exigidos_aula' => 20,
        'exigidos_trabalho' => 10,
        'exigidos_total' => 30,
    ],
    creditosLivres: [
        'aula' => 4,
        'trabalho' => 0,
        'total' => 4,
        'exigidos_aula' => 16,
        'exigidos_trabalho' => 0,
        'exigidos_total' => 16,
    ],
    porcentagensConsolidacao: [
        'obrigatorios' => 12.5,
        'eletivos' => 13.33,
        'livres' => 25.0,
        'total' => 14.29,
    ],
    semestreEstagio: 2,
    blocos: null,
    trilhas: null,
);

// Gerar PDF
$pdfService = app(App\Services\PdfGenerationService::class);
$response = $pdfService->gerarEvolucaoPdf($dados);

// Salvar
file_put_contents('/var/www/html/storage/app/evolucao_mock.pdf', $response->getContent());
echo "PDF mockado salvo em: storage/app/evolucao_mock.pdf\n";
```

---

## Possíveis Erros e Soluções

### Erro: "Connection refused" ou "Replicado error"
**Causa:** Credenciais do Replicado incorretas ou servidor inacessível
**Solução:** Verifique `.env` e teste conexão com Replicado separadamente

### Erro: "Failed to generate PDF: Could not find Chrome"
**Causa:** Puppeteer/Chromium não instalado no container
**Solução:**
```bash
./vendor/bin/sail exec laravel.test npm install -g puppeteer
```

### Erro: "Class 'DOMDocument' not found"
**Causa:** Extensão PHP DOM não instalada
**Solução:** Já deve estar incluída no Sail, mas verifique `php -m | grep dom`

### PDF em branco ou vazio
**Causa:** Dados do DTO vazios ou template com erro
**Solução:**
1. Verifique se `$evolucaoDTO` tem dados: `dd($evolucaoDTO)`
2. Teste o template diretamente: `return view('pdf.evolucao-padrao', ['dados' => $evolucaoDTO, 'colorido' => true]);`

---

## Testando Modo P&B (Preto e Branco)

Para gerar PDF sem cores (modo impressão):

```php
// Via serviço
$response = $pdfService->gerarEvolucaoPdf($evolucaoDTO, colorido: false);

// Via rota
http://localhost:8000/test-pdf?codpes=123456&codcrl=45052001&colorido=0
```

---

## Após Testar

1. ✅ Verificar se PDF foi gerado corretamente
2. ✅ Testar com diferentes cursos (45052, 45024, etc.)
3. ✅ Testar modo colorido e P&B
4. ✅ Validar layout e dados no PDF
5. ⚠️ **REMOVER** arquivos de teste antes do commit:
   - `routes/web-test.php`
   - `TESTE_PDF.md`
   - Reverter alterações em `bootstrap/app.php`

---

## Próximos Passos

Após validar que o PDF está funcionando:

1. Criar controller real para geração de PDF
2. Adicionar rotas autenticadas
3. Implementar validação de permissões (aluno só vê próprio PDF)
4. Criar templates específicos (45052, 45024, MAP)
5. Adicionar testes automatizados
