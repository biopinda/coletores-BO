# Documentação: gerar_relatorios.py

## Descrição
O script `gerar_relatorios.py` é responsável por criar relatórios detalhados e visualizações dos resultados da canonicalização. Oferece múltiplos formatos e tipos de análise para diferentes audiências e necessidades.

## Funcionalidades Principais

### 1. Relatórios Estatísticos
- **Visão geral**: Estatísticas gerais do processo
- **Top coletores**: Coletores mais frequentes
- **Distribuição de qualidade**: Análise da confiança
- **Análise temporal**: Evolução dos dados ao longo do tempo

### 2. Relatórios por Kingdom
- **Plantae**: Coletores especializados em botânica
- **Animalia**: Coletores especializados em zoologia
- **Análise comparativa**: Diferenças entre reinos
- **Crossover**: Coletores que trabalham com ambos

### 3. Relatórios de Qualidade
- **Casos problemáticos**: Identificação de inconsistências
- **Recomendações**: Ações sugeridas para melhoria
- **Métricas de sucesso**: KPIs do processo de canonicalização

### 4. Exportações Especializadas
- **CSV para análise**: Dados estruturados
- **JSON para APIs**: Integração com sistemas
- **Relatórios executivos**: Resumos para gestão

## Tipos de Relatórios

### 1. Relatório de Estatísticas Gerais
```
================================================================================
RELATÓRIO ESTATÍSTICO - CANONICALIZAÇÃO DE COLETORES
================================================================================
Data/Hora: 2025-09-20 16:45:30
Período de Análise: 2020-01-01 a 2025-09-20

RESUMO EXECUTIVO
----------------------------------------
Total de registros processados: 11,234,567
Coletores únicos identificados: 45,623
Taxa de canonicalização: 246.2 registros/coletor
Eficiência do processo: 94.7%

DISTRIBUIÇÃO DE QUALIDADE
----------------------------------------
Alta confiança (≥0.95): 28,456 coletores (62.4%)
Confiança moderada (0.85-0.94): 12,890 coletores (28.3%)
Baixa confiança (0.70-0.84): 3,456 coletores (7.6%)
Revisão necessária (<0.70): 821 coletores (1.8%)

ANÁLISE POR KINGDOM
----------------------------------------
Especialistas Plantae: 28,450 (62.4%)
  - Registros: 7,234,567 (64.4%)
  - Variações médias: 4.2 por coletor

Especialistas Animalia: 15,120 (33.1%)
  - Registros: 3,567,890 (31.8%)
  - Variações médias: 3.8 por coletor

Generalistas: 2,053 (4.5%)
  - Registros: 432,110 (3.8%)
  - Variações médias: 5.6 por coletor

MÉTRICAS DE PERFORMANCE
----------------------------------------
Tempo total de processamento: 7h 23m
Performance média: 423 registros/segundo
Checkpoints utilizados: 225
Taxa de sucesso: 99.2%
```

### 2. Top Coletores por Frequência
```
================================================================================
TOP 50 COLETORES MAIS FREQUENTES
================================================================================

Rank | Coletor Canônico          | Registros | Variações | Kingdoms       | Confiança
-----|---------------------------|-----------|-----------|----------------|----------
1    | Silva, J.C.              | 15,234    | 23        | P:80% A:20%   | 0.96
2    | Santos, M.A.             | 12,567    | 18        | P:95% A:5%    | 0.94
3    | Costa, R.                | 11,890    | 15        | A:100%        | 0.98
4    | Oliveira, L.P.           | 10,234    | 12        | P:75% A:25%   | 0.92
5    | Pesquisas Biodiversidade | 9,567     | 8         | P:60% A:40%   | 0.89
...

ANÁLISE DOS TOP COLETORES
----------------------------------------
- 50% são especialistas em Plantae
- 35% são especialistas em Animalia
- 15% são generalistas ou grupos de pesquisa
- Confiança média: 0.93
- Variações médias: 16.4 por coletor
```

### 3. Relatório de Variações
```
================================================================================
ANÁLISE DE VARIAÇÕES E PADRÕES
================================================================================

DISTRIBUIÇÃO DE VARIAÇÕES POR COLETOR
----------------------------------------
1 variação: 18,450 coletores (40.4%)
2-5 variações: 15,678 coletores (34.4%)
6-10 variações: 7,234 coletores (15.9%)
11-20 variações: 3,456 coletores (7.6%)
>20 variações: 805 coletores (1.8%)

PADRÕES MAIS COMUNS DE VARIAÇÃO
----------------------------------------
1. Abreviação de nomes:
   - "Silva, João Carlos" → "Silva, J.C." → "Silva, J."

2. Diferenças de capitalização:
   - "SILVA" → "Silva" → "silva"

3. Variações de pontuação:
   - "Silva, J.C." → "Silva J.C" → "Silva JC"

4. Formas completas vs abreviadas:
   - "Santos, Maria Alice" → "Santos, M.A." → "M.A. Santos"

CASOS COMPLEXOS IDENTIFICADOS
----------------------------------------
- Coletores com sobrenomes compostos: 2,345 casos
- Nomes estrangeiros: 1,234 casos
- Grupos de pesquisa: 567 casos
- Variações com caracteres especiais: 890 casos
```

### 4. Relatório de Qualidade Detalhado
```json
{
  "relatorio_qualidade": {
    "data_geracao": "2025-09-20T16:45:30Z",
    "metricas_globais": {
      "total_coletores": 45623,
      "confianca_media": 0.879,
      "desvio_padrao_confianca": 0.123,
      "percentil_95_confianca": 0.985
    },
    "distribuicao_por_faixa": {
      "muito_alta": {"count": 28456, "percent": 62.4},
      "alta": {"count": 12890, "percent": 28.3},
      "media": {"count": 3456, "percent": 7.6},
      "baixa": {"count": 621, "percent": 1.4},
      "muito_baixa": {"count": 200, "percent": 0.4}
    },
    "problemas_identificados": {
      "sobrenomes_inconsistentes": 234,
      "muitas_variacoes_raras": 156,
      "grupos_muito_grandes": 89,
      "tipos_misturados": 45,
      "confianca_muito_baixa": 23
    },
    "recomendacoes": [
      "Revisar 821 casos com confiança < 0.70",
      "Dividir 89 grupos com >20 variações",
      "Separar 45 casos com tipos misturados",
      "Ajustar threshold para reduzir falsos positivos"
    ]
  }
}
```

## Configuração de Relatórios

### Parâmetros Customizáveis
```python
# config/mongodb_config.py
REPORT_CONFIG = {
    'top_n_default': 50,
    'include_examples': True,
    'date_format': '%Y-%m-%d %H:%M:%S',
    'export_formats': ['txt', 'json', 'csv'],
    'quality_thresholds': {
        'muito_alta': 0.95,
        'alta': 0.85,
        'media': 0.70,
        'baixa': 0.50
    }
}
```

### Templates de Relatório
```python
REPORT_TEMPLATES = {
    'executivo': {
        'sections': ['resumo', 'qualidade', 'recomendacoes'],
        'detail_level': 'low',
        'include_technical': False
    },
    'tecnico': {
        'sections': ['estatisticas', 'variacoes', 'problemas'],
        'detail_level': 'high',
        'include_technical': True
    },
    'auditoria': {
        'sections': ['all'],
        'detail_level': 'maximum',
        'include_raw_data': True
    }
}
```

## Execução

### Comandos Disponíveis

#### Gerar Todos os Relatórios
```bash
cd src/
python gerar_relatorios.py
```

#### Relatório Específico
```bash
python gerar_relatorios.py --tipo estatisticas
python gerar_relatorios.py --tipo top --top-n 100
python gerar_relatorios.py --tipo qualidade
python gerar_relatorios.py --tipo variacoes
```

#### Exportação Personalizada
```bash
python gerar_relatorios.py --formato csv --output dados_completos.csv
python gerar_relatorios.py --formato json --kingdom Plantae
python gerar_relatorios.py --template executivo --output relatorio_gestao.pdf
```

### Opções de Linha de Comando
- `--tipo TIPO`: Tipo específico de relatório
- `--formato FORMAT`: txt, json, csv, pdf
- `--output ARQUIVO`: Arquivo de saída personalizado
- `--top-n N`: Número de top coletores
- `--kingdom REINO`: Filtrar por kingdom
- `--template TEMPLATE`: Template pré-definido
- `--periodo INICIO FIM`: Período específico
- `--incluir-exemplos`: Adiciona exemplos detalhados

## Análise Comparativa por Kingdom

### Métricas Especializadas

#### Coletores de Plantae
```python
relatorio_plantae = {
    'total_coletores': 28450,
    'total_registros': 7234567,
    'media_variacoes': 4.2,
    'confianca_media': 0.894,
    'padroes_comuns': [
        'Sobrenomes com origem botânica',
        'Uso frequente de iniciais',
        'Colaborações institucionais'
    ],
    'top_instituicoes': [
        'Jardim Botânico do Rio de Janeiro',
        'Instituto de Botânica de São Paulo',
        'Museu Nacional'
    ]
}
```

#### Coletores de Animalia
```python
relatorio_animalia = {
    'total_coletores': 15120,
    'total_registros': 3567890,
    'media_variacoes': 3.8,
    'confianca_media': 0.887,
    'padroes_comuns': [
        'Nomes mais curtos',
        'Menos variações por coletor',
        'Especialização por grupo taxonômico'
    ],
    'especialidades': [
        'Entomologia': 4560,
        'Ornitologia': 3220,
        'Mastozoologia': 2890,
        'Ictiologia': 2450
    ]
}
```

## Visualizações e Gráficos

### Distribuição de Qualidade
```python
# Dados para gráfico de pizza
quality_distribution = {
    'Muito Alta (≥0.95)': 62.4,
    'Alta (0.85-0.94)': 28.3,
    'Média (0.70-0.84)': 7.6,
    'Baixa (<0.70)': 1.8
}
```

### Timeline de Coletas
```python
# Dados para gráfico temporal
timeline_data = {
    '2020': {'Plantae': 1234567, 'Animalia': 567890},
    '2021': {'Plantae': 1345678, 'Animalia': 678901},
    '2022': {'Plantae': 1456789, 'Animalia': 789012},
    '2023': {'Plantae': 1567890, 'Animalia': 890123},
    '2024': {'Plantae': 1678901, 'Animalia': 901234}
}
```

## Integração com Dashboards

### API de Dados
```python
class RelatorioAPI:
    def get_estatisticas_gerais(self):
        """Retorna estatísticas para dashboard"""
        return {
            'total_coletores': 45623,
            'total_registros': 11234567,
            'qualidade_media': 0.879,
            'taxa_canonicalizacao': 246.2
        }

    def get_top_coletores(self, n=10, kingdom=None):
        """Retorna top N coletores"""
        # Implementação da consulta

    def get_metricas_reino(self, kingdom):
        """Retorna métricas específicas de um reino"""
        # Implementação da consulta
```

### Formato JSON para APIs
```json
{
  "api_version": "1.0",
  "timestamp": "2025-09-20T16:45:30Z",
  "data": {
    "summary": {
      "total_collectors": 45623,
      "total_records": 11234567,
      "avg_confidence": 0.879,
      "canonicalization_rate": 246.2
    },
    "by_kingdom": {
      "Plantae": {
        "collectors": 28450,
        "records": 7234567,
        "avg_variations": 4.2
      },
      "Animalia": {
        "collectors": 15120,
        "records": 3567890,
        "avg_variations": 3.8
      }
    },
    "quality_metrics": {
      "high_confidence": 0.906,
      "needs_review": 0.018,
      "avg_score": 0.879
    }
  }
}
```

## Performance e Otimização

### Consultas Otimizadas
```python
# Índices recomendados para relatórios
db.coletores.createIndex({"total_registros": -1})
db.coletores.createIndex({"confianca_canonicalizacao": -1})
db.coletores.createIndex({"kingdoms.Plantae": -1})
db.coletores.createIndex({"kingdoms.Animalia": -1})
```

### Cache de Resultados
```python
class CacheRelatorios:
    def __init__(self):
        self.cache_duration = 3600  # 1 hora
        self.cache = {}

    def get_cached_report(self, report_type, params):
        cache_key = f"{report_type}_{hash(str(params))}"
        if cache_key in self.cache:
            if time.time() - self.cache[cache_key]['timestamp'] < self.cache_duration:
                return self.cache[cache_key]['data']
        return None
```

## Troubleshooting

### Problemas Comuns

1. **Relatórios Muito Lentos**
   ```python
   # Soluções:
   - Adicionar índices específicos
   - Usar agregações otimizadas
   - Implementar cache
   - Processar por batches
   ```

2. **Memória Insuficiente**
   ```python
   # Para relatórios grandes:
   - Usar cursors com streaming
   - Processar por páginas
   - Filtrar dados desnecessários
   ```

3. **Dados Inconsistentes**
   ```python
   # Verificações:
   - Validar integridade dos dados
   - Comparar com totais conhecidos
   - Verificar atualizações recentes
   ```

## Agendamento e Automação

### Relatórios Automáticos
```python
# Script para execução periódica
import schedule
import time

def gerar_relatorio_diario():
    """Gera relatório diário automaticamente"""
    timestamp = datetime.now().strftime('%Y%m%d')
    os.system(f'python gerar_relatorios.py --output relatorio_diario_{timestamp}.txt')

# Agendar para executar diariamente às 06:00
schedule.every().day.at("06:00").do(gerar_relatorio_diario)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Verifica a cada hora
```

### Integração com CI/CD
```yaml
# .github/workflows/reports.yml
name: Generate Reports
on:
  schedule:
    - cron: '0 6 * * 1'  # Segunda-feira às 06:00

jobs:
  generate-reports:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Generate reports
        run: |
          cd src/
          python gerar_relatorios.py --formato json --output weekly_report.json
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: weekly-reports
          path: reports/
```

## Exemplo de Uso Programático
```python
from gerar_relatorios import GeradorRelatorios

# Inicializar gerador
gerador = GeradorRelatorios()

# Gerar relatório executivo
relatorio_executivo = gerador.gerar_relatorio_executivo()

# Top coletores por kingdom
top_botanicos = gerador.gerar_top_coletores(kingdom='Plantae', n=20)
top_zoologos = gerador.gerar_top_coletores(kingdom='Animalia', n=20)

# Exportar para CSV
gerador.exportar_csv(
    dados=top_botanicos,
    arquivo='top_botanicos.csv',
    colunas=['coletor_canonico', 'total_registros', 'confianca']
)

# Relatório de qualidade personalizado
qualidade = gerador.analisar_qualidade(
    threshold_baixa=0.7,
    incluir_exemplos=True
)

print(f"Relatórios gerados em: {gerador.diretorio_saida}")
```