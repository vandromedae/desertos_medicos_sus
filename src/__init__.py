"""
desertos_medicos_sus.src - Pacote de código reutilizável.

Módulos:
    - config: Constantes e caminhos do projeto
    - data_loader: Download e carregamento de dados
    - geospatial: Funções geoespaciais
    - analysis: Análises estatísticas e de saúde
    - visualization: Geração de mapas e visualizações
"""

from src.config import (
    PROJECT_ROOT,
    DATA_RAW,
    DATA_PROCESSED,
    DATA_EXTERNAL,
    OUTPUT_MAPAS,
    OUTPUT_RELATORIOS,
)
from src.data_loader import ElasticnesDownloader
from src.analysis import calcular_densidade_medica, identificar_desertos_medicos
from src.visualization import (
    mapa_densidade_populacional,
    mapa_cnes_setores,
    mapa_densidade_medica_setorial,
)

__all__ = [
    "ElasticnesDownloader",
    "calcular_densidade_medica",
    "identificar_desertos_medicos",
    "mapa_densidade_populacional",
    "mapa_cnes_setores",
    "mapa_densidade_medica_setorial",
]