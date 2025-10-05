# Ajustes necessários no processamento e no algoritmo de interpretação, identificação e classificação de entidades

## ✅ Regras de Formatação Implementadas (2025-10-04)

### Normalização (apenas para comparação)
- A string normalizada (UPPERCASE) é usada **APENAS** para comparação e busca de similaridade
- A normalização NÃO é armazenada no banco de dados ou CSV

### Formato do canonicalName
- **Pessoa**: `"Andrade, I.R."` (primeira letra maiúscula no sobrenome, iniciais em maiúscula)
- **Empresa/Instituição**: `"EMBRAPA"` (tudo em maiúscula)
- **GrupoPessoas**: `"EQUIPE DE PESQUISA"` (tudo em maiúscula)
- **NãoDeterminado**: formato original preservado

### Formato das Variações
- As variações são armazenadas **exatamente como estão no MongoDB original**
- Exemplos:
  - MongoDB: `"Forzza, R.C."` → Variação: `"Forzza, R.C."`
  - MongoDB: `"R.C. Forzza"` → Variação: `"R.C. Forzza"`
  - MongoDB: `"EMBRAPA"` → Variação: `"EMBRAPA"`
  - MongoDB: `"Embrapa"` → Variação: `"Embrapa"`

---

## ✅ Ajustes Implementados (2025-10-04)

### Normalização
* ✅ ". L. Azevedo, L.O." - Remove pontuação inicial → "L. Azevedo, L.O."
* ✅ "Botelho, R.D. ET. AL." - Remove "et al." e variações (et. al., Et. Al., et alli, etc.)
* ✅ "G.M. Antar Et. Al." - Remove todas as variações de "et al"

### Canonicalização
* ✅ "Alisson Nogueira Braz" → "Braz, A.N." (nomes completos sem iniciais)
* ✅ "D.R. Gonzaga" → "Gonzaga, D.R." (iniciais antes do sobrenome)
* ✅ "Débora G. Takaki" → "Takaki, D.G." (nome completo + inicial + sobrenome)
* ✅ "G.M. Antar" → "Antar, G.M." (múltiplas iniciais + sobrenome)

### Atomização
* ✅ "Fernandes, F. M, Nogueira, J. B" - Detecta e separa nomes com vírgula como separador
* ✅ "Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré" - Melhoria na detecção de conjuntos

## ✅ Ajustes Implementados (2025-10-05)

### Normalização
* ✅ Strings com números inválidos são descartadas (ex: "Hh-10512, G.H.", "1006, M.E.")
* ✅ Melhorada remoção de "et al" em qualquer posição da string (não apenas no final)
* ✅ Adicionado suporte ao caractere "|" como separador

### Classificação
* ✅ Melhorada detecção de conjuntos de pessoas:
  * Múltiplos nomes separados por vírgula (padrão "Surname, Initials" repetido)
  * Nomes com números associados (ex: "I. E. Santo 410, M. F. CASTILHORI 444")
  * Palavras-chave de grupo em listas (ALUNOS, EQUIPE, GRUPO)
  * Suporte ao separador "|"

### Canonicalização
* ✅ Corrigida conversão de nomes completos para iniciais: "Grespan, TIAGO" → "Grespan, T."

### Atomização
* ✅ Adicionado suporte ao separador "|" (pipe)
* ✅ Remoção automática de números associados a nomes (ex: "I. E. Santo 410" → "I. E. Santo")
* ✅ Melhorada remoção de "et al" em conjuntos

### Agrupamento
* ✅ Implementada verificação de similaridade contra variações existentes
* ✅ Agrupa corretamente variações como "Korte, A" e "Korte, A."
* ✅ Agrupa variações fonéticas similares (ex: "Kumerrow", "Kummorov", "Kummrov", "Kummrow")

## ✅ Ajustes de NER Fallback (2025-10-05)

### Uso Mais Generoso do NER Fallback
* ✅ Threshold de acionamento aumentado de 0.70 para **0.85**
  * Agora o NER fallback é usado em muito mais casos
  * Apenas classificações de muito alta confiança não passam pelo NER

### Redução de Confiança nas Classificações
* ✅ Empresa (sigla maiúscula): 0.95 → **0.85**
* ✅ Conjunto de Pessoas: 0.92 → **0.82**
* ✅ Pessoa (padrão "Sobrenome, Iniciais"): 0.90 → **0.80**
* ✅ Pessoa (com iniciais, sem padrão estrito): 0.75 → **0.65**
* ✅ Grupo de Pessoas: 0.80 → **0.70**
* ✅ Fallback padrão: 0.70 → **0.60**

### Descarte Automático via NER
* ✅ Implementado descarte de strings inválidas:
  * Texto muito curto (<3 caracteres) sem entidades reconhecidas
  * Texto com baixa proporção de caracteres alfabéticos (<50%)
  * Todas as entidades com confiança muito baixa (<0.50)
  * Strings que retornam confiança 0.0 são marcadas como NAO_DETERMINADO

### Melhorias no NER Fallback
* ✅ Confiança mais conservadora (máximo 0.90 ao invés de 0.95)
* ✅ Detecção de múltiplas pessoas (classifica como CONJUNTO_PESSOAS)
* ✅ Lógica de confiança baseada em scores do NER:
  * Score >0.85: confiança 0.85
  * Score >0.70: confiança 0.75
  * Score >0.50: confiança 0.70
  * Sem entidades claras: confiança 0.65

## ✅ Ajustes Implementados (2025-10-05 - Parte 2)

### Variações Únicas
* ✅ Implementada verificação de duplicatas no canonicalizer
* ✅ Variações são registradas apenas uma vez (case-sensitive)
* ✅ Contador de ocorrências atualizado para variações existentes

### Descarte de Strings Inválidas
* ✅ Descartadas strings que começam com números (ex: "13313, A.C.B.")
* ✅ Descartadas strings que começam com separador "|" (ex: "|Amanda, A.")
* ✅ Descartados nomes genéricos isolados (uma palavra, sem pontuação)
  * Exemplos: "Soares", "Solange", "Nilda", "Márcio"

### Agrupamento Fonético Melhorado
* ✅ Peso fonético aumentado de 0.2 para 0.3
* ✅ Peso Levenshtein ajustado de 0.4 para 0.3
* ✅ Comparação sem pontuação/espaços para match exato
* ✅ Agrupa melhor variações como:
  * "Zaslawski, W." e "Zaslawsky, W." (fonética similar)
  * "Nascimento, J. C. F" e "Nascimento, J.C.F." (pontuação diferente)
  * "Zappi, L.", "Zappi, L.F.", "Zappia, L" (variações fonéticas)

### Detecção de Conjuntos Melhorada
* ✅ Detecta padrão "Name & Name" com ampersand
* ✅ Detecta múltiplos nomes curtos (ex: "Y. Pires, C. GOMES, E. ADAIS")
* ✅ Melhores padrões regex para conjuntos complexos

## Ajustes Pendentes

Nenhum ajuste pendente no momento.

