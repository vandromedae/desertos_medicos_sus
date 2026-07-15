"""
Módulo de análises estatísticas e de saúde pública.
"""

import pandas as pd

from src.config import CBO_MEDICOS_PREFIX, LIMIAR_DENSIDADE_MEDICA


def filtrar_medicos(df: pd.DataFrame, coluna_cbo: str = "profissional_cbo") -> pd.DataFrame:
    """
    Filtra apenas médicos (CBO 225xxx) de um DataFrame de profissionais.
    
    Args:
        df: DataFrame com coluna CBO
        coluna_cbo: Nome da coluna CBO
    
    Returns:
        DataFrame filtrado apenas com médicos
    """
    df = df.copy()
    df[coluna_cbo] = df[coluna_cbo].astype(str)
    mask = df[coluna_cbo].str.startswith(CBO_MEDICOS_PREFIX)
    return df[mask].copy()


def deduplicar_medicos_por_local(
    df: pd.DataFrame,
    coluna_cns: str = "profissional_cns",
    coluna_cnes: str = "cnes",
) -> pd.DataFrame:
    """
    Deduplica médicos por (CNS, CNES) - um médico por estabelecimento.
    
    Args:
        df: DataFrame de médicos
        coluna_cns: Nome da coluna CNS do profissional
        coluna_cnes: Nome da coluna CNES
    
    Returns:
        DataFrame deduplicado
    """
    return df.drop_duplicates(subset=[coluna_cns, coluna_cnes]).copy()


def calcular_densidade_medica(
    df_medicos: pd.DataFrame,
    df_populacao: pd.DataFrame,
    coluna_mun_medicos: str = "cod_mun_6",
    coluna_mun_pop: str = "cod_mun_6",
    coluna_pop: str = "populacao",
) -> pd.DataFrame:
    """
    Calcula densidade médica (médicos por 1.000 habitantes) por município.
    
    Args:
        df_medicos: DataFrame de médicos com coluna de município
        df_populacao: DataFrame de população por município
        coluna_mun_medicos: Coluna de município em df_medicos
        coluna_mun_pop: Coluna de município em df_populacao
        coluna_pop: Coluna de população
    
    Returns:
        DataFrame com densidade médica por município
    """
    # Agregar médicos por município
    medicos_por_mun = (
        df_medicos
        .groupby(coluna_mun_medicos)
        .agg(total_medicos=("profissional_cns", "nunique"))
        .reset_index()
    )
    
    # Merge com população
    df_base = pd.merge(
        df_populacao[[coluna_mun_pop, coluna_pop]],
        medicos_por_mun,
        left_on=coluna_mun_pop,
        right_on=coluna_mun_medicos,
        how="left",
    )
    
    # Tratar NaN
    df_base["total_medicos"] = df_base["total_medicos"].fillna(0).astype(int)
    
    # Calcular densidade
    pop_segura = df_base[coluna_pop].replace(0, float("nan"))
    df_base["medicos_por_1k"] = (df_base["total_medicos"] / pop_segura * 1000).round(2)
    
    return df_base


def classificar_densidade_medica(valor: float) -> str:
    """Classifica densidade médica em categorias."""
    if pd.isna(valor):
        return "Sem dados"
    if valor < LIMIAR_DENSIDADE_MEDICA["critico"]:
        return "1. Crítico (<1,0)"
    if valor < LIMIAR_DENSIDADE_MEDICA["insuficiente"]:
        return "2. Insuficiente (1-2)"
    if valor < LIMIAR_DENSIDADE_MEDICA["adequado"]:
        return "3. Adequado (2-4)"
    if valor < LIMIAR_DENSIDADE_MEDICA["bom"]:
        return "4. Bom (4-8)"
    return "5. Excelente (≥8)"


def identificar_desertos_medicos(
    df: pd.DataFrame,
    coluna_densidade: str = "medicos_por_1k",
    limiar: float = LIMIAR_DENSIDADE_MEDICA["critico"],
) -> pd.DataFrame:
    """
    Identifica municípios/setores em situação de deserto médico.
    
    Args:
        df: DataFrame com coluna de densidade médica
        coluna_densidade: Nome da coluna de densidade
        limiar: Limiar para considerar deserto médico
    
    Returns:
        DataFrame filtrado com apenas áreas em deserto médico
    """
    return df[df[coluna_densidade] < limiar].copy()