# Ajustes na interpretação, identificação e classificação de entidades

* canonicalNames devem ser representados como `Guimarães, T. M.`, e não `GUIMARÃES, T. M.`. Esta representação deve valer tanto para o arquivo .CSV quando para o registro no banco de dados;
* Nunca usar `"` no registro de entidades no arquivo `canonical_report.csv` ou no banco de dados;
* Registros de `canonicalName` no banco de dados estão iniciando com `; `. Corrigir!
* O campo do banco de dados e do arquivo .CSV é `canonicalName`
* Ajuste as regras.

---

## Ajustes Implementados

### ✅ 1. Capitalização dos Nomes Canônicos

* **Alteração**: Modificado `_format_canonicalName()` em `canonicalizer.py` para usar `.title()` em vez de manter maiúsculo
* **Resultado**: Nomes como `Guimarães, T. M.` em vez de `GUIMARÃES, T. M.`

### ✅ 2. Remoção de Aspas no CSV

* **Alteração**: Adicionado `quoting=3` (QUOTE_NONE) no `export_to_csv()`
* **Resultado**: Valores sem aspas desnecessárias no arquivo CSV

### ✅ 3. Campo Renomeado

* **Alteração**: Campo `canonicalName` consolidado em todo o código
* **Arquivos afetados**:
  * `src/storage/local_db.py` (schema, queries, índices)
  * `src/models/entities.py`
  * `src/models/schemas.py`
  * `specs/main/contracts/pipeline_contracts.py`
  * Documentação (README.md, data-model.md)

### 🔄 4. Problema "; " no Início (Pendente)

* **Status**: Identificado mas não corrigido
* **Possível causa**: Problema na serialização/desserialização JSON das variações
* **Próximos passos**: Investigar como as variações são salvas/recuperadas do banco

### 📋 Regras Ajustadas

* Nomes canônicos agora seguem capitalização Title Case
* CSV usa TAB como separador sem aspas
* Campo padronizado como `canonicalName` (camelCase)
