"""
Mapas por município: MAPA 2 (densidade setorial) e MAPA 4 (bivariado setorial).

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

Extraído do notebook 04_visualizacao_e_insights.ipynb.
"""

from pathlib import Path
from typing import Optional

import folium
import geopandas as gpd
import jenkspy
import pandas as pd

from src.config import OUTPUT_MAPAS
from src.visualization.helpers import adicionar_metadados
from src.visualization.index import gerar_indice_mapas


PALETA_DENSIDADE_SETORIAL = {
    '1. Baixa':  '#ffffb2',
    '2. Média-Baixa':  '#fecc5c',
    '3. Média':   '#fd8d3c',
    '4. Alta':   '#f03b20',
    '5. Muito Alta': '#800026',
}

PALETA_BIVARIADA_SETORIAL = {
    'Alta + Baixo':  '#800026',
    'Alta + Médio':  '#e34a33',
    'Alta + Alto':   '#41ab5d',
    'Média + Baixo': '#fb6a4a',
    'Média + Médio': '#fed976',
    'Média + Alto':  '#a1d99b',
    'Baixa + Baixo': '#969696',
    'Baixa + Médio': '#d9d9d9',
    'Baixa + Alto':  '#c6dbef',
    'Irrelevante':   '#f0f0f0',
    'Sem dados':     '#ffffff',
}

FILL_OPACITY_SETORES = 0.85
LINHAS_OPACITY = 0.40
PADDING_FIT_BOUNDS = [5, 5]


def _classificar_jenks(valores, n_classes=5):
    """Classifica valores usando Jenks Natural Breaks sobre log10(densidade+1).

    Aplica transformação log10 para comprimir a cauda extrema da distribuição
    de densidade, depois converte os breaks de volta para a escala original.

    Retorna (categorias, breaks) onde categorias é uma Series com as classes
    e breaks é a lista de limites de corte na escala original (hab/km²).
    """
    import numpy as np

    valores_series = pd.Series(valores)
    valores_validos = valores_series[(valores_series > 0) & (~valores_series.isna())]

    n_unicos = len(valores_validos.unique())
    if n_unicos < n_classes:
        n_classes = max(1, n_unicos)
    if n_classes < 2:
        return pd.Series(['1. Baixa'] * len(valores)), [0, float('inf')]

    # Transformação log10 para comprimir cauda extrema
    log_vals = np.log10(valores_validos.values + 1)
    log_breaks = jenkspy.jenks_breaks(log_vals.tolist(), n_classes=n_classes)

    # Converter breaks de volta para escala original
    breaks = [round(10**b - 1, 2) for b in log_breaks]

    breaks_unicos = sorted(set(breaks))
    if len(breaks_unicos) < len(breaks):
        breaks = breaks_unicos
        n_classes = len(breaks) - 1

    categorias = pd.cut(
        valores_series,
        bins=breaks,
        labels=list(PALETA_DENSIDADE_SETORIAL.keys())[:n_classes],
        include_lowest=True,
        right=True,
        duplicates='drop',
    )
    categorias = categorias.astype(str).replace('nan', '1. Baixa')
    return categorias, breaks


def _gerar_legenda_densidade(breaks):
    """Gera HTML de legenda para densidade setorial com limiares Jenks."""
    n_classes = len(breaks) - 1
    cores = list(PALETA_DENSIDADE_SETORIAL.values())[:n_classes]
    rótulos = list(PALETA_DENSIDADE_SETORIAL.keys())[:n_classes]

    itens = ""
    for i in range(n_classes):
        inferior = f"{breaks[i]:,.0f}".replace(",", ".")
        superior = f"{breaks[i+1]:,.0f}".replace(",", ".")
        itens += f'<span style="color:{cores[i]}">■</span> {inferior} - {superior} hab/km²<br>\n'

    return f'''
    <div style="position: fixed; bottom: 10px; left: 10px; background: rgba(255,255,255,0.95);
                padding: 12px; border: 2px solid #333; border-radius: 6px; font-size: 11px; z-index: 1000;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <b style="font-size:13px;">📊 Densidade Populacional</b><br>
        <small>(habitantes por km² — Jenks Natural Breaks)</small><br><br>
        {itens}
    </div>
    '''


def _gerar_legenda_bivariada():
    """Gera HTML de legenda para o mapa bivariado setorial."""
    itens = ""
    for categoria, cor in PALETA_BIVARIADA_SETORIAL.items():
        if categoria in ('Irrelevante', 'Sem dados'):
            continue
        itens += f'<span style="color:{cor}">■</span> {categoria}<br>\n'

    return f'''
    <div style="position: fixed; bottom: 10px; left: 10px; background: rgba(255,255,255,0.95);
                padding: 12px; border: 2px solid #333; border-radius: 6px; font-size: 11px; z-index: 1000;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3); width: 220px;">
        <b style="font-size:13px;">🏥 Acesso a Médicos</b><br>
        <small>(Densidade Pop × Acesso E2SFCA)</small><br><br>
        {itens}
    </div>
    '''


def _calcular_zoom(bounds):
    """Calcula zoom inicial baseado no bounding box."""
    lat_diff = abs(bounds[3] - bounds[1])
    lon_diff = abs(bounds[2] - bounds[0])
    tamanho_mun = max(lat_diff, lon_diff)

    if tamanho_mun > 0.5:
        return 11
    elif tamanho_mun > 0.2:
        return 12
    elif tamanho_mun > 0.05:
        return 13
    return 14


def _preparar_dados_setores(df_setores, gdf_setores_geo, colunas_extra=None):
    """
    Prepara dados mergeando shapefile de setores com dados processados.

    Retorna (gdf_mapa_setores, col_nm_mun).
    """
    colunas_df = df_setores.columns.tolist()
    col_pop_df = next(
        (c for c in colunas_df if c.lower() in ['v0001', 'populacao', 'população']),
        None
    )

    cols_para_merge = ['CD_SETOR']
    for extra in (colunas_extra or []):
        if extra in df_setores.columns:
            cols_para_merge.append(extra)
    if col_pop_df:
        cols_para_merge.append(col_pop_df)

    n_linhas_antes = len(gdf_setores_geo)

    gdf_mapa_setores = gdf_setores_geo.merge(
        df_setores[cols_para_merge],
        on='CD_SETOR',
        how='left',
        suffixes=('', '_dados')
    )

    if len(gdf_mapa_setores) != n_linhas_antes:
        print(f"    ATENÇÃO: merge alterou contagem de linhas ({n_linhas_antes:,} → {len(gdf_mapa_setores):,})")

    cols_para_remover = [c for c in gdf_mapa_setores.columns if c.endswith('_dados')]
    if cols_para_remover:
        gdf_mapa_setores = gdf_mapa_setores.drop(columns=cols_para_remover)

    if col_pop_df and col_pop_df != 'v0001':
        gdf_mapa_setores = gdf_mapa_setores.rename(columns={col_pop_df: 'v0001'})

    colunas = gdf_mapa_setores.columns.tolist()
    col_nm_mun = next((c for c in colunas if c == 'NM_MUN' or c.startswith('NM_MUN')), None)

    if 'v0001' not in gdf_mapa_setores.columns:
        gdf_mapa_setores['v0001'] = 0
    else:
        gdf_mapa_setores['v0001'] = gdf_mapa_setores['v0001'].fillna(0).astype(int)

    gdf_mapa_setores['area_final_km2'] = gdf_mapa_setores['AREA_KM2'].fillna(0.001)
    gdf_mapa_setores.loc[gdf_mapa_setores['area_final_km2'] < 0.001, 'area_final_km2'] = 0.001

    gdf_mapa_setores['densidade_pop'] = (
        gdf_mapa_setores['v0001'] / gdf_mapa_setores['area_final_km2']
    ).round(2)

    return gdf_mapa_setores, col_nm_mun


def _gerar_mapa_setor_municipio(
    gdf_mun,
    col_nm_mun,
    municipio,
    paleta,
    tooltip_fields,
    tooltip_aliases,
    output_path,
    titulo_prefixo="Densidade Populacional",
    legenda_html=None,
):
    """Gera um mapa Folium para um único município (setores com polígonos)."""
    bounds = gdf_mun.total_bounds
    centro_lat = (bounds[1] + bounds[3]) / 2
    centro_lon = (bounds[0] + bounds[2]) / 2
    zoom = _calcular_zoom(bounds)

    m = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=zoom,
        tiles='CartoDB voyager no labels'
    )
    adicionar_metadados(m, f"{titulo_prefixo} - {municipio}")
    folium.map.CustomPane("linhas_base_topo", z_index=640).add_to(m)
    folium.map.CustomPane("labels_topo", z_index=650).add_to(m)

    def style_function(feature):
        props = feature['properties']
        categoria = props.get('categoria_bivariada',
                    props.get('categoria_densidade', ''))
        cor = paleta.get(categoria, '#f0f0f0')
        return {
            'fillColor': cor,
            'fillOpacity': FILL_OPACITY_SETORES,
            'color': '#ffffff',
            'weight': 0.8,
            'opacity': 0.6
        }

    geojson_mun = gdf_mun.__geo_interface__

    geojson_layer = folium.GeoJson(
        geojson_mun,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            style='background-color: white; color: #333; font-family: arial; font-size: 12px; padding: 10px; border-radius: 5px; box-shadow: 2px 2px 6px rgba(0,0,0,0.2);',
            localize=True
        ),
        highlight_function=lambda feature: {
            'fillOpacity': 0.95,
            'weight': 2.5,
            'color': '#000000'
        }
    ).add_to(m)

    geojson_layer.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tooltip-pane { z-index: 9999 !important; }</style>"
    ))

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png',
        attr='© OpenStreetMap contributors © CARTO',
        name='Linhas das Ruas e Quadras',
        overlay=True, control=False, opacity=LINHAS_OPACITY, pane="linhas_base_topo"
    ).add_to(m)

    folium.TileLayer(
        tiles='CartoDB voyager only labels',
        name='Nomes dos Bairros e Ruas',
        overlay=True, control=False, pane="labels_topo"
    ).add_to(m)

    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=PADDING_FIT_BOUNDS)

    titulo = f'''
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                background-color: rgba(255,255,255,0.95); border: 2px solid #333;
                border-radius: 8px; padding: 10px 20px; font-size: 14px; font-weight: bold;
                z-index: 1000; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
         {titulo_prefixo} - {municipio}
    </div>
    '''
    m.get_root().html.add_child(folium.Element(titulo))

    if legenda_html:
        m.get_root().html.add_child(folium.Element(legenda_html))

    m.save(output_path)
    return m


def classificar_densidade_por_municipio(grupo):
    """Classifica densidade em tercis dentro de cada município."""
    densidade = grupo['densidade_pop']

    if len(grupo) < 10:
        return pd.cut(densidade, bins=[0, 100, 1000, float('inf')],
                      labels=['Baixa', 'Média', 'Alta'], include_lowest=True)

    try:
        return pd.qcut(densidade, q=[0, 0.33, 0.66, 1.0],
                       labels=['Baixa', 'Média', 'Alta'], duplicates='drop')
    except ValueError:
        return pd.cut(densidade, bins=[0, 100, 1000, float('inf')],
                      labels=['Baixa', 'Média', 'Alta'], include_lowest=True)


def mapa_densidade_setorial_por_municipio(
    gdf_setores: gpd.GeoDataFrame,
    df_setores: pd.DataFrame,
    col_nm_mun: Optional[str] = None,
    output_dir: Optional[Path] = None,
    municipios_amostra: Optional[list[str]] = None,
) -> list[Path]:
    """
    MAPA 2: Gera um mapa de densidade populacional por município (~645 mapas).

    Args:
        gdf_setores: GeoDataFrame de setores censitários (shapefile)
        df_setores: DataFrame de setores processados (parquet)
        col_nm_mun: Coluna de nome do município (auto-detect se None)
        output_dir: Diretório de saída (default: OUTPUT_MAPAS)
        municipios_amostra: Se fornecido, gera mapas apenas para estes municípios

    Returns:
        Lista de caminhos dos arquivos HTML gerados.
    """
    if output_dir is None:
        output_dir = OUTPUT_MAPAS
    output_dir.mkdir(parents=True, exist_ok=True)

    colunas_extra = ['dist_minima_metros', 'categoria_acesso', 'acessibilidade_e2sfca', 'total_medicos_dentro']
    gdf_mapa_setores, col_nm_mun_auto = _preparar_dados_setores(
        df_setores, gdf_setores, colunas_extra=colunas_extra
    )
    if col_nm_mun is None:
        col_nm_mun = col_nm_mun_auto

    gdf_mapa_setores = gdf_mapa_setores.to_crs('EPSG:4326')

    municipios_unicos = sorted(gdf_mapa_setores[col_nm_mun].dropna().unique().tolist())

    if municipios_amostra is not None:
        municipios_unicos = [m for m in municipios_unicos if m in municipios_amostra]

    entries = []
    arquivos_gerados = []

    for i, municipio in enumerate(municipios_unicos, 1):
        gdf_mun = gdf_mapa_setores[gdf_mapa_setores[col_nm_mun] == municipio].copy().reset_index(drop=True)
        if len(gdf_mun) == 0:
            continue

        n_classes = min(5, len(gdf_mun['densidade_pop'].unique()))
        if n_classes < 2:
            gdf_mun['categoria_densidade'] = '1. Baixa'
            breaks = [0, float('inf')]
        else:
            gdf_mun['categoria_densidade'], breaks = _classificar_jenks(
                gdf_mun['densidade_pop'].tolist(), n_classes=n_classes
            )

        legenda_html = _gerar_legenda_densidade(breaks)

        nome_arquivo = municipio.replace(' ', '_').replace('/', '_').lower()
        output_file = output_dir / f'mapa_{nome_arquivo}.html'

        tooltip_fields = [col_nm_mun, 'CD_SETOR', 'v0001', 'area_final_km2', 'densidade_pop', 'categoria_acesso', 'acessibilidade_e2sfca']
        tooltip_aliases = ['🏙️ Município:', '📍 Setor:', '👥 População:', '📐 Área (km²):', '📊 Densidade (hab/km²):', '🏥 Acesso (E2SFCA):', '📈 Índice E2SFCA:']

        _gerar_mapa_setor_municipio(
            gdf_mun=gdf_mun,
            col_nm_mun=col_nm_mun,
            municipio=municipio,
            paleta=PALETA_DENSIDADE_SETORIAL,
            tooltip_fields=tooltip_fields,
            tooltip_aliases=tooltip_aliases,
            output_path=output_file,
            titulo_prefixo="Densidade Populacional",
            legenda_html=legenda_html,
        )
        arquivos_gerados.append(output_file)

        entries.append({
            'href': f'mapa_{nome_arquivo}.html',
            'nome': municipio,
            'info': f'{len(gdf_mun)} setores | {gdf_mun["v0001"].sum():,} hab',
        })

        if i % 50 == 0:
            print(f"   Progresso: {i}/{len(municipios_unicos)} municípios...")

    gerar_indice_mapas(
        titulo="🗺️ Mapas de Densidade Populacional - São Paulo",
        subtitulo="",
        entries=entries,
        output_path=output_dir / 'indice_mapas.html',
        grid_min_width="250px",
    )

    print(f"\n {len(entries)} mapas gerados!")
    print(f" Página índice: {output_dir / 'indice_mapas.html'}")
    return arquivos_gerados


def mapa_bivariado_setorial_por_municipio(
    gdf_setores: gpd.GeoDataFrame,
    df_setores: pd.DataFrame,
    pop_minima: int = 50,
    col_nm_mun: Optional[str] = None,
    output_dir: Optional[Path] = None,
    municipios_amostra: Optional[list[str]] = None,
) -> list[Path]:
    """
    MAPA 4: Gera mapas bivariados setoriais por município (~645 mapas).

    Classificação 3×3 + Irrelevante: Densidade Pop (Baixa/Média/Alta) × Acesso (Baixo/Médio/Alto).

    Args:
        gdf_setores: GeoDataFrame de setores censitários (shapefile)
        df_setores: DataFrame de setores processados (parquet)
        pop_minima: População mínima para classificação relevante
        col_nm_mun: Coluna de nome do município (auto-detect se None)
        output_dir: Diretório de saída (default: OUTPUT_MAPAS)
        municipios_amostra: Se fornecido, gera mapas apenas para estes municípios

    Returns:
        Lista de caminhos dos arquivos HTML gerados.
    """
    from src.visualization.classifiers import classificar_acesso_por_categoria

    if output_dir is None:
        output_dir = OUTPUT_MAPAS
    output_dir.mkdir(parents=True, exist_ok=True)

    colunas_extra = ['dist_minima_metros', 'categoria_acesso', 'total_medicos_dentro']
    gdf_mapa_setores, col_nm_mun_auto = _preparar_dados_setores(
        df_setores, gdf_setores, colunas_extra=colunas_extra
    )
    if col_nm_mun is None:
        col_nm_mun = col_nm_mun_auto

    gdf_mapa_setores['populacao_relevante'] = (gdf_mapa_setores['v0001'] >= pop_minima)

    gdf_mapa_setores.loc[gdf_mapa_setores['populacao_relevante'], 'cat_densidade_pop'] = (
        gdf_mapa_setores[gdf_mapa_setores['populacao_relevante']]
        .groupby(col_nm_mun, group_keys=False)
        .apply(classificar_densidade_por_municipio, include_groups=False)
    )
    gdf_mapa_setores['cat_densidade_pop'] = gdf_mapa_setores['cat_densidade_pop'].astype(str)
    gdf_mapa_setores.loc[~gdf_mapa_setores['populacao_relevante'], 'cat_densidade_pop'] = 'Irrelevante'

    gdf_mapa_setores['cat_acesso_medicos'] = gdf_mapa_setores['categoria_acesso'].apply(
        classificar_acesso_por_categoria
    )

    gdf_mapa_setores.loc[~gdf_mapa_setores['populacao_relevante'], 'categoria_bivariada'] = 'Irrelevante'
    gdf_mapa_setores.loc[gdf_mapa_setores['populacao_relevante'], 'categoria_bivariada'] = (
        gdf_mapa_setores.loc[gdf_mapa_setores['populacao_relevante'], 'cat_densidade_pop'] +
        ' + ' +
        gdf_mapa_setores.loc[gdf_mapa_setores['populacao_relevante'], 'cat_acesso_medicos']
    )

    categorias_nao_mapeadas = ~gdf_mapa_setores['categoria_bivariada'].isin(PALETA_BIVARIADA_SETORIAL.keys())
    n_nao_mapeados = categorias_nao_mapeadas.sum()
    if n_nao_mapeados > 0:
        print(f"\n    ATENÇÃO: {n_nao_mapeados:,} setores com categoria fora da paleta:")
        print(gdf_mapa_setores.loc[categorias_nao_mapeadas, 'categoria_bivariada'].value_counts())

    gdf_mapa_setores = gdf_mapa_setores.to_crs('EPSG:4326')

    municipios_unicos = sorted(gdf_mapa_setores[col_nm_mun].dropna().unique().tolist())

    if municipios_amostra is not None:
        municipios_unicos = [m for m in municipios_unicos if m in municipios_amostra]

    entries = []
    arquivos_gerados = []
    legenda_html = _gerar_legenda_bivariada()

    for i, municipio in enumerate(municipios_unicos, 1):
        gdf_mun = gdf_mapa_setores[gdf_mapa_setores[col_nm_mun] == municipio].copy().reset_index(drop=True)
        if len(gdf_mun) == 0:
            continue

        stats_mun = gdf_mun['categoria_bivariada'].value_counts()
        n_critico = stats_mun.get('Alta + Baixo', 0)
        n_deserto = stats_mun.get('Baixa + Baixo', 0)
        pop_critico = gdf_mun[gdf_mun['categoria_bivariada'] == 'Alta + Baixo']['v0001'].sum()

        nome_arquivo = municipio.replace(' ', '_').replace('/', '_').lower()
        output_file = output_dir / f'mapa_bivariado_{nome_arquivo}.html'

        tooltip_fields = [col_nm_mun, 'CD_SETOR', 'v0001', 'densidade_pop', 'cat_densidade_pop', 'cat_acesso_medicos', 'dist_minima_metros']
        tooltip_aliases = ['🏙️ Município:', '📍 Setor:', '👥 População:', '📊 Densidade (hab/km²):', '📈 Densidade:', '🏥 Acesso:', '📏 Dist. médico mais próx. (m):']

        _gerar_mapa_setor_municipio(
            gdf_mun=gdf_mun,
            col_nm_mun=col_nm_mun,
            municipio=municipio,
            paleta=PALETA_BIVARIADA_SETORIAL,
            tooltip_fields=tooltip_fields,
            tooltip_aliases=tooltip_aliases,
            output_path=output_file,
            titulo_prefixo="Desertos Médicos por Setor",
            legenda_html=legenda_html,
        )
        arquivos_gerados.append(output_file)

        entries.append({
            'href': f'mapa_bivariado_{nome_arquivo}.html',
            'nome': municipio,
            'info': f'{len(gdf_mun)} setores | {gdf_mun["v0001"].sum():,} hab',
            'stats': {
                'critico': n_critico,
                'deserto': n_deserto,
                'pop_risco': pop_critico,
            },
        })

        if i % 50 == 0:
            print(f"   Progresso: {i}/{len(municipios_unicos)} municípios...")

    gerar_indice_mapas(
        titulo=" Desertos Médicos por Setor Censitário",
        subtitulo="Mapa bivariado: Densidade Populacional × Acesso a Médicos (E2SFCA)",
        entries=entries,
        output_path=output_dir / 'indice_mapas_bivariados.html',
        grid_min_width="280px",
    )

    print(f"\n {len(entries)} mapas bivariados gerados!")
    print(f" Página índice: {output_dir / 'indice_mapas_bivariados.html'}")
    return arquivos_gerados
