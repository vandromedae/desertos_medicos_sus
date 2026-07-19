"""
Mapas coropléticos municipais: MAPA 1 (densidade médica) e MAPA 3 (bivariado).

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

Extraído do notebook 04_visualizacao_e_insights.ipynb.
"""

from pathlib import Path
from typing import Optional

import folium
import geopandas as gpd
import numpy as np
import pandas as pd

from src.visualization.helpers import adicionar_metadados, adicionar_titulo, adicionar_legenda


def mapa_densidade_municipal(
    gdf_municipios: gpd.GeoDataFrame,
    df_municipal: pd.DataFrame,
    col_densidade: str = "medicos_por_1k",
    col_nm_mun: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> folium.Map:
    """
    MAPA 1: Gera mapa coroplético estadual de densidade médica por município.

    Classificação por limiar fixo: Crítico (<1), Insuficiente (1-2),
    Adequado (2-4), Bom (4-8), Excelente (≥8).

    Args:
        gdf_municipios: GeoDataFrame de municípios (shapefile)
        df_municipal: DataFrame municipal com dados de densidade
        col_densidade: Coluna de densidade médica (médicos/1k hab)
        col_nm_mun: Coluna de nome do município (auto-detect se None)
        output_path: Caminho para salvar o HTML

    Returns:
        Objeto folium.Map
    """
    if col_nm_mun is None:
        colunas = df_municipal.columns.tolist()
        col_nm_mun = next(
            (c for c in colunas if c in ['nm_mun', 'nome_mun', 'municipio']),
            None
        )

    col_cod_mun = next(
        (c for c in df_municipal.columns if c in ['cod_mun_6', 'cod_mun_ibge', 'cd_mun_6', 'cod_mun']),
        None
    )

    if col_cod_mun and col_cod_mun != 'cod_mun_6':
        df_municipal = df_municipal.copy()
        df_municipal['cod_mun_6'] = df_municipal[col_cod_mun].astype(str).str[:6]
    elif not col_cod_mun:
        if 'cd_mun' in df_municipal.columns:
            df_municipal = df_municipal.copy()
            df_municipal['cod_mun_6'] = df_municipal['cd_mun'].astype(str).str[:6]
        else:
            raise ValueError("Não foi possível identificar coluna de código de município!")

    cols_para_merge = ['cod_mun_6']
    if col_nm_mun:
        cols_para_merge.append(col_nm_mun)
    cols_para_merge.append(col_densidade)

    for extra_col in ['populacao', 'total_medicos']:
        if extra_col in df_municipal.columns:
            cols_para_merge.append(extra_col)

    gdf_mapa_mun = gdf_municipios.merge(
        df_municipal[cols_para_merge],
        on='cod_mun_6',
        how='left'
    )

    gdf_mapa_mun[col_densidade] = gdf_mapa_mun[col_densidade].fillna(0)

    def classificar_densidade(valor):
        if valor < 1.0:
            return '1. Crítico (<1,0)'
        elif valor < 2.0:
            return '2. Insuficiente (1-2)'
        elif valor < 4.0:
            return '3. Adequado (2-4)'
        elif valor < 8.0:
            return '4. Bom (4-8)'
        else:
            return '5. Excelente (≥8)'

    gdf_mapa_mun['categoria'] = gdf_mapa_mun[col_densidade].apply(classificar_densidade)

    cores_categorias = {
        '1. Crítico (<1,0)':     '#ffeda0',
        '2. Insuficiente (1-2)': '#feb24c',
        '3. Adequado (2-4)':     '#fd8d3c',
        '4. Bom (4-8)':          '#fc4e2a',
        '5. Excelente (≥8)':     '#bd0026',
    }

    centro_sp = [-22.19, -48.71]
    m = folium.Map(location=centro_sp, zoom_start=7, tiles='CartoDB positron')
    adicionar_metadados(m, "MAPA 1: Densidade Médica Municipal - São Paulo")

    for categoria, cor in cores_categorias.items():
        gdf_cat = gdf_mapa_mun[gdf_mapa_mun['categoria'] == categoria].copy()

        if len(gdf_cat) > 0:
            geo_json = gdf_cat.to_json()

            folium.GeoJson(
                geo_json,
                name=categoria,
                style_function=lambda feature, cor=cor: {
                    'fillColor': cor,
                    'color': 'white',
                    'weight': 0.8,
                    'fillOpacity': 0.65,
                },
                highlight_function=lambda feature: {
                    'weight': 2.5,
                    'color': '#333',
                    'fillOpacity': 0.85
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[col_nm_mun, 'populacao', 'total_medicos', col_densidade],
                    aliases=['🏙️ Município:', ' População:', '🩺 Médicos SUS:', '📊 Densidade (por 1k hab):'],
                    style=('background-color: white; color: #333333; font-family: arial; '
                           'font-size: 12px; padding: 10px; border-radius: 5px;'),
                    localize=True,
                    sticky=True
                )
            ).add_to(m)

    legenda_html = '''
    <div style="position: fixed;
                bottom: 30px; left: 30px;
                width: 260px;
                background-color: rgba(255,255,255,0.95);
                border: 2px solid #333;
                border-radius: 8px;
                padding: 14px;
                font-size: 13px;
                z-index: 9999;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);">
        <b style="font-size:14px;">🩺 Densidade Médica SUS</b><br>
        <small>(médicos por 1.000 hab)</small><br>
        <small style="color:#666;">Mais escuro = mais médicos</small><br><br>
        <i style="background:#bd0026;width:18px;height:18px;float:left;margin-right:8px;opacity:0.8;border-radius:3px;"></i>
        Excelente (≥8)<br>
        <i style="background:#fc4e2a;width:18px;height:18px;float:left;margin-right:8px;opacity:0.8;border-radius:3px;"></i>
        Bom (4-8)<br>
        <i style="background:#fd8d3c;width:18px;height:18px;float:left;margin-right:8px;opacity:0.8;border-radius:3px;"></i>
        Adequado (2-4)<br>
        <i style="background:#feb24c;width:18px;height:18px;float:left;margin-right:8px;opacity:0.8;border-radius:3px;"></i>
        Insuficiente (1-2)<br>
        <i style="background:#ffeda0;width:18px;height:18px;float:left;margin-right:8px;opacity:0.8;border-radius:3px;"></i>
        Crítico (&lt;1,0)
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legenda_html))

    titulo_html = '''
    <div style="position: fixed;
                top: 10px; left: 50%;
                transform: translateX(-50%);
                background-color: rgba(255,255,255,0.95);
                border: 2px solid #333;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                z-index: 9999;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);">
         Densidade Médica SUS - Estado de São Paulo
    </div>
    '''
    m.get_root().html.add_child(folium.Element(titulo_html))

    folium.LayerControl(collapsed=False).add_to(m)

    if output_path:
        m.save(output_path)

    return m


def mapa_bivariado_municipal(
    gdf_municipios: gpd.GeoDataFrame,
    df_comparacao: pd.DataFrame,
    col_densidade: str = "medicos_por_1k",
    col_acesso: str = "acessibilidade_e2sfca_mediana",
    col_nm_mun: str = "nm_mun",
    output_path: Optional[Path] = None,
) -> folium.Map:
    """
    MAPA 3: Gera mapa bivariado estadual (densidade médica × acessibilidade E2SFCA).

    Classificação 3×3 por tercis: Densidade (Baixa/Média/Alta) × Acesso (Baixo/Médio/Alto).

    Args:
        gdf_municipios: GeoDataFrame de municípios (shapefile)
        df_comparacao: DataFrame com colunas de densidade e acessibilidade
        col_densidade: Coluna de densidade médica
        col_acesso: Coluna de acessibilidade E2SFCA
        col_nm_mun: Coluna de nome do município
        output_path: Caminho para salvar o HTML

    Returns:
        Objeto folium.Map
    """
    from src.visualization.classifiers import (
        classificar_densidade_bivariada,
        classificar_acesso_por_tercis_com_quartis,
    )

    df_bivariado = df_comparacao.copy()
    df_bivariado['cod_mun_6'] = df_bivariado['cod_mun_ibge'].astype(str).str[:6]

    usar_distancia = False
    if col_acesso not in df_bivariado.columns:
        col_acesso = 'dist_mediana_km'
        usar_distancia = True

    densidade_quartis = df_bivariado[col_densidade].quantile([0.33, 0.66])
    df_bivariado['cat_densidade'] = df_bivariado[col_densidade].apply(
        lambda v: classificar_densidade_bivariada(v, densidade_quartis)
    )

    if not usar_distancia:
        acesso_quartis = df_bivariado[col_acesso].quantile([0.33, 0.66])
        df_bivariado['cat_acesso'] = classificar_acesso_por_tercis_com_quartis(
            df_bivariado[col_acesso], tipo="e2sfca"
        )
        alias_acesso = ' Índice E2SFCA mediano:'
    else:
        df_bivariado['cat_acesso'] = classificar_acesso_por_tercis_com_quartis(
            df_bivariado[col_acesso], tipo="distancia"
        )
        alias_acesso = ' Dist. mediana ao médico (km):'

    df_bivariado['categoria_bivariada'] = (
        df_bivariado['cat_densidade'] + ' + ' + df_bivariado['cat_acesso']
    )

    gdf_bivariado = gdf_municipios.merge(
        df_bivariado[['cod_mun_6', 'categoria_bivariada', 'cat_densidade',
                      'cat_acesso', col_densidade, col_acesso, col_nm_mun]],
        on='cod_mun_6',
        how='left'
    )
    gdf_bivariado['categoria_bivariada'] = gdf_bivariado['categoria_bivariada'].fillna('Sem dados')

    paleta_bivariada = {
        'Alta + Baixo':  '#800026',
        'Alta + Médio':  '#fc4e2a',
        'Alta + Alto':   '#41ab5d',
        'Média + Baixo': '#e34a33',
        'Média + Médio': '#fed976',
        'Média + Alto':  '#a1d99b',
        'Baixa + Baixo': '#969696',
        'Baixa + Médio': '#d9d9d9',
        'Baixa + Alto':  '#c6dbef',
        'Sem dados':     '#f0f0f0',
    }

    centro_sp = [-22.19, -48.71]
    m = folium.Map(location=centro_sp, zoom_start=7, tiles='CartoDB positron')
    adicionar_metadados(m, "MAPA 3: Densidade Médica x Acessibilidade (E2SFCA) - São Paulo")

    def style_function(feature):
        categoria = feature['properties'].get('categoria_bivariada', 'Sem dados')
        cor = paleta_bivariada.get(categoria, '#f0f0f0')
        return {
            'fillColor': cor,
            'color': 'white',
            'weight': 0.8,
            'fillOpacity': 0.75,
        }

    folium.GeoJson(
        gdf_bivariado,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[col_nm_mun, col_densidade, col_acesso, 'cat_densidade', 'cat_acesso'],
            aliases=['🏙️ Município:', '🩺 Densidade (méd/1k hab):',
                     alias_acesso,
                     '📈 Densidade:', '🏥 Acesso:'],
            style='background-color: white; color: #333; font-family: arial; font-size: 12px; padding: 10px; border-radius: 5px;',
            localize=True
        ),
        highlight_function=lambda feature: {
            'fillOpacity': 0.95,
            'weight': 2.5,
            'color': '#000000'
        }
    ).add_to(m)

    legenda_html = '''
    <div style="position: fixed;
                bottom: 30px; left: 30px;
                width: 340px;
                background-color: rgba(255,255,255,0.98);
                border: 2px solid #333;
                border-radius: 8px;
                padding: 15px;
                font-size: 11px;
                z-index: 9999;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);">
        <b style="font-size:13px;"> Mapa Bivariado: Densidade Médica x Acessibilidade (E2SFCA)</b><br>
        <small style="color:#666;">Nível municipal | Identificação de desertos médicos</small><br><br>

        <table style="width:100%; border-collapse: collapse;">
            <tr>
                <td style="padding:2px;"></td>
                <td style="text-align:center; font-weight:bold; padding:2px;">Baixo Acesso<br><small>(índice baixo)</small></td>
                <td style="text-align:center; font-weight:bold; padding:2px;">Médio Acesso</td>
                <td style="text-align:center; font-weight:bold; padding:2px;">Alto Acesso<br><small>(índice alto)</small></td>
            </tr>
            <tr>
                <td style="font-weight:bold; padding:2px;">Alta Densidade<br><small>(médicos/1k)</small></td>
                <td style="background:#800026; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#fc4e2a; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#41ab5d; width:70px; height:35px; border:1px solid #333;"></td>
            </tr>
            <tr>
                <td style="font-weight:bold; padding:2px;">Média Densidade</td>
                <td style="background:#e34a33; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#fed976; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#a1d99b; width:70px; height:35px; border:1px solid #333;"></td>
            </tr>
            <tr>
                <td style="font-weight:bold; padding:2px;">Baixa Densidade</td>
                <td style="background:#969696; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#d9d9d9; width:70px; height:35px; border:1px solid #333;"></td>
                <td style="background:#c6dbef; width:70px; height:35px; border:1px solid #333;"></td>
            </tr>
        </table>

        <br>
        <small>
            <b>🔴 Vermelho escuro</b> = CRÍTICO (desigualdade: médicos no município, mas acesso real baixo)<br>
            <b>⚫ Cinza escuro</b> = DESERTO RURAL (poucos médicos E acesso ruim)<br>
            <b>🟢 Verde</b> = BOM (bom acesso a médicos)<br>
            <small style="color:#888;">(Cores cinzas representam municípios de baixa densidade populacional)</small>
        </small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legenda_html))

    titulo_html = '''
    <div style="position: fixed;
                top: 10px; left: 50%;
                transform: translateX(-50%);
                background-color: rgba(255,255,255,0.95);
                border: 2px solid #333;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                z-index: 9999;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);">
         Desertos Médicos em SP: Densidade x Acessibilidade (Municipal - E2SFCA)
    </div>
    '''
    m.get_root().html.add_child(folium.Element(titulo_html))

    if output_path:
        m.save(output_path)

    return m
