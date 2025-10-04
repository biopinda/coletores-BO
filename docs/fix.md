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

## Ajustes Pendentes

* ". L. Azevedo, L.O." está iniciando com ". ". Corrigir
* "Alisson Nogueira Braz" é uma pessoa, mas seu canonicalName deve ser "Braz, A.N.". Sempre use este padrão para nomes completos sem iniciais definidas
* "Botelho, R.D. ET. AL." novamente "ET. AL." atrapalhando a definição do canonicalName. Corrija.
* "Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré" é um conjunto de pessoas
* "D.R. Gonzaga" deve ser canonizado para "Gonzaga, D.R."
* "Débora G. Takaki" deve ser canonizado como "Takaki, D.G."
* "Fernandes, F. M, Nogueira, J. B" São duas pessoas: "Fernandes, F. M." e "Nogueira, J. B."
* "G.M. Antar Et. Al." outra forma de "et al" atrapalhando. Encontre uma forma de identificar "et al" e "et alli" em todas as suas formas e descartar

