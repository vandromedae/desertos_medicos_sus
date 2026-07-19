"""
Pacote de visualização e geração de mapas interativos.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

Submódulos:
  - helpers: Funções auxiliares de UI (mapa base, título, legenda)
  - circle_maps: Mapas com CircleMarker (densidade populacional, CNES, densidade médica)
  - choropleth: Mapas coropléticos municipais (MAPA 1, MAPA 3)
  - per_municipality: Mapas por município (MAPA 2, MAPA 4)
  - classifiers: Funções de classificação para mapas bivariados
  - index: Geração de páginas índice HTML

"""

from src.visualization.circle_maps import (
    mapa_densidade_populacional,
    mapa_cnes_setores,
    mapa_densidade_medica_setorial,
)
from src.visualization.choropleth import (
    mapa_densidade_municipal,
    mapa_bivariado_municipal,
)
from src.visualization.per_municipality import (
    mapa_densidade_setorial_por_municipio,
    mapa_bivariado_setorial_por_municipio,
)
from src.visualization.classifiers import (
    classificar_acesso_por_tercis,
    classificar_acesso_por_tercis_com_quartis,
    classificar_acesso_por_categoria,
    classificar_densidade_bivariada,
)
from src.visualization.index import gerar_indice_mapas

__all__ = [
    "mapa_densidade_populacional",
    "mapa_cnes_setores",
    "mapa_densidade_medica_setorial",
    "mapa_densidade_municipal",
    "mapa_bivariado_municipal",
    "mapa_densidade_setorial_por_municipio",
    "mapa_bivariado_setorial_por_municipio",
    "classificar_acesso_por_tercis",
    "classificar_acesso_por_tercis_com_quartis",
    "classificar_acesso_por_categoria",
    "classificar_densidade_bivariada",
    "gerar_indice_mapas",
]
