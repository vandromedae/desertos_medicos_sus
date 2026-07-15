"""
Módulo de visualização e geração de mapas interativos.
"""

from pathlib import Path
from typing import Optional

import folium
import geopandas as gpd
import pandas as pd

from src.config import (
    COR_CNES,
    IBGE_SP_CAPITAL,
    OUTPUT_MAPAS,
    PALETA_DENSIDADE_MEDICA,
    PALETA_DENSIDADE_POPULACIONAL,
)


def _criar_mapa_base(lat: float, lon: float, zoom: int = 11) -> folium.Map:
    """Cria mapa base com tema escuro."""
    return folium.Map(
        location=[lat, lon],
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
    )


def _adicionar_titulo(m: folium.Map, titulo: str) -> None:
    """Adiciona título flutuante ao mapa."""
    html = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                background-color: rgba(255,255,255,0.95); border: 2px solid #333;
                border-radius: 8px; padding: 12px 24px; font-size: 16px;
                font-weight: bold; z-index: 9999; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);">
        {titulo}
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))


def _adicionar_legenda(m: folium.Map, titulo: str, itens: dict[str, str]) -> None:
    """Adiciona legenda customizada ao mapa."""
    itens_html = ""
    for label, cor in itens.items():
        itens_html += f"""
        <i style="background:{cor};width:16px;height:16px;float:left;
                  margin-right:8px;opacity:0.8;border:1px solid #333;"></i>
        {label}<br>
        """
    
    html = f"""
    <div style="position: fixed; bottom: 30px; left: 30px;
                width: 260px; background-color: rgba(255,255,255,0.95);
                border: 2px solid #333; border-radius: 8px; padding: 12px;
                font-size: 12px; z-index: 9999; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);">
        <b style="font-size:14px;">{titulo}</b><br><br>
        {itens_html}
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))


def mapa_densidade_populacional(
    gdf_setores: gpd.GeoDataFrame,
    coluna_pop: str = "v0001",
    coluna_municipio: Optional[str] = None,
    codigo_municipio: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> folium.Map:
    """
    Gera mapa de densidade populacional por setor censitário.
    
    Args:
        gdf_setores: GeoDataFrame de setores censitários
        coluna_pop: Coluna de população
        coluna_municipio: Coluna de código do município (para filtro)
        codigo_municipio: Código IBGE do município (filtro opcional)
        output_path: Caminho para salvar o HTML
    
    Returns:
        Objeto folium.Map
    """
    # Filtrar por município se especificado
    df = gdf_setores.copy()
    if coluna_municipio and codigo_municipio:
        df = df[df[coluna_municipio] == codigo_municipio]
    
    # Calcular centroide para zoom
    centro = df.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x
    
    m = _criar_mapa_base(lat, lon, zoom=11)
    
    # Calcular densidade (hab/km²)
    df = df.copy()
    df["area_km2"] = df["area_km2"].replace(0, 0.001)
    df["densidade"] = (df[coluna_pop] / df["area_km2"]).round(0)
    
    # Classificar por percentis
    percentis = df["densidade"].quantile([0.2, 0.4, 0.6, 0.8]).values
    
    def classificar(dens):
        if dens <= percentis[0]:
            return "1. Muito baixa"
        if dens <= percentis[1]:
            return "2. Baixa"
        if dens <= percentis[2]:
            return "3. Média"
        if dens <= percentis[3]:
            return "4. Alta"
        return "5. Muito alta"
    
    df["categoria"] = df["densidade"].apply(classificar)
    
    # Adicionar setores ao mapa
    for categoria, cor in PALETA_DENSIDADE_POPULACIONAL.items():
        df_cat = df[df["categoria"] == categoria]
        if df_cat.empty:
            continue
        
        fg = folium.FeatureGroup(name=f"População: {categoria}")
        for _, row in df_cat.iterrows():
            folium.CircleMarker(
                location=[row.geometry.centroid.y, row.geometry.centroid.x],
                radius=3,
                color=cor,
                fill=True,
                fill_color=cor,
                fill_opacity=0.7,
                weight=0.5,
                tooltip=(
                    f"<b>Setor:</b> {row.get('cd_setor', 'N/A')}<br>"
                    f"<b>População:</b> {row[coluna_pop]:,}<br>"
                    f"<b>Densidade:</b> {row['densidade']:,.0f} hab/km²"
                ),
            ).add_to(fg)
        fg.add_to(m)
    
    _adicionar_titulo(m, "👥 Densidade Populacional por Setor Censitário")
    _adicionar_legenda(m, "Densidade (hab/km²)", PALETA_DENSIDADE_POPULACIONAL)
    folium.LayerControl(collapsed=False).add_to(m)
    
    if output_path:
        m.save(output_path)
        print(f"💾 Mapa salvo em: {output_path}")
    
    return m


def mapa_cnes_setores(
    gdf_setores: gpd.GeoDataFrame,
    df_medicos: pd.DataFrame,
    coluna_municipio_setor: Optional[str] = None,
    codigo_municipio: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> folium.Map:
    """
    Gera mapa com setores censitários e CNES sobrepostos.
    
    Args:
        gdf_setores: GeoDataFrame de setores
        df_medicos: DataFrame de médicos com colunas lat/long
        coluna_municipio_setor: Coluna de município para filtro
        codigo_municipio: Código IBGE para filtro
        output_path: Caminho para salvar HTML
    
    Returns:
        Objeto folium.Map
    """
    # Filtrar setores
    df_setores = gdf_setores.copy()
    if coluna_municipio_setor and codigo_municipio:
        df_setores = df_setores[df_setores[coluna_municipio_setor] == codigo_municipio]
    
    # Filtrar médicos
    df_medicos_filtrado = df_medicos.copy()
    if "cod_mun_6" in df_medicos.columns and codigo_municipio:
        cod_mun_6 = codigo_municipio[:6]
        df_medicos_filtrado = df_medicos_filtrado[
            df_medicos_filtrado["cod_mun_6"] == cod_mun_6
        ]
    
    # Centro
    centro = df_setores.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x
    
    m = _criar_mapa_base(lat, lon, zoom=11)
    
    # Camada de setores (fundo)
    fg_setores = folium.FeatureGroup(name="Setores Censitários")
    for _, row in df_setores.iterrows():
        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            radius=2,
            color="#3498db",
            fill=True,
            fill_color="#3498db",
            fill_opacity=0.4,
            weight=0.3,
        ).add_to(fg_setores)
    fg_setores.add_to(m)
    
    # Camada de CNES (agrupados)
    if not df_medicos_filtrado.empty and "lat" in df_medicos_filtrado.columns:
        cnes_agg = (
            df_medicos_filtrado
            .groupby(["cnes", "nome_fantaia", "lat", "long"])
            .agg(total_medicos=("profissional_cns", "nunique"))
            .reset_index()
        )
        
        def classificar_cnes(n):
            if n <= 2:
                return 5
            if n <= 5:
                return 8
            if n <= 10:
                return 12
            return 16
        
        cnes_agg["radius"] = cnes_agg["total_medicos"].apply(classificar_cnes)
        
        fg_cnes = folium.FeatureGroup(name="CNES (Estabelecimentos)")
        for _, row in cnes_agg.iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["long"]],
                radius=row["radius"],
                color="white",
                fill=True,
                fill_color=COR_CNES,
                fill_opacity=0.9,
                weight=2,
                tooltip=(
                    f"<b>{row['nome_fantaia']}</b><br>"
                    f"<b>CNES:</b> {row['cnes']}<br>"
                    f"<b>Médicos SUS:</b> {row['total_medicos']}"
                ),
            ).add_to(fg_cnes)
        fg_cnes.add_to(m)
    
    _adicionar_titulo(m, "🏥 Setores Censitários + CNES")
    folium.LayerControl(collapsed=False).add_to(m)
    
    if output_path:
        m.save(output_path)
        print(f"💾 Mapa salvo em: {output_path}")
    
    return m


def mapa_densidade_medica_setorial(
    gdf_setores: gpd.GeoDataFrame,
    df_medicos: pd.DataFrame,
    coluna_municipio: Optional[str] = None,
    codigo_municipio: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> folium.Map:
    """
    Gera mapa de densidade médica (médicos/1000 hab) por setor censitário.
    
    Args:
        gdf_setores: GeoDataFrame de setores
        df_medicos: DataFrame de médicos com lat/long
        coluna_municipio: Coluna de município para filtro
        codigo_municipio: Código IBGE para filtro
        output_path: Caminho para salvar HTML
    
    Returns:
        Objeto folium.Map
    """
    from src.analysis import classificar_densidade_medica
    
    # Filtrar setores
    df_setores = gdf_setores.copy()
    if coluna_municipio and codigo_municipio:
        df_setores = df_setores[df_setores[coluna_municipio] == codigo_municipio]
    
    # Associar médicos aos setores via spatial join
    gdf_medicos = gpd.GeoDataFrame(
        df_medicos,
        geometry=gpd.points_from_xy(df_medicos["long"], df_medicos["lat"]),
        crs="EPSG:4326",
    )
    
    # Garantir mesmo CRS
    if gdf_medicos.crs != df_setores.crs:
        gdf_medicos = gdf_medicos.to_crs(df_setores.crs)
    
    # Spatial join: contar médicos por setor
    join_result = gpd.sjoin(gdf_medicos, df_setores[["cd_setor", "geometry"]], how="left", predicate="within")
    
    medicos_por_setor = (
        join_result
        .groupby("cd_setor")
        .agg(total_medicos=("profissional_cns", "nunique"))
        .reset_index()
    )
    
    # Merge com setores
    df_setores = df_setores.merge(medicos_por_setor, on="cd_setor", how="left")
    df_setores["total_medicos"] = df_setores["total_medicos"].fillna(0).astype(int)
    
    # Calcular densidade
    df_setores["area_km2"] = df_setores["area_km2"].replace(0, 0.001)
    df_setores["pop_1k"] = df_setores["v0001"] / 1000
    df_setores["medicos_por_1k"] = (df_setores["total_medicos"] / df_setores["pop_1k"]).round(2)
    df_setores["categoria"] = df_setores["medicos_por_1k"].apply(classificar_densidade_medica)
    
    # Centro
    centro = df_setores.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x
    
    m = _criar_mapa_base(lat, lon, zoom=11)
    
    # Adicionar setores coloridos
    for categoria, cor in PALETA_DENSIDADE_MEDICA.items():
        df_cat = df_setores[df_setores["categoria"] == categoria]
        if df_cat.empty:
            continue
        
        fg = folium.FeatureGroup(name=categoria)
        for _, row in df_cat.iterrows():
            folium.CircleMarker(
                location=[row.geometry.centroid.y, row.geometry.centroid.x],
                radius=3,
                color=cor,
                fill=True,
                fill_color=cor,
                fill_opacity=0.75,
                weight=0.5,
                tooltip=(
                    f"<b>Setor:</b> {row['cd_setor']}<br>"
                    f"<b>População:</b> {row['v0001']:,}<br>"
                    f"<b>Médicos SUS:</b> {row['total_medicos']}<br>"
                    f"<b>Densidade:</b> {row['medicos_por_1k']:.2f} médicos/1k hab"
                ),
            ).add_to(fg)
        fg.add_to(m)
    
    _adicionar_titulo(m, "🏥 Densidade Médica SUS por Setor Censitário")
    _adicionar_legenda(m, "Médicos por 1.000 hab", PALETA_DENSIDADE_MEDICA)
    folium.LayerControl(collapsed=False).add_to(m)
    
    if output_path:
        m.save(output_path)
        print(f"💾 Mapa salvo em: {output_path}")
    
    return m