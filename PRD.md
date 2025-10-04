# PRD - Sistema de Identificação e Canonicalização de Coletores de Plantas

Este projeto irá desenvolver um algoritmo para identificar coletores de amostras de plantas representados em um campo de uma coleção, em um banco de dados MongoDB. O desenvolvimento deste algoritmo é centrado no reconhecimento de padrões de representação destes coletores, através da análise de uma string. Esta análise irá seguir o seguinte pipeline de processamento:

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

## Pessoa

- Nome próprio de uma única pessoa
- Ex: "Silva, J.C.", "Maria Santos", "A. Costa", "G.A. Damasceno-Junior"
- Confiança baseada na presença de padrões de nomes individuais

## Conjunto de Pessoas

- Múltiplos nomes próprios para atomização
- Ex: "Silva, J.; Santos, M.; et al.", "Gonçalves, J.M.; A.O.Moraes"
- Contém nomes próprios separados por `;`, `&`, ou `et al.`
- Deve ser atomizado para separar as diferentes pessoas

## Grupo de Pessoas

- Denominações genéricas SEM nomes próprios
- Ex: "Pesquisas da Biodiversidade", "Alunos da disciplina", "Equipe de pesquisa"
- Coletores não identificados ou anônimos

## Empresa/Instituição

- Acrônimos e códigos institucionais
- Ex: "EMBRAPA", "USP", "RB", "INPA", "Universidade Federal"
- Universidades, museus, herbários
- Empresas e órgãos governamentais

## Não determinado

- Ex: "?", "sem coletor", "não identificado"

Deve ser feita uma profunda pesquisa em algoritmos já existentes para lidar, identificar e classificar strings com nomes de pessoas, assim como algoritmos mais apropriados para agrupá-los por similaridade, que implica que, por exemplo, "Forzza, R.C.", "Forzza, R.", "R.C. Forzza", e "Rafaela C. Forzza" são representações da mesma entidade (pessoa) e devem ser agrupados.

Existem modelos no Hugging Face dedicados ao **NER (Named Entity Recognition)**, que identificam entidades nomeadas como nomes de pessoas em textos.

Para **português**, alguns modelos populares incluem:

- **neuralmind/bert-base-portuguese-cased** - um modelo BERT treinado para português que pode ser fine-tuned para NER
- **pierreguillou/bert-base-cased-pt-lenerbr** - modelo BERT treinado especificamente no dataset LeNER-Br para NER em português
- **pucpr/biobertpt-all** e **pucpr/biobertpt-clin** - focados em textos biomédicos mas também reconhecem entidades PESSOA

Para **inglês e multilíngue**:

- **dslim/bert-base-NER** - muito popular para inglês
- **xlm-roberta-large-finetuned-conll03-english** - modelo multilíngue
- **Babelscape/wikineural-multilingual-ner** - suporta vários idiomas

**✓ IMPLEMENTADO**: Sistema de NER fallback usando **pierreguillou/bert-base-cased-pt-lenerbr**

O modelo NER foi implementado com as seguintes características:
- **Ativação Automática**: Quando confiança da classificação < 0.70
- **GPU-Accelerado**: Usa CUDA automaticamente se disponível (10-20x mais rápido)
- **Modelo**: Portuguese BERT fine-tuned no LeNER-Br dataset
- **Tamanho**: 414 MB na GPU
- **Performance**: 0.03s por texto com GPU (vs 2s com CPU)
- **Boost de Confiança**: +0.05 a +0.15 baseado em detecção de entidades
- **Lazy Loading**: Modelo carrega apenas quando necessário

O sistema usa uma abordagem híbrida:
1. **Classificação baseada em regras** (rápida, sem AI)
2. **Fallback NER com BERT** (apenas para casos com baixa confiança)

Esta implementação garante melhor precisão sem sacrificar performance na maioria dos casos.

O resultado da análise e agrupamento será armazenado em um banco de dados, contendo o "nome canônico do coletor" e todas as suas variações. Conforme os dados forem sendo analisados e padrões e agrupamentos forem sendo encontrados e realizados, o banco de dados irá sendo atualizado, dinamicamente, durante o processamento. Considere que a análise será realizada com cerca de 4.6 milhões de registros onde o "kingdom" == "Plantae". Assim, desempenho é crucial. Encontre a melhor forma de registrar o resultado da análise (por exemplo, um banco de dados local SQL).

Ao final, um relatório completo de nome canônico definido com suas variações e contagem de ocorrências para cada variação deve ser apresentado em uma tabela simples, no formato .CSV e o banco de dados local mantido para futuros tratamentos. A análise desta tabela, e do banco de dados, irá provocar ajustes nas regras de identificação, separação e agrupamento das entidades, que devem estar claramente definidas em uma documentação que irá ser editada, para refinamento do algoritmo.

Desta forma, os produtos finais deste projeto são:

- Um algoritmo robusto e maduro, que foi desenvolvido analisando um conjunto de mais de 4.6 milhões de registros;
- uma base de dados com nomes canônicos de entidades (Pessoas, Grupo de Pessoas e Empresa/Instituição) e suas variações, com um índice de confiança da classificação e do agrupamento ou relação com o nome canônico.

Uma série de ajustes já foram feitos nas regras de normalização, detecção e formatação canônica. Mantenha estas regras.

A rotina de rodar o processamento com uma amostra de dados, e melhorar o algoritmo passando instruções no arquivo /docs/fix.md vai continuar como atividade central de melhoria do algoritmo. Assim, o report em CSV e a carga no banco de dados DuckDB também devem ser mantidas.
