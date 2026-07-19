"""

Funções geoespaciais para manipulação de coordenadas e geometrias.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

from typing import Optional

import geopandas as gpd
import pandas as pd


def parse_location_wkt(location_str: str) -> Optional[tuple[float, float]]:
    """
    Converte string WKT 'POINT (lon lat)' para tupla (lon, lat).
    
    Suporta formatos:
    - WKT: "POINT (-46.6333 -23.5505)"
    - Separado por vírgula: "-46.6333,-23.5505" ou "-23.5505,-46.6333"
    
    Para strings com vírgula, usa heurística de que latitude está entre -90 e 90
    para desambiguar a ordem.
    
    Args:
        location_str: String no formato WKT ou 'lon,lat'
    
    Returns:
        Tupla (longitude, latitude) ou None
    """
    if pd.isna(location_str) or location_str in ("-", ""):
        return None
    
    location_str = str(location_str).strip()
    
    # Formato WKT: POINT (lon lat)
    if "POINT" in location_str:
        location_str = location_str.replace("POINT", "").strip()
        location_str = location_str.replace("(", "").replace(")", "").strip()
        parts = location_str.split()
        if len(parts) >= 2:
            try:
                return (float(parts[0]), float(parts[1]))
            except ValueError:
                return None
    
    # Formato alternativo: "lon,lat" ou "lat,lon"
    if "," in location_str:
        parts = location_str.split(",")
        if len(parts) == 2:
            try:
                val1 = float(parts[0].strip())
                val2 = float(parts[1].strip())
                # Heurística: latitude é sempre entre -90 e 90
                if -90 <= val1 <= 90 and (val2 < -90 or val2 > 90):
                    return (val2, val1)  # (lon, lat)
                elif -90 <= val2 <= 90 and (val1 < -90 or val1 > 90):
                    return (val1, val2)  # (lon, lat)
                else:
                    # Ambos válidos como lat, assumir ordem lon,lat
                    return (val1, val2)
            except ValueError:
                return None
    
    return None


def criar_geodataframe_pontos(
    df: pd.DataFrame,
    coluna_lon: str = "longitude",
    coluna_lat: str = "latitude",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Cria GeoDataFrame a partir de DataFrame com colunas de coordenadas.
    
    Args:
        df: DataFrame com colunas de longitude e latitude
        coluna_lon: Nome da coluna de longitude
        coluna_lat: Nome da coluna de latitude
        crs: Sistema de referência de coordenadas
    
    Returns:
        GeoDataFrame com geometria de pontos
    """
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[coluna_lon], df[coluna_lat]),
        crs=crs,
    )
    return gdf


def associar_pontos_a_setores(
    gdf_pontos: gpd.GeoDataFrame,
    gdf_setores: gpd.GeoDataFrame,
    coluna_setor: str = "cd_setor",
) -> gpd.GeoDataFrame:
    """
    Associa pontos (CNES) aos setores censitários que os contêm.
    
    Args:
        gdf_pontos: GeoDataFrame de pontos (CNES)
        gdf_setores: GeoDataFrame de polígonos (setores censitários)
        coluna_setor: Nome da coluna do código do setor
    
    Returns:
        GeoDataFrame de pontos com coluna do setor associado
    """
    # Spatial join
    resultado = gpd.sjoin(
        gdf_pontos,
        gdf_setores[[coluna_setor, "geometry"]],
        how="left",
        predicate="within",
    )
    
    # Remover coluna de índice duplicada
    if "index_right" in resultado.columns:
        resultado = resultado.drop(columns=["index_right"])
    
    return resultado