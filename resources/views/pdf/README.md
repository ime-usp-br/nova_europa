# PDF Templates

This directory contains Blade templates for generating PDF documents using Browsershot.

## Available Templates

### `evolucao-padrao.blade.php`
Standard student evolution report template.

**Used for**: All courses except those with specific templates below
**Features**:
- Student information header
- Mandatory, Elective, and Free Elective course tables
- Extra-curricular courses (if any)
- Credit consolidation summary
- Color-coded status (green=approved, red=pending, yellow=enrolled)
- Black & white printing support

### `evolucao-45052.blade.php` (To be implemented)
Computer Science (Ciência da Computação) evolution report.

**Additional features**:
- Trilhas (academic tracks) section
- Track completion validation

### `evolucao-45024.blade.php` (To be implemented)
Math Education (Licenciatura em Matemática) evolution report.

**Additional features**:
- Blocos (course blocks) section
- Block completion validation

### `evolucao-map.blade.php` (To be implemented)
Biology programs (45070, 45042) evolution report.

**Additional features**:
- Supplementary elective courses section

## Template Variables

All templates receive the following variables:

```php
[
    'dados' => EvolucaoDTO,  // Complete evolution data
    'colorido' => bool       // Whether to use color (true) or B&W (false)
]
```

### EvolucaoDTO Structure

```php
[
    'aluno' => [
        'codpes' => int,
        'nompes' => string,
        'codcur' => int,
        'nomcur' => string,
    ],
    'curriculo' => [
        'codcrl' => string,
        'curriculo' => array,
        'disciplinas' => Collection,
    ],
    'disciplinasObrigatorias' => Collection,
    'disciplinasEletivas' => Collection,
    'disciplinasLivres' => Collection,
    'disciplinasExtraCurriculares' => Collection,
    'creditosObrigatorios' => [
        'aula' => int,
        'trabalho' => int,
        'total' => int,
        'exigidos_aula' => int,
        'exigidos_trabalho' => int,
        'exigidos_total' => int,
    ],
    'creditosEletivos' => [...],
    'creditosLivres' => [...],
    'porcentagensConsolidacao' => [
        'obrigatorios' => float,
        'eletivos' => float,
        'livres' => float,
        'total' => float,
    ],
    'semestreEstagio' => int,
    'blocos' => Collection|null,   // Only for course 45024
    'trilhas' => Collection|null,  // Only for course 45052
]
```

## Creating New Templates

When creating a new template:

1. **Use semantic HTML**: Modern HTML5 elements work great with Browsershot
2. **CSS Grid/Flexbox**: Use modern CSS layout techniques
3. **Inline styles**: For maximum compatibility, use `<style>` tags in `<head>`
4. **Print-friendly**: Test with both color and B&W printing
5. **Localization**: Use `{{ __('key') }}` for all user-facing text
6. **Page breaks**: Use CSS `page-break-after` or `page-break-before` for multi-page PDFs

### Example Structure

```blade
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ __('Document Title') }}</title>
    <style>
        /* Your CSS here */
    </style>
</head>
<body>
    <!-- Your content here -->
</body>
</html>
```

## Browsershot Configuration

PDFs are generated with these settings:
- **Format**: A4 (210mm x 297mm)
- **Margins**: 10mm on all sides
- **Background**: Enabled (shows background colors/images)
- **Orientation**: Portrait (default)

To customize, edit `PdfGenerationService::gerarEvolucaoPdf()`.

## Testing Templates

Test your templates by:

1. Creating test data with `EvolucaoDTO`
2. Rendering template in browser: `return view('pdf.your-template', ['dados' => $testData, 'colorido' => true]);`
3. Generating PDF: Use `PdfGenerationService::gerarEvolucaoPdf()`
4. Testing both color and B&W modes

## Localization

All templates must support both English and Portuguese. Add translations to:
- `lang/en.json`
- `lang/pt_BR.json`
