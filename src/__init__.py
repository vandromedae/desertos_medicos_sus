"""
Pacote de código reutilizável do projeto Desertos Médicos SUS.
Expõe as principais funções de configuração, carregamento de dados,
análise e visualização para uso nos notebooks e scripts.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

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
from src.analysis import identificar_desertos_medicos
from src.visualization import (
    mapa_densidade_populacional,
    mapa_cnes_setores,
    mapa_densidade_medica_setorial,
)

__all__ = [
    "ElasticnesDownloader",
    "identificar_desertos_medicos",
    "mapa_densidade_populacional",
    "mapa_cnes_setores",
    "mapa_densidade_medica_setorial",
]