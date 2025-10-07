# Validador CNAB400 - Bradesco

Ferramenta inicial para validação de arquivos CNAB400 (Remessa) do Banco Bradesco.

Status: MVP cobrindo:

- Verificação de tamanho de linha (400 posições)
- Identificação de tipos de registro (Header, 1, 2, 7, Trailer futuro)
- Validações de campos principais do Registro Header e Registro Tipo 1
- Relatório em JSON ou texto
- Validação opcional do DV do Nosso Número (usar --validar-nosso-numero)
- Inclusão registros placeholder tipos 3 e 6

Como usar:

```
python validate_cnab.py caminho/arquivo.rem --formato json --seculo-base 2000 --tolerancia-centavos 2 --min-severidade field --validar-nosso-numero
```

Saída exemplo (JSON):

```json
{
  "valid": false,
  "errors": [
    {
      "line": 2,
      "record_type": "1",
      "field": "codigo_banco_debito",
      "position": "063-065",
      "expected": "237",
      "found": "000"
    }
  ]
}
```

Próximos passos sugeridos:

- Completar todos os campos do layout (Tipos 1,2,3,6,7, Trailer)
- Suporte a retorno (layout retorno)
- Regras condicionais (ex: multa só se indicador = '2')
- Exportar relatório em CSV/Excel/JSONL/HTML
- Testes unitários
- Tolerância configurável (já suportado via --tolerancia-centavos)
- Filtro de severidade (já suportado via --min-severidade)
- Externalizar layout (JSON/YAML)

Estrutura:

```
layouts/bradesco_cnab400.py  -> Definições de campos
validator.py                -> Engine de validação
validate_cnab.py            -> CLI
```
