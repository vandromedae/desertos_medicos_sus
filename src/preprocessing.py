"""
Módulo de pré-processamento para dados de profissionais de saúde e Censo.

Extrai lógica de limpeza e transformação dos notebooks 01 e 02
para funções reutilizáveis.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from src.analysis import classificar_densidade_medica
from src.config import DATA_EXTERNAL


def padronizar_campos_medicos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza campos críticos do DataFrame de médicos.

    Opera sobre: CNES (7 dígitos), município (uppercase), UF (uppercase),
    CNS (string), e cria 'cod_mun_ibge' (6 dígitos) a partir da coluna 'ibge'.

    Args:
        df: DataFrame de médicos (copia interna, original não é modificada)

    Returns:
        DataFrame com campos padronizados
    """
    df = df.copy()

    # 1. Padronizar CNES (7 dígitos, string)
    df["cnes"] = df["cnes"].astype(str).str.strip().str.zfill(7)

    # 2. Padronizar município (uppercase, sem espaços extras)
    df["municipio"] = df["municipio"].astype(str).str.strip().str.upper()

    # 3. Padronizar UF
    df["uf"] = df["uf"].astype(str).str.strip().str.upper()

    # 4. Padronizar CNS (15 dígitos)
    df["profissional_cns"] = df["profissional_cns"].astype(str).str.strip()

    # 5. Criar código de município IBGE (6 dígitos) a partir do IBGE
    # O ElastiCNES tem a coluna 'ibge' com código de 6 dígitos
    if "ibge" in df.columns:
        df["cod_mun_ibge"] = df["ibge"].astype(str).str.strip().str.zfill(6)
    else:
        df["cod_mun_ibge"] = None

    return df


def carregar_censo_sp() -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Carrega shapefile do Censo 2022 (SP) e retorna GeoDataFrame completo
    e DataFrame com colunas selecionadas.

    Colunas selecionadas: CD_SETOR, CD_MUN, NM_MUN, v0001, AREA_KM2
    (apenas as que existirem no shapefile).

    Cria 'cod_mun_ibge' (6 dígitos) a partir de CD_MUN.

    Returns:
        Tupla (gdf_censo, df_censo) com GeoDataFrame completo e DataFrame
        filtrado
    """
    shapefile_path = (
        DATA_EXTERNAL / "SP_setores_CD2022_IBGE" / "SP_setores_CD2022.shp"
    )

    gdf_censo = gpd.read_file(shapefile_path)

    # Selecionar apenas as colunas necessárias para a base municipal
    # v0001 = população total (Censo 2022)
    COLUNAS_CENSO = ["CD_SETOR", "CD_MUN", "NM_MUN", "v0001", "AREA_KM2"]
    cols_existentes = [c for c in COLUNAS_CENSO if c in gdf_censo.columns]
    df_censo = gdf_censo[cols_existentes].copy()

    # Criar código de município de 6 dígitos (IBGE)
    df_censo["cod_mun_ibge"] = df_censo["CD_MUN"].astype(str).str[:6]

    return gdf_censo, df_censo


def agregar_medicos_por_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega médicos por município usando código IBGE.

    Args:
        df: DataFrame de médicos com colunas 'cod_mun_ibge', 'municipio',
            'uf', 'profissional_cns', 'cnes'

    Returns:
        DataFrame com colunas: cod_mun_ibge, municipio, uf, total_medicos,
        total_cnes, total_vinculos
    """
    df_medicos_mun = (
        df
        .groupby(["cod_mun_ibge", "municipio", "uf"])
        .agg(
            total_medicos=("profissional_cns", "nunique"),
            total_cnes=("cnes", "nunique"),
            total_vinculos=("profissional_cns", "count"),
        )
        .reset_index()
    )
    return df_medicos_mun


def cruzar_medicos_populacao(
    df_medicos_mun: pd.DataFrame,
    df_censo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza médicos agregados com população do Censo e calcula densidade.

    Args:
        df_medicos_mun: Saída de agregar_medicos_por_municipio()
        df_censo: Saída de carregar_censo_sp()[1] (DataFrame, não GeoDataFrame)

    Returns:
        DataFrame com colunas: cod_mun_ibge, nm_mun, populacao, area_km2,
        num_setores, total_medicos, total_cnes, medicos_por_1k,
        categoria_densidade, uf
    """
    # 1. Agregar população por município
    df_pop_mun = (
        df_censo
        .groupby(["cod_mun_ibge", "NM_MUN"])
        .agg(
            populacao=("v0001", "sum"),
            area_km2=("AREA_KM2", "sum"),
            num_setores=("CD_SETOR", "count"),
        )
        .reset_index()
        .rename(columns={"NM_MUN": "nm_mun"})
    )

    # 2. Merge (left join para manter todos os municípios do censo)
    df_base = pd.merge(
        df_pop_mun,
        df_medicos_mun[["cod_mun_ibge", "total_medicos", "total_cnes"]],
        on="cod_mun_ibge",
        how="left",
    )

    # Tratar municípios sem médicos
    df_base["total_medicos"] = df_base["total_medicos"].fillna(0).astype(int)
    df_base["total_cnes"] = df_base["total_cnes"].fillna(0).astype(int)

    # 3. Calcular densidade médica (médicos por 1.000 habitantes)
    pop_segura = df_base["populacao"].replace(0, np.nan)
    df_base["medicos_por_1k"] = (df_base["total_medicos"] / pop_segura * 1000).round(2)

    # 4. Classificar densidade
    df_base["categoria_densidade"] = df_base["medicos_por_1k"].apply(
        classificar_densidade_medica
    )

    # 5. Adicionar UF a partir do código IBGE
    if "uf" not in df_base.columns:
        df_base["uf"] = df_base["cod_mun_ibge"].astype(str).str[:2]

    return df_base
