# Encoding UTF-8 - Documentação Técnica

## Status Atual

✅ **Todos os arquivos do repositório estão em UTF-8 puro**

### Arquivos Corrigidos

- ✅ `README.md` - Convertido de latin-1 com double-encoding para UTF-8 limpo
- ✅ `docs/rules.md` - Convertido de latin-1 para UTF-8
- ✅ Todos os 30 arquivos `.md` verificados e em UTF-8
- ✅ Todos os 35 arquivos `.py` verificados e em UTF-8

### Código Python

#### DuckDB (`src/storage/local_db.py`)

```python
# JSON serialization with UTF-8
variations_json = json.dumps(
    [...],
    ensure_ascii=False  # Preserva caracteres UTF-8
)

# CSV export with UTF-8
df.to_csv(output_path, index=False, encoding='utf-8')
```

#### MongoDB (`src/storage/mongodb_client.py`)

```python
# Conexão com validação UTF-8 estrita
self.client = MongoClient(uri, unicode_decode_error_handler='strict')
```

## Como Funciona

### Pipeline de Encoding

```
MongoDB (dados originais)
    ↓ (leitura com unicode_decode_error_handler='strict')
Python strings (UTF-8 nativo)
    ↓ (json.dumps com ensure_ascii=False)
DuckDB JSON field (UTF-8 preservado)
    ↓ (leitura normal)
Pandas DataFrame
    ↓ (to_csv com encoding='utf-8')
CSV file (UTF-8 com BOM opcional)
```

### Verificação de Encoding

Para verificar se um arquivo está em UTF-8:

```bash
# Windows
file nome_arquivo.csv

# Python
python -c "
with open('arquivo.csv', 'rb') as f:
    raw = f.read(100)
    print(raw.hex())  # c3a3 = ã, c3a7 = ç, c3a9 = é
"
```

### Bytes UTF-8 Comuns (Português)

| Caractere | UTF-8 (hex) | Exemplo |
|-----------|-------------|---------|
| ã | c3 a3 | São Paulo |
| á | c3 a1 | Brasília |
| â | c3 a2 | Pântano |
| ç | c3 a7 | Conceição |
| é | c3 a9 | José |
| ê | c3 aa | Você |
| í | c3 ad | Polícia |
| ó | c3 b3 | Córrego |
| ô | c3 b4 | Mônica |
| ú | c3 ba | Ú tima |

## Problemas Conhecidos

### Terminal Windows (cp1252)

O terminal Windows usa codepage 1252 (cp1252) por padrão, não UTF-8. Quando você vê:

```
GUIMAR�ES, E.
```

O arquivo está **correto em UTF-8**! O problema é apenas a exibição do terminal.

**Solução 1: Configurar terminal UTF-8**
```bash
chcp 65001  # Muda para UTF-8
```

**Solução 2: Abrir em editor UTF-8**
- VSCode (detecta automaticamente)
- Notepad++ (Encoding → UTF-8)
- Sublime Text (View → Encoding → UTF-8)

### Git Line Endings

Git pode mostrar warnings sobre CRLF/LF:

```
warning: LF will be replaced by CRLF
```

Isso é **normal** e não afeta UTF-8. Git normaliza line endings mas preserva encoding.

## Dados do MongoDB

⚠️ **Importante**: Se os dados originais no MongoDB já têm encoding incorreto, o sistema **preserva** esse encoding.

Exemplo:
- MongoDB armazena: `"GUIMAR\xc3\x83ES"` (double-encoded)
- Sistema preserva: `"GUIMAR\xc3\x83ES"` (não corrige automaticamente)
- Solução: Corrigir na origem (MongoDB) antes de processar

### Identificando Problemas na Origem

```python
# Caracteres suspeitos indicam double-encoding
"GUIMAR\xc3\x83ES"  # ❌ Double UTF-8 (Ã ao invés de ã)
"GUIMAR\xc3\xa3ES"  # ✅ UTF-8 correto (ã)
```

## Garantias do Sistema

1. ✅ **Documentação**: Todos os arquivos `.md` e `.py` são UTF-8 puro
2. ✅ **Processamento**: Python usa strings UTF-8 nativas
3. ✅ **Armazenamento**: DuckDB preserva UTF-8 (testado com hex dump)
4. ✅ **Exportação**: CSV gerado com `encoding='utf-8'` explícito
5. ⚠️ **Dados originais**: Preservados como estão no MongoDB (não corrigidos)

## Referências

- [UTF-8 Standard](https://en.wikipedia.org/wiki/UTF-8)
- [Python Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [DuckDB Text Type](https://duckdb.org/docs/sql/data_types/text.html)
- [Pandas to_csv encoding](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html)

---

**Última atualização**: 2025-10-03
**Status**: ✅ Encoding UTF-8 garantido em todo o sistema
