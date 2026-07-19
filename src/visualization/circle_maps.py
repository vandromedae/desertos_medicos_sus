"""
Mapas com CircleMarker: densidade populacional, CNES, densidade médica.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

Funções movidas de src/visualization.py (versão original mantida em src/visualization_old.py).
"""

from pathlib import Path
from typing import Optional

import folium
import folium.plugins
import geopandas as gpd
import pandas as pd

from src.config import (
    COR_CNES,
    PALETA_DENSIDADE_MEDICA,
    PALETA_DENSIDADE_POPULACIONAL,
)
from src.visualization.helpers import criar_mapa_base, adicionar_metadados, adicionar_titulo, adicionar_legenda


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
    df = gdf_setores.copy()
    if coluna_municipio and codigo_municipio:
        df = df[df[coluna_municipio] == codigo_municipio]

    centro = df.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x

    m = criar_mapa_base(lat, lon, zoom=11)
    adicionar_metadados(m, "Densidade Populacional por Setor Censitário")

    df = df.copy()
    df["area_km2"] = df["area_km2"].replace(0, 0.001)
    df["densidade"] = (df[coluna_pop] / df["area_km2"]).round(0)

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

    centroids_x = df.geometry.centroid.x.values
    centroids_y = df.geometry.centroid.y.values
    cd_setor_vals = df.get("cd_setor", pd.Series(["N/A"] * len(df))).values
    pop_vals = df[coluna_pop].values
    dens_vals = df["densidade"].values

    for categoria, cor in PALETA_DENSIDADE_POPULACIONAL.items():
        mask = df["categoria"] == categoria
        if not mask.any():
            continue

        cat_y = centroids_y[mask.values]
        cat_x = centroids_x[mask.values]
        cat_setor = cd_setor_vals[mask.values]
        cat_pop = pop_vals[mask.values]
        cat_dens = dens_vals[mask.values]

        tooltips = [
            f"<b>Setor:</b> {s}<br><b>População:</b> {int(p):,}<br><b>Densidade:</b> {int(d):,.0f} hab/km²"
            for s, p, d in zip(cat_setor, cat_pop, cat_dens)
        ]

        fg = folium.FeatureGroup(name=f"População: {categoria}")
        folium.plugins.FastMarkerCluster(
            data=list(zip(cat_y, cat_x, tooltips)),
            callback="""function(row){
                var m = L.marker(new L.LatLng(row[0], row[1]));
                m.bindTooltip(row[2], {className: 'folium-tooltip'});
                return m;
            }""",
            name=categoria,
        ).add_to(fg)
        fg.add_to(m)

    adicionar_titulo(m, " Densidade Populacional por Setor Censitário")
    adicionar_legenda(m, "Densidade (hab/km²)", PALETA_DENSIDADE_POPULACIONAL)
    folium.LayerControl(collapsed=False).add_to(m)

    if output_path:
        m.save(output_path)
        print(f" Mapa salvo em: {output_path}")

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
    df_setores = gdf_setores.copy()
    if coluna_municipio_setor and codigo_municipio:
        df_setores = df_setores[df_setores[coluna_municipio_setor] == codigo_municipio]

    df_medicos_filtrado = df_medicos.copy()
    if "cod_mun_6" in df_medicos.columns and codigo_municipio:
        cod_mun_6 = codigo_municipio[:6]
        df_medicos_filtrado = df_medicos_filtrado[
            df_medicos_filtrado["cod_mun_6"] == cod_mun_6
        ]

    centro = df_setores.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x

    m = criar_mapa_base(lat, lon, zoom=11)
    adicionar_metadados(m, "Setores Censitários + CNES")

    fg_setores = folium.FeatureGroup(name="Setores Censitários")
    centroids = df_setores.geometry.centroid
    fg_setores.add_child(
        folium.plugins.FastMarkerCluster(
            data=list(zip(centroids.y.values, centroids.x.values)),
            callback="""function(row){
                return L.circleMarker(new L.LatLng(row[0], row[1]), {
                    radius: 2, color: '#3498db', fillColor: '#3498db',
                    fillOpacity: 0.4, weight: 0.3, fill: true
                });
            }""",
        )
    )
    fg_setores.add_to(m)

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

    adicionar_titulo(m, " Setores Censitários + CNES")
    folium.LayerControl(collapsed=False).add_to(m)

    if output_path:
        m.save(output_path)
        print(f" Mapa salvo em: {output_path}")

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

    df_setores = gdf_setores.copy()
    if coluna_municipio and codigo_municipio:
        df_setores = df_setores[df_setores[coluna_municipio] == codigo_municipio]

    gdf_medicos = gpd.GeoDataFrame(
        df_medicos,
        geometry=gpd.points_from_xy(df_medicos["long"], df_medicos["lat"]),
        crs="EPSG:4326",
    )

    if gdf_medicos.crs != df_setores.crs:
        gdf_medicos = gdf_medicos.to_crs(df_setores.crs)

    join_result = gpd.sjoin(gdf_medicos, df_setores[["cd_setor", "geometry"]], how="left", predicate="within")

    medicos_por_setor = (
        join_result
        .groupby("cd_setor")
        .agg(total_medicos=("profissional_cns", "nunique"))
        .reset_index()
    )

    df_setores = df_setores.merge(medicos_por_setor, on="cd_setor", how="left")
    df_setores["total_medicos"] = df_setores["total_medicos"].fillna(0).astype(int)

    df_setores["area_km2"] = df_setores["area_km2"].replace(0, 0.001)
    df_setores["pop_1k"] = df_setores["v0001"] / 1000
    df_setores["medicos_por_1k"] = (df_setores["total_medicos"] / df_setores["pop_1k"]).round(2)
    df_setores["categoria"] = df_setores["medicos_por_1k"].apply(classificar_densidade_medica)

    centro = df_setores.geometry.centroid.unary_union
    lat, lon = centro.y, centro.x

    m = criar_mapa_base(lat, lon, zoom=11)
    adicionar_metadados(m, "Densidade Médica SUS por Setor Censitário")

    centroids_x = df_setores.geometry.centroid.x.values
    centroids_y = df_setores.geometry.centroid.y.values
    cd_setor_vals = df_setores["cd_setor"].values
    pop_vals = df_setores["v0001"].values
    med_vals = df_setores["total_medicos"].values
    dens_vals = df_setores["medicos_por_1k"].values

    for categoria, cor in PALETA_DENSIDADE_MEDICA.items():
        mask = df_setores["categoria"] == categoria
        if not mask.any():
            continue

        cat_y = centroids_y[mask.values]
        cat_x = centroids_x[mask.values]
        cat_setor = cd_setor_vals[mask.values]
        cat_pop = pop_vals[mask.values]
        cat_med = med_vals[mask.values]
        cat_dens = dens_vals[mask.values]

        tooltips = [
            f"<b>Setor:</b> {s}<br><b>População:</b> {int(p):,}<br><b>Médicos SUS:</b> {int(med)}<br><b>Densidade:</b> {float(d):.2f} médicos/1k hab"
            for s, p, med, d in zip(cat_setor, cat_pop, cat_med, cat_dens)
        ]

        fg = folium.FeatureGroup(name=categoria)
        folium.plugins.FastMarkerCluster(
            data=list(zip(cat_y, cat_x, tooltips)),
            callback="""function(row){
                var m = L.circleMarker(new L.LatLng(row[0], row[1]), {
                    radius: 3, color: '%s', fillColor: '%s',
                    fillOpacity: 0.75, weight: 0.5, fill: true
                });
                m.bindTooltip(row[2], {className: 'folium-tooltip'});
                return m;
            }""" % (cor, cor),
        ).add_to(fg)
        fg.add_to(m)

    adicionar_titulo(m, "Densidade Médica SUS por Setor Censitário")
    adicionar_legenda(m, "Médicos por 1.000 hab", PALETA_DENSIDADE_MEDICA)
    folium.LayerControl(collapsed=False).add_to(m)

    if output_path:
        m.save(output_path)
        print(f" Mapa salvo em: {output_path}")

    return m
