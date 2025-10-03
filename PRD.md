Este projeto irá desenvolver um algoritmo para identificar coletores de amostras de plantas representados em um campo de uma coleção, em um banco de dados MongoDB. O deenvolvimento deste algoritmo é centrado no reconhecimento de padrões de representação destes coletores, através da análise de uma string. Esta análise irá seguir o seguinte pipeline de processamento:

Entrada: "Silva, J. & R.C. Forzza; Santos, M. et al."
    ↓
[1] CLASSIFICAÇÃO → "conjunto_pessoas" (confiança: 0.95)
    ↓
[2] ATOMIZAÇÃO → ["Silva, J.", "R.C. Forzza", "Santos, M."]
    ↓
[3] NORMALIZAÇÃO → Para cada nome individual
    ↓
[4] CANONICALIZAÇÃO → Agrupamento por similaridade
    ↓
Saída: Coletores canônicos com variações agrupadas

O algoritmo irá Classificar os registros em cinco categorias principais com índice de confiança:

#### Pessoa

- Nome próprio de uma única pessoa
- Ex: "Silva, J.C.", "Maria Santos", "A. Costa", "G.A. Damasceno-Junior"
- Confiança baseada na presença de padrões de nomes individuais

#### Conjunto de Pessoas

- Múltiplos nomes próprios para atomização
- Ex: "Silva, J.; Santos, M.; et al.", "Gonçalves, J.M.; A.O.Moraes"
- Contém nomes próprios separados por `;`, `&`, ou `et al.`
- Deve ser atomizado para separar as diferentes pessoas

#### Grupo de Pessoas

- Denominações genéricas SEM nomes próprios
- Ex: "Pesquisas da Biodiversidade", "Alunos da disciplina", "Equipe de pesquisa"
- Coletores não identificados ou anônimos

#### Empresa/Instituição

- Acrônimos e códigos institucionais
- Ex: "EMBRAPA", "USP", "RB", "INPA", "Universidade Federal"
- Universidades, museus, herbários
- Empresas e órgãos governamentais

#### Não determinado
- Ex: "?", "sem coletor", "não identificado"

Dese ser feita uma profunda pesquisa em algoritmos já existentes para lidar, identificar e classificar strings com nomes de pessoas, assim como allgoritmos mais apropriados para agrupá-los por similaridade, que implica que, poe exemplo, "Forzza, R.C.", "Forzza, R.", "R.C. Forzza", e "Rafaela C. Forzza" são representações da mesma entidade (pessoa) e devem ser agrupados.

O resultado da análise e agrupamento será armazenado em um banco de dados, contendo o "nome canônico do coletor" e todas as suas variações. Conforme os dados forem sendo analisados e padrões e agrupamentos forem sendo encontrados e realizados, o banco de dados irá sendo atualizado, dinâmicamente, durante o processamento. Considere que a análise será realizada com cerca de 4.6 milhões de registros onde o "kingdom" == "Plantae". Assim, desenpenho pr crucial. Encontre a melhor forma de registrar o resultado da análise (por exemplo, um banco de dados local SQL).

Ao final, um relatório completo de nome canônico definido com suas variações e contagem de ocorrências para cada variação deve ser apresentado em uma tabela simples, no formato .CSV e o banco de dados local mantido para futuros tratamentos. A análise desta tabela, e do banco de dados, irá provocar ajustes nas regras de identificação, separação e agrupamento das entidades, que devem estar claramente definidas em uma documentação que irá ser editada, para refinamento do algoritmo.

Desta forma, os produtos finais deste projeto são:
* Um algoritmo robusto e maduro, que foi desenvolvido analisando um conjunto de mais de 4.6 milhões de registros;
* uma base de dados com nomes canônicos de entidades (Pessoas, Grupo de Pessoas e Empresa/Instituição) e suas variações, com um índice de confiança da classificação e do agrupamento ou relação com o nome canônico.