"""
Funções de classificação para mapas bivariados e coropléticos.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import warnings

import pandas as pd


def classificar_acesso_por_tercis(valor, tipo: str = "e2sfca"):
    """
    Classifica acessibilidade em Baixo/Médio/Alto usando tercis.

    .. deprecated:: 4.0
        Use ``classificar_acesso_por_tercis_com_quartis()`` que aceita uma série
        e computa os tercis internamente.

    Args:
        valor: Valor da acessibilidade (índice E2SFCA ou distância em km).
        tipo: "e2sfca" (índice: maior = melhor) ou "distancia" (menor = melhor).

    Returns:
        'Baixo', 'Médio' ou 'Alto'.
    """
    warnings.warn(
        "classificar_acesso_por_tercis() está obsoleta. "
        "Use classificar_acesso_por_tercis_com_quartis().",
        DeprecationWarning,
        stacklevel=2,
    )
    if pd.isna(valor) or valor == 0:
        return 'Baixo'
    return 'Médio'


def classificar_acesso_por_tercis_com_quartis(
    serie: pd.Series, tipo: str = "e2sfca"
) -> pd.Series:
    """
    Classifica acessibilidade em Baixo/Médio/Alto usando tercis de uma série.

    Args:
        serie: Série pandas com valores de acessibilidade.
        tipo: "e2sfca" (índice: maior = melhor) ou "distancia" (menor = melhor).

    Returns:
        Série com categorias 'Baixo', 'Médio', 'Alto'.
    """
    quartis = serie.quantile([0.33, 0.66])

    if tipo == "e2sfca":
        def _classificar(valor):
            if pd.isna(valor) or valor == 0:
                return 'Baixo'
            elif valor < quartis.iloc[0]:
                return 'Baixo'
            elif valor < quartis.iloc[1]:
                return 'Médio'
            else:
                return 'Alto'
    elif tipo == "distancia":
        def _classificar(valor):
            if pd.isna(valor):
                return 'Baixo'
            elif valor < quartis.iloc[0]:
                return 'Alto'
            elif valor < quartis.iloc[1]:
                return 'Médio'
            else:
                return 'Baixo'
    else:
        raise ValueError(f"Tipo desconhecido: {tipo}. Use 'e2sfca' ou 'distancia'.")

    return serie.apply(_classificar)


def classificar_acesso_por_categoria(categoria) -> str:
    """
    Classifica acesso E2SFCA em Alto/Médio/Baixo a partir da categoria de texto.

    Usado no MAPA 4 (bivariado setorial) onde a coluna 'categoria_acesso'
    contém strings como "Excelente", "Bom", "Moderado", "Limitado", "Crítico", "Deserto".

    Args:
        categoria: String com a categoria E2SFCA.

    Returns:
        'Alto', 'Médio' ou 'Baixo'.
    """
    if pd.isna(categoria):
        return 'Baixo'

    cat_str = str(categoria).strip()

    if 'Excelente' in cat_str or 'Bom' in cat_str:
        return 'Alto'
    elif 'Moderado' in cat_str:
        return 'Médio'
    else:
        return 'Baixo'


def classificar_densidade_bivariada(valor, quartis: pd.Series) -> str:
    """
    Classifica densidade em Baixa/Média/Alta usando tercis pré-computados.

    Args:
        valor: Valor da densidade.
        quartis: Série com os valores dos tercis (índices 0.33 e 0.66).

    Returns:
        'Baixa', 'Média' ou 'Alta'.
    """
    if pd.isna(valor) or valor == 0:
        return 'Baixa'
    elif valor < quartis.iloc[0]:
        return 'Baixa'
    elif valor < quartis.iloc[1]:
        return 'Média'
    else:
        return 'Alta'
