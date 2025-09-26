"""
Script Orchestration Service

Orquestra a execução dos scripts existentes através da nova camada CLI,
mantendo compatibilidade com scripts legados e adicionando funcionalidades
de monitoramento e validação.
"""

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .config_integration import config_integrator
from .performance_monitor import PerformanceMonitor


class ScriptStatus(Enum):
    """Status de execução de scripts"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ScriptExecution:
    """Dados de execução de um script"""
    script_name: str
    command: List[str]
    status: ScriptStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    process_id: Optional[int] = None


class ScriptOrchestrator:
    """
    Orquestrador de scripts que integra scripts existentes com nova infraestrutura
    """

    def __init__(self, enable_monitoring: bool = True):
        self.logger = logging.getLogger(__name__)
        self.enable_monitoring = enable_monitoring
        self.performance_monitor = PerformanceMonitor() if enable_monitoring else None

        # Controle de execução
        self.active_executions: Dict[str, ScriptExecution] = {}
        self.execution_history: List[ScriptExecution] = []
        self._lock = threading.Lock()

        # Configuração de scripts
        self.script_configs = {
            'analise_coletores.py': {
                'description': 'Análise exploratória completa do dataset',
                'timeout_minutes': 120,
                'requires_analysis': False,
                'generates_analysis': True,
                'critical': True
            },
            'processar_coletores.py': {
                'description': 'Processamento e canonicalização de coletores',
                'timeout_minutes': 240,
                'requires_analysis': True,
                'generates_analysis': False,
                'critical': True
            },
            'gerar_relatorios.py': {
                'description': 'Geração de relatórios com insights',
                'timeout_minutes': 30,
                'requires_analysis': False,
                'generates_analysis': False,
                'critical': False
            },
            'validar_canonicalizacao.py': {
                'description': 'Validação de qualidade dos resultados',
                'timeout_minutes': 60,
                'requires_analysis': False,
                'generates_analysis': False,
                'critical': False
            }
        }

    def execute_script_with_integration(self, script_name: str, args: Dict[str, Any],
                                      integration_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa script com integração completa (monitoramento, validação, etc.)

        Args:
            script_name: Nome do script a executar
            args: Argumentos do script
            integration_config: Configuração de integração (opcional)

        Returns:
            Dict com resultados da execução
        """

        self.logger.info(f"Iniciando execução orquestrada de: {script_name}")

        try:
            # Valida script
            if script_name not in self.script_configs:
                raise ValueError(f"Script não reconhecido: {script_name}")

            script_config = self.script_configs[script_name]

            # Constrói comando
            command = self._build_script_command(script_name, args)

            # Cria execução
            execution = ScriptExecution(
                script_name=script_name,
                command=command,
                status=ScriptStatus.PENDING
            )

            # Registra execução
            with self._lock:
                self.active_executions[script_name] = execution

            # Executa validações pré-execução
            pre_validation = self._run_pre_execution_validation(script_name, args, integration_config)
            if not pre_validation['is_valid']:
                execution.status = ScriptStatus.FAILED
                execution.stderr = '; '.join(pre_validation['errors'])
                return self._create_execution_result(execution, pre_validation)

            # Inicia monitoramento se habilitado
            if self.performance_monitor:
                self.performance_monitor.start_monitoring()
                self.performance_monitor.start_processing_timer()

            # Executa script
            execution_result = self._execute_script(execution, script_config)

            # Para monitoramento
            if self.performance_monitor:
                self.performance_monitor.end_processing_timer()
                self.performance_monitor.stop_monitoring()

            # Executa validações pós-execução
            if execution_result['success']:
                post_validation = self._run_post_execution_validation(
                    script_name, execution_result, integration_config
                )
                execution_result['post_validation'] = post_validation

            # Move para histórico
            with self._lock:
                if script_name in self.active_executions:
                    del self.active_executions[script_name]
                self.execution_history.append(execution)

            return execution_result

        except Exception as e:
            self.logger.error(f"Erro na execução orquestrada de {script_name}: {e}")

            # Limpa execução ativa
            with self._lock:
                if script_name in self.active_executions:
                    self.active_executions[script_name].status = ScriptStatus.FAILED
                    self.active_executions[script_name].stderr = str(e)

            raise

    def _build_script_command(self, script_name: str, args: Dict[str, Any]) -> List[str]:
        """Constrói comando para execução do script"""

        command = [sys.executable, str(Path('src') / script_name)]

        # Adiciona argumentos baseado no script
        if script_name == 'analise_coletores.py':
            if args.get('output_path'):
                command.extend(['--output', args['output_path']])
            if args.get('database_config'):
                command.extend(['--config', args['database_config']])
            if args.get('force_refresh'):
                command.append('--force-refresh')

        elif script_name == 'processar_coletores.py':
            if args.get('analysis_results'):
                command.extend(['--analysis-results', args['analysis_results']])
            if args.get('batch_size'):
                command.extend(['--batch-size', str(args['batch_size'])])
            # Checkpointing globally disabled; do not add enable_checkpoints flag

        elif script_name == 'gerar_relatorios.py':
            if args.get('analysis_results'):
                command.extend(['--analysis-results', args['analysis_results']])
            if args.get('output_dir'):
                command.extend(['--output-dir', args['output_dir']])
            if args.get('include_analysis'):
                command.append('--include-analysis')

        elif script_name == 'validar_canonicalizacao.py':
            if args.get('baseline_analysis'):
                command.extend(['--baseline-analysis', args['baseline_analysis']])
            if args.get('quality_threshold'):
                command.extend(['--threshold', str(args['quality_threshold'])])

        return command

    def _execute_script(self, execution: ScriptExecution, script_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o script com monitoramento"""

        execution.status = ScriptStatus.RUNNING
        execution.start_time = datetime.now()

        try:
            self.logger.info(f"Executando comando: {' '.join(execution.command)}")

            # Timeout em segundos
            timeout_seconds = script_config.get('timeout_minutes', 60) * 60

            # Executa processo
            result = subprocess.run(
                execution.command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=Path.cwd()
            )

            execution.end_time = datetime.now()
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            execution.exit_code = result.returncode
            execution.stdout = result.stdout
            execution.stderr = result.stderr

            if result.returncode == 0:
                execution.status = ScriptStatus.SUCCESS
            else:
                execution.status = ScriptStatus.FAILED

            return self._create_execution_result(execution)

        except subprocess.TimeoutExpired:
            execution.end_time = datetime.now()
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            execution.status = ScriptStatus.TIMEOUT
            execution.stderr = f"Timeout após {script_config.get('timeout_minutes', 60)} minutos"

            return self._create_execution_result(execution)

        except Exception as e:
            execution.end_time = datetime.now()
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            execution.status = ScriptStatus.FAILED
            execution.stderr = str(e)

            return self._create_execution_result(execution)

    def _create_execution_result(self, execution: ScriptExecution,
                                validation_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Cria resultado estruturado da execução"""

        result = {
            'script_name': execution.script_name,
            'status': execution.status.value,
            'success': execution.status == ScriptStatus.SUCCESS,
            'exit_code': execution.exit_code,
            'duration_seconds': execution.duration_seconds,
            'stdout': execution.stdout,
            'stderr': execution.stderr,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'command': execution.command
        }

        # Adiciona dados de validação se disponíveis
        if validation_data:
            result['validation'] = validation_data

        # Adiciona dados de performance se disponível
        if self.performance_monitor:
            try:
                performance_summary = self.performance_monitor.get_performance_summary()
                processing_stats = self.performance_monitor.get_processing_stats()

                result['performance'] = {
                    'system_metrics': performance_summary,
                    'processing_stats': {
                        'total_items': processing_stats.total_items,
                        'successful_items': processing_stats.successful_items,
                        'failed_items': processing_stats.failed_items,
                        'avg_processing_rate': processing_stats.avg_processing_rate,
                        'peak_memory_mb': processing_stats.peak_memory_mb,
                        'peak_cpu_percent': processing_stats.peak_cpu_percent
                    }
                }
            except Exception as e:
                self.logger.warning(f"Erro ao coletar métricas de performance: {e}")

        return result

    def _run_pre_execution_validation(self, script_name: str, args: Dict[str, Any],
                                    integration_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Executa validações antes da execução do script"""

        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        script_config = self.script_configs[script_name]

        # Valida dependência de análise
        if script_config['requires_analysis']:
            analysis_path = args.get('analysis_results')
            if not analysis_path:
                validation['errors'].append("Caminho para resultados de análise é obrigatório")
            elif not Path(analysis_path).exists():
                validation['errors'].append(f"Arquivo de análise não encontrado: {analysis_path}")
            else:
                # Valida integração de análise
                try:
                    analysis_validation = config_integrator.validate_analysis_integration(analysis_path)
                    if not analysis_validation['is_valid']:
                        validation['errors'].extend(analysis_validation['errors'])
                        validation['warnings'].extend(analysis_validation['warnings'])
                except Exception as e:
                    validation['errors'].append(f"Erro ao validar análise: {e}")

        # Valida configuração de integração
        if integration_config:
            pipeline_config = integration_config.get('pipeline_config', {})
            if not pipeline_config:
                validation['warnings'].append("Configuração de pipeline não encontrada")

        # Valida recursos do sistema
        try:
            if self.performance_monitor:
                resource_check = self.performance_monitor.check_resource_limits()
                if resource_check['status'] != 'ok':
                    validation['warnings'].extend(resource_check['warnings'])
        except Exception as e:
            validation['warnings'].append(f"Não foi possível verificar recursos: {e}")

        validation['is_valid'] = len(validation['errors']) == 0

        return validation

    def _run_post_execution_validation(self, script_name: str, execution_result: Dict[str, Any],
                                     integration_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Executa validações após execução do script"""

        validation = {
            'output_validation': True,
            'quality_checks': [],
            'recommendations': []
        }

        try:
            # Validações específicas por script
            if script_name == 'analise_coletores.py' and execution_result['success']:
                # Verifica se arquivo de análise foi gerado
                stdout = execution_result['stdout']
                if 'análise salva em' in stdout or 'analysis saved' in stdout:
                    validation['quality_checks'].append("Arquivo de análise gerado com sucesso")
                else:
                    validation['output_validation'] = False
                    validation['quality_checks'].append("Arquivo de análise pode não ter sido gerado")

            elif script_name == 'processar_coletores.py' and execution_result['success']:
                # Verifica métricas de processamento
                stdout = execution_result['stdout']
                if 'coletores processados' in stdout:
                    validation['quality_checks'].append("Processamento concluído com métricas")

                # Recomendações baseadas em performance
                if 'performance' in execution_result:
                    perf_data = execution_result['performance']
                    if perf_data['processing_stats']['avg_processing_rate'] < 50:
                        validation['recommendations'].append(
                            "Taxa de processamento baixa - considere otimizar batch size"
                        )

        except Exception as e:
            validation['quality_checks'].append(f"Erro na validação pós-execução: {e}")

        return validation

    def get_execution_status(self, script_name: Optional[str] = None) -> Dict[str, Any]:
        """Obtém status atual das execuções"""

        with self._lock:
            if script_name:
                if script_name in self.active_executions:
                    execution = self.active_executions[script_name]
                    return {
                        'script': script_name,
                        'status': execution.status.value,
                        'start_time': execution.start_time.isoformat() if execution.start_time else None,
                        'duration': (datetime.now() - execution.start_time).total_seconds() if execution.start_time else 0
                    }
                else:
                    return {'script': script_name, 'status': 'not_running'}
            else:
                return {
                    'active_executions': {
                        name: {
                            'status': exec.status.value,
                            'start_time': exec.start_time.isoformat() if exec.start_time else None,
                            'duration': (datetime.now() - exec.start_time).total_seconds() if exec.start_time else 0
                        } for name, exec in self.active_executions.items()
                    },
                    'total_active': len(self.active_executions)
                }

    def cancel_execution(self, script_name: str) -> bool:
        """Cancela execução de um script (se possível)"""

        with self._lock:
            if script_name in self.active_executions:
                execution = self.active_executions[script_name]
                if execution.process_id:
                    try:
                        import os
                        import signal
                        os.kill(execution.process_id, signal.SIGTERM)
                        execution.status = ScriptStatus.CANCELLED
                        self.logger.info(f"Execução de {script_name} cancelada")
                        return True
                    except Exception as e:
                        self.logger.error(f"Erro ao cancelar {script_name}: {e}")
                        return False

        return False

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém histórico de execuções"""

        with self._lock:
            recent_executions = self.execution_history[-limit:] if limit else self.execution_history

        return [
            {
                'script_name': exec.script_name,
                'status': exec.status.value,
                'duration_seconds': exec.duration_seconds,
                'start_time': exec.start_time.isoformat() if exec.start_time else None,
                'success': exec.status == ScriptStatus.SUCCESS
            } for exec in reversed(recent_executions)
        ]


# Instância global do orquestrador
script_orchestrator = ScriptOrchestrator()