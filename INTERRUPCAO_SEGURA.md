# Sistema de Interrupção Segura - Processar Coletores

## Como Interromper o Script com Segurança

O `processar_coletores.py` possui um sistema robusto de checkpoint e interrupção segura que preserva a integridade da coleção "coletores".

### 1. Formas Seguras de Interrupção

#### Método 1: Ctrl+C (Recomendado)
```bash
# Durante a execução do script, pressione:
Ctrl + C
```

**IMPORTANTE**: Se o script não responder imediatamente ao primeiro Ctrl+C:
- ⏳ Aguarde até 30 segundos (timeout das operações MongoDB)
- 🔄 Se ainda não responder, pressione Ctrl+C novamente para **forçar saída imediata**

#### Método 1b: Saída Forçada (Emergência)
```bash
# Se o primeiro Ctrl+C não funcionar:
Ctrl + C  (segunda vez - força saída imediata)
```

#### Método 2: Sinal SIGTERM (Linux/Unix)
```bash
# Em outro terminal, encontre o PID do processo:
ps aux | grep processar_coletores

# Envie sinal de término seguro:
kill -TERM <PID>
```

#### Método 3: Sinal SIGINT (Linux/Unix)
```bash
kill -INT <PID>
```

### 2. O que Acontece Durante a Interrupção

Quando você interrompe o script:

1. **Detecção do Sinal**: O script detecta a solicitação de parada
2. **Finalização do Lote Atual**: Completa o processamento do lote em andamento
3. **Checkpoint Automático**: Salva automaticamente o estado atual
4. **Fechamento Seguro**: Fecha conexões e libera recursos
5. **Log da Interrupção**: Registra a interrupção nos logs

**Exemplo de log:**
```
2025-09-20 10:32:45 - WARNING - Sinal recebido (2). Iniciando parada controlada...
2025-09-20 10:32:46 - INFO - Interrupção solicitada. Salvando checkpoint...
2025-09-20 10:32:47 - INFO - Checkpoint 15 salvo
```

### 3. Reiniciando do Ponto de Parada

#### Reinício Automático (Recomendado)
```bash
cd src
python processar_coletores.py
```

O script automaticamente:
- Detecta checkpoint existente
- Carrega estado anterior
- Continua do ponto exato da interrupção
- Preserva todas as estatísticas

#### Reinício Forçado (Recomeça do Zero)
```bash
cd src
python processar_coletores.py --restart
```

⚠️ **ATENÇÃO**: `--restart` limpa toda a coleção "coletores" e recomeça do zero!

### 4. Sistema de Checkpoint

#### Frequência de Checkpoint
- **Automático**: A cada 50.000 registros processados (configurável)
- **Interrupção**: Sempre ao interromper o script
- **Finalização**: Ao concluir o processamento

#### Dados Salvos no Checkpoint
- Total de registros processados
- Total de nomes atomizados
- Total de coletores canônicos
- Registros com erro
- Registros vazios
- Timestamp do checkpoint
- Versão do algoritmo

#### Localização dos Checkpoints
Os checkpoints são salvos na própria base MongoDB, na coleção especial de controle.

### 5. Verificação de Integridade

#### Comando para Verificar Estado
```bash
cd src
python processar_coletores.py --revisao
```

Este comando mostra:
- Coletores que precisam revisão manual
- Estatísticas de qualidade
- Não modifica dados

#### Logs de Monitoramento
```bash
# Monitorar logs em tempo real:
tail -f ../logs/processamento.log
```

### 6. Configurações de Segurança

#### Arquivo: `config/mongodb_config.py`
```python
ALGORITHM_CONFIG = {
    'batch_size': 10000,           # Tamanho do lote
    'checkpoint_interval': 50000   # Frequência de checkpoint
}
```

#### Reduzir Risco de Perda
Para processamentos críticos, reduza o intervalo de checkpoint:
```python
'checkpoint_interval': 10000  # Checkpoint a cada 10k registros
```

### 7. Monitoramento de Progresso

#### Durante a Execução
O script exibe:
- Barra de progresso por lote
- Estatísticas em tempo real
- Status de checkpoint

#### Exemplo de Output
```
Processando lote 25 (10000 registros)...
Processando registros: 100%|████████| 10000/10000 [02:15<00:00, 74.1it/s]
Checkpoint 5 salvo
Total processados: 250,000 registros
```

### 8. Solução de Problemas

#### Checkpoint Corrompido
Se houver problemas com checkpoint:
```bash
# Força reinício (use com cuidado!)
python processar_coletores.py --restart
```

#### Verificar Logs de Erro
```bash
grep "ERROR" ../logs/processamento.log
```

#### Estatísticas da Coleção
O script automaticamente verifica a integridade da coleção "coletores" ao iniciar.

### 9. Boas Práticas

✅ **Recomendado:**
- Use sempre Ctrl+C para interromper
- Deixe o script finalizar o lote atual
- Verifique logs após interrupção
- Teste com amostra pequena primeiro

❌ **Evite:**
- Matar processo forçadamente (`kill -9`)
- Desligar máquina durante processamento
- Interromper conexão de rede abruptamente
- Usar `--restart` sem necessidade

### 10. Exemplo Completo

```bash
# 1. Iniciar processamento
cd D:\git\coletoresDWC2JSON\src
python processar_coletores.py

# 2. Aguardar até ver processamento em andamento
# Processando lote 10 (10000 registros)...

# 3. Interromper com segurança
Ctrl + C

# 4. Aguardar mensagem de checkpoint
# INFO - Checkpoint 8 salvo

# 5. Reiniciar do ponto de parada
python processar_coletores.py

# 6. Verificar que continuou do checkpoint
# INFO - Checkpoint encontrado: 80000 registros processados
```

## Resumo

O sistema garante que:
- ✅ A coleção "coletores" permanece íntegra
- ✅ Nenhum trabalho é perdido
- ✅ Reinício é automático e transparente
- ✅ Processamento é retomado exatamente onde parou
- ✅ Todas as estatísticas são preservadas