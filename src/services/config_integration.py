"""
Configuration Integration Service

Integra resultados de análise com configuração de processamento,
conectando descoberta de padrões com pipeline de canonicalização.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .pattern_discovery import PatternDiscoveryService
from .analysis_persistence import AnalysisPersistenceService


class ConfigurationIntegrator:
    """
    Integrador de configuração que conecta análise com processamento
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pattern_discovery = PatternDiscoveryService()
        self.analysis_persistence = AnalysisPersistenceService()

    def generate_processing_config_from_analysis(self, analysis_results_path: str) -> Dict[str, Any]:
        """
        Gera configuração de processamento a partir dos resultados da análise

        Args:
            analysis_results_path: Caminho para resultados da análise completa

        Returns:
            Dict com configuração otimizada para processamento
        """

        self.logger.info(f"Gerando configuração de processamento a partir de: {analysis_results_path}")

        try:
            analysis_path = Path(analysis_results_path)

            # Carrega resultados da análise
            analysis_data = self.analysis_persistence.load_analysis_results(analysis_results_path)

            # Descobre padrões
            pattern_results = self.pattern_discovery.analyze_complete_dataset_results(analysis_path)

            # Gera configuração de processamento
            processing_config = self.pattern_discovery.generate_processing_configuration(pattern_results)

            # Adiciona metadados de integração
            processing_config['integration_metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'source_analysis': analysis_results_path,
                'pattern_discovery_version': '1.0.0',
                'config_generator': 'ConfigurationIntegrator',
                'total_patterns_discovered': len(pattern_results.get('discovered_patterns', [])),
                'total_recommendations': len(pattern_results.get('threshold_recommendations', []))
            }

            self.logger.info(f"Configuração gerada com sucesso: {len(pattern_results.get('discovered_patterns', []))} padrões descobertos")

            return processing_config

        except Exception as e:
            self.logger.error(f"Erro ao gerar configuração de processamento: {e}")
            raise

    def validate_analysis_integration(self, analysis_results_path: str) -> Dict[str, Any]:
        """
        Valida se a integração entre análise e processamento está correta

        Args:
            analysis_results_path: Caminho para resultados da análise

        Returns:
            Dict com status de validação
        """

        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }

        try:
            analysis_path = Path(analysis_results_path)

            # Verifica se arquivo existe
            if not analysis_path.exists():
                validation_result['errors'].append(f"Arquivo de análise não encontrado: {analysis_results_path}")
                return validation_result

            # Carrega e valida estrutura dos dados
            try:
                analysis_data = self.analysis_persistence.load_analysis_results(analysis_results_path)

                # Verifica campos obrigatórios
                required_fields = ['total_records', 'collector_analysis', 'pattern_analysis']
                missing_fields = [field for field in required_fields if field not in analysis_data]

                if missing_fields:
                    validation_result['errors'].extend([
                        f"Campo obrigatório ausente: {field}" for field in missing_fields
                    ])

                # Verifica qualidade dos dados
                if 'total_records' in analysis_data:
                    total_records = analysis_data['total_records']
                    if total_records < 1000:
                        validation_result['warnings'].append(
                            f"Dataset pequeno ({total_records} registros) pode gerar padrões menos confiáveis"
                        )
                    elif total_records > 10000000:
                        validation_result['recommendations'].append(
                            "Dataset grande detectado - considere usar processamento em paralelo"
                        )

                # Verifica análise de coletores
                if 'collector_analysis' in analysis_data:
                    collector_data = analysis_data['collector_analysis']
                    if 'unique_collectors' in collector_data:
                        unique_count = collector_data['unique_collectors']
                        if unique_count < 100:
                            validation_result['warnings'].append(
                                f"Poucos coletores únicos ({unique_count}) - verificar qualidade dos dados"
                            )

                # Verifica análise de padrões
                if 'pattern_analysis' in analysis_data:
                    pattern_data = analysis_data['pattern_analysis']
                    if 'separator_patterns' in pattern_data:
                        separators = pattern_data['separator_patterns']
                        if len(separators) < 3:
                            validation_result['warnings'].append(
                                "Poucos padrões de separadores encontrados - pode afetar atomização"
                            )

            except json.JSONDecodeError as e:
                validation_result['errors'].append(f"Erro ao decodificar JSON: {e}")
                return validation_result

            except Exception as e:
                validation_result['errors'].append(f"Erro ao validar dados de análise: {e}")
                return validation_result

            # Se chegou até aqui sem erros críticos, é válido
            if not validation_result['errors']:
                validation_result['is_valid'] = True

            # Recomendações gerais
            validation_result['recommendations'].extend([
                "Execute descoberta de padrões para otimizar configuração",
                "Monitore performance durante processamento",
                "Valide qualidade dos resultados após canonicalização"
            ])

        except Exception as e:
            validation_result['errors'].append(f"Erro de validação: {e}")

        return validation_result

    def create_pipeline_integration_config(self, analysis_results_path: str,
                                         custom_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Cria configuração completa de integração para o pipeline

        Args:
            analysis_results_path: Caminho para resultados da análise
            custom_overrides: Substituições personalizadas (opcional)

        Returns:
            Dict com configuração completa de integração
        """

        self.logger.info("Criando configuração de integração do pipeline")

        try:
            # Gera configuração base
            base_config = self.generate_processing_config_from_analysis(analysis_results_path)

            # Valida integração
            validation = self.validate_analysis_integration(analysis_results_path)

            # Configuração completa de integração
            integration_config = {
                'pipeline_config': base_config,
                'validation_results': validation,
                'execution_order': {
                    'stage_sequence': ['analysis', 'processing', 'reports', 'validation'],
                    'stage_dependencies': {
                        'processing': ['analysis'],
                        'reports': ['processing'],
                        'validation': ['processing']
                    },
                    'parallel_execution': {
                        'reports': ['validation']  # Podem executar em paralelo
                    }
                },
                'integration_hooks': {
                    'pre_processing': [
                        'validate_analysis_results',
                        'load_discovered_patterns',
                        'configure_dynamic_thresholds'
                    ],
                    'post_processing': [
                        'persist_results',
                        'generate_quality_metrics',
                        'update_baseline'
                    ]
                },
                'monitoring_config': {
                    'enable_performance_monitoring': True,
                    'enable_progress_tracking': True,
                    'enable_resource_monitoring': True,
                    'checkpoint_frequency': base_config.get('processing_parameters', {}).get('checkpoint_frequency', 10000)
                }
            }

            # Aplica substituições personalizadas
            if custom_overrides:
                integration_config = self._apply_config_overrides(integration_config, custom_overrides)

            self.logger.info("Configuração de integração criada com sucesso")

            return integration_config

        except Exception as e:
            self.logger.error(f"Erro ao criar configuração de integração: {e}")
            raise

    def _apply_config_overrides(self, base_config: Dict[str, Any],
                               overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica substituições personalizadas na configuração

        Args:
            base_config: Configuração base
            overrides: Substituições a aplicar

        Returns:
            Dict com configuração atualizada
        """

        import copy
        updated_config = copy.deepcopy(base_config)

        def _update_nested_dict(target: Dict[str, Any], updates: Dict[str, Any]):
            for key, value in updates.items():
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    _update_nested_dict(target[key], value)
                else:
                    target[key] = value

        _update_nested_dict(updated_config, overrides)

        return updated_config

    def save_integration_config(self, config: Dict[str, Any], output_path: str):
        """
        Salva configuração de integração em arquivo

        Args:
            config: Configuração de integração
            output_path: Caminho para salvar arquivo
        """

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Configuração de integração salva em: {output_path}")

        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")
            raise

    def load_integration_config(self, config_path: str) -> Dict[str, Any]:
        """
        Carrega configuração de integração de arquivo

        Args:
            config_path: Caminho do arquivo de configuração

        Returns:
            Dict com configuração carregada
        """

        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.logger.info(f"Configuração de integração carregada de: {config_path}")
            return config

        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")
            raise


# Instância global do integrador
config_integrator = ConfigurationIntegrator()