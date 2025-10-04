# Ajustes necessários no algoritmo de interpretação, identificação e classificação de entidades

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

## Ajustes Pendentes

Nenhum ajuste pendente no momento.

