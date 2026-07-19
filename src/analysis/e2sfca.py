"""
Módulo de cálculo do índice E2SFCA (Enhanced Two-Step Floating Catchment Area).

Implementação fiel ao notebook 03_analise_geoespacial.ipynb, preservando
a lógica numérica exata e os parâmetros originais.

Referência: Luo, W., & Wang, F. (2003).

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import gc
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

from src.config import BETA, CRS_PROJETADO, RAIO_CAPTURA_M


def peso_gaussiano(distancia_m: float, raio_m: float = RAIO_CAPTURA_M, beta: float = BETA) -> float:
    """
    Calcula peso gaussiano. Retorna 0 para distâncias >= raio.

    Fórmula: W(d) = exp(-β * (d/r)²) se d < r, senão 0
    """
    if distancia_m >= raio_m:
        return 0.0
    return np.exp(-beta * (distancia_m / raio_m) ** 2)


def calcular_percentis_e2sfca(acessibilidade: pd.Series) -> tuple[float, float, float, float, float]:
    """
    Calcula percentis para classificação E2SFCA.
    Percentis são computados apenas sobre valores positivos (> 0).

    Returns:
        Tupla (p5, p25, p50, p75, p90)
    """
    idx_positivo = acessibilidade[acessibilidade > 0]
    if len(idx_positivo) > 0:
        p5 = idx_positivo.quantile(0.05)
        p25 = idx_positivo.quantile(0.25)
        p50 = idx_positivo.quantile(0.50)
        p75 = idx_positivo.quantile(0.75)
        p90 = idx_positivo.quantile(0.90)
    else:
        p5, p25, p50, p75, p90 = 0.0, 0.0, 0.0, 0.0, 0.0
    return p5, p25, p50, p75, p90


def classificar_e2sfca(valor: float, percentis: tuple[float, float, float, float, float]) -> str:
    """
    Classifica índice E2SFCA em 6 categorias usando percentis pré-computados.

    Args:
        valor: Índice E2SFCA do setor
        percentis: Tupla (p5, p25, p50, p75, p90) computed from positive values
    """
    p5, p25, p50, p75, _p90 = percentis
    if valor == 0:
        return '6. Deserto médico (sem acesso)'
    elif valor < p5:
        return '5. Crítico (acesso muito baixo)'
    elif valor < p25:
        return '4. Limitado (acesso baixo)'
    elif valor < p50:
        return '3. Moderado (acesso médio)'
    elif valor < p75:
        return '2. Bom (acesso alto)'
    else:
        return '1. Excelente (acesso muito alto)'


def calcular_e2sfca(
    gdf_medicos_setor: gpd.GeoDataFrame,
    gdf_setores: gpd.GeoDataFrame,
    raio_captura_m: float = RAIO_CAPTURA_M,
    beta: float = BETA,
    crs_projetado: str = CRS_PROJETADO,
) -> pd.DataFrame:
    """
    Calcula o índice E2SFCA completo (Passo 1 global + Passo 2 por município + classificação).

    Este é o algoritmo principal Luo & Wang (2003) implementado no notebook 03.

    Args:
        gdf_medicos_setor: GeoDataFrame de médicos com coluna CD_SETOR (resultado do spatial join).
        gdf_setores: GeoDataFrame de setores censitários com colunas v0001, CD_SETOR, CD_MUN, geometry.
        raio_captura_m: Raio de captura em metros (default 5000).
        beta: Parâmetro de decaimento gaussiano (default 0.5).
        crs_projetado: CRS projetado em metros (default EPSG:31983).

    Returns:
        DataFrame com colunas: CD_SETOR, acessibilidade_e2sfca, categoria_acesso
    """
    print("=" * 70)
    print("CÁLCULO DE ACESSIBILIDADE VIA E2SFCA (OTIMIZADO POR MUNICÍPIOS)")
    print("=" * 70)
    print(f"\n  Configurações:")
    print(f"   Raio de captura: {raio_captura_m / 1000:.0f} km")
    print(f"   Função de decaimento: Gaussiana (β={beta})")
    print(f"   CRS projetado: {crs_projetado}")

    # ============================================================
    # PASSO 0: Preparar dados
    # ============================================================
    print("\n Preparando dados globais...")

    # 1. Agregar médicos por CNES (ponto único por estabelecimento)
    print("\n1. Agregando médicos por CNES...")
    cnes_agg = (
        gdf_medicos_setor
        .groupby(['cnes', 'municipio', 'nome_fantaia'])
        .agg(
            total_medicos_cnes=('profissional_cns', 'nunique'),
            latitude=('latitude', 'first'),
            longitude=('longitude', 'first')
        )
        .reset_index()
    )

    gdf_cnes = gpd.GeoDataFrame(
        cnes_agg,
        geometry=gpd.points_from_xy(cnes_agg['longitude'], cnes_agg['latitude']),
        crs='EPSG:4326'
    )
    gdf_cnes = gdf_cnes[gdf_cnes['total_medicos_cnes'] > 0].copy()
    print(f"    {len(gdf_cnes):,} CNES com médicos SUS")

    # 2. Converter para CRS projetado
    print(f"\n2. Convertendo para CRS projetado ({crs_projetado})...")
    gdf_cnes_proj = gdf_cnes.to_crs(crs_projetado)
    gdf_setores_proj = gdf_setores.to_crs(crs_projetado)

    # Criar centróides dos setores (com população)
    gdf_setores_centroides = gdf_setores_proj.copy()
    gdf_setores_centroides['geometry'] = gdf_setores_centroides.centroid
    gdf_setores_centroides['populacao'] = gdf_setores_centroides['v0001'].fillna(0).astype(int)

    # Garantir coluna de município
    if 'cod_mun_ibge' not in gdf_setores_centroides.columns:
        gdf_setores_centroides['cod_mun_ibge'] = gdf_setores_centroides['CD_MUN'].astype(str).str[:6]

    print(f"    CRS unificado em metros")

    # 3. Lista de municípios para processar
    municipios_unicos = sorted(gdf_setores_centroides['cod_mun_ibge'].dropna().unique().tolist())
    print(f"   {len(municipios_unicos)} municípios para processar")

    # ============================================================
    # PASSO 1 GLOBAL: Calcular razão de oferta (R_j) para cada CNES
    # ============================================================
    print(f"\n PASSO 1 GLOBAL: Calculando razão de oferta ponderada por CNES...")
    print(f"    Processando {len(gdf_cnes_proj):,} CNES...")

    # Criar buffers nos CNES
    gdf_cnes_proj['buffer'] = gdf_cnes_proj.geometry.buffer(raio_captura_m)

    # Spatial join: centróides dos setores DENTRO dos buffers dos CNES
    join_passo1 = gpd.sjoin(
        gdf_setores_centroides[['CD_SETOR', 'populacao', 'geometry']],
        gdf_cnes_proj[['cnes', 'total_medicos_cnes', 'buffer']].set_geometry('buffer'),
        how='left',
        predicate='within'
    )

    if 'index_right' in join_passo1.columns:
        join_passo1 = join_passo1.drop(columns=['index_right'])

    # Calcular distância entre centróide do setor e ponto do CNES
    gdf_cnes_pts = gdf_cnes_proj[['cnes', 'geometry']].rename(columns={'geometry': 'geom_cnes'})
    join_passo1 = join_passo1.merge(gdf_cnes_pts, on='cnes', how='left')

    join_passo1['distancia_m'] = join_passo1.apply(
        lambda row: row['geometry'].distance(row['geom_cnes']) if pd.notna(row['geom_cnes']) else raio_captura_m,
        axis=1
    )

    # Calcular peso gaussiano
    join_passo1['peso'] = join_passo1['distancia_m'].apply(
        lambda d: peso_gaussiano(d, raio_m=raio_captura_m, beta=beta)
    )

    # População ponderada por CNES
    join_passo1['pop_ponderada'] = join_passo1['populacao'] * join_passo1['peso']

    pop_ponderada_por_cnes = join_passo1.groupby('cnes')['pop_ponderada'].sum().reset_index()
    pop_ponderada_por_cnes.columns = ['cnes', 'populacao_ponderada']

    # Merge com dados dos CNES
    gdf_cnes_proj = gdf_cnes_proj.merge(pop_ponderada_por_cnes, on='cnes', how='left')
    gdf_cnes_proj['populacao_ponderada'] = gdf_cnes_proj['populacao_ponderada'].fillna(0)

    # Calcular razão R_j = médicos / população_ponderada
    gdf_cnes_proj['razao_oferta'] = np.where(
        gdf_cnes_proj['populacao_ponderada'] > 0,
        gdf_cnes_proj['total_medicos_cnes'] / gdf_cnes_proj['populacao_ponderada'],
        0
    )

    print(f"    Razão de oferta calculada para {len(gdf_cnes_proj):,} CNES")
    print(f"    Estatísticas da razão de oferta (R_j):")
    print(f"      Média: {gdf_cnes_proj['razao_oferta'].mean():.6f} médicos/hab")
    print(f"      Mediana: {gdf_cnes_proj['razao_oferta'].median():.6f}")
    print(f"      Máximo: {gdf_cnes_proj['razao_oferta'].max():.6f}")

    # Liberar memória
    del join_passo1, pop_ponderada_por_cnes
    gc.collect()

    # ============================================================
    # PASSO 2 POR MUNICÍPIO: Calcular acessibilidade (A_i) por setor
    # ============================================================
    print(f"\n PASSO 2: Calculando acessibilidade E2SFCA por município...")
    print(f"   Processando {len(municipios_unicos)} municípios...")

    gdf_cnes_proj['cnes_x'] = gdf_cnes_proj.geometry.x
    gdf_cnes_proj['cnes_y'] = gdf_cnes_proj.geometry.y

    resultados = []

    for idx_mun, cod_mun in enumerate(municipios_unicos, 1):
        # Filtrar setores do município
        setores_mun = gdf_setores_centroides[
            gdf_setores_centroides['cod_mun_ibge'] == cod_mun
        ].copy()

        if len(setores_mun) == 0:
            continue

        # Criar buffers nos centróides dos setores deste município
        setores_mun['buffer_setor'] = setores_mun.geometry.buffer(raio_captura_m)

        cnes_cols = ['cnes', 'razao_oferta', 'cnes_x', 'cnes_y', 'geometry']
        gdf_cnes_sjoin = gdf_cnes_proj[cnes_cols].copy()

        # Spatial join: CNES dentro dos buffers dos setores
        join_passo2 = gpd.sjoin(
            setores_mun[['CD_SETOR', 'buffer_setor']].set_geometry('buffer_setor'),
            gdf_cnes_sjoin,
            how='left',
            predicate='contains'
        )

        if 'index_right' in join_passo2.columns:
            join_passo2 = join_passo2.drop(columns=['index_right'])

        join_passo2['ponto_cnes'] = gpd.points_from_xy(
            join_passo2['cnes_x'],
            join_passo2['cnes_y']
        )

        setores_centroide_orig = setores_mun[['CD_SETOR', 'geometry']].copy()
        setores_centroide_orig = setores_centroide_orig.rename(columns={'geometry': 'centroide_setor'})

        join_passo2 = join_passo2.merge(setores_centroide_orig, on='CD_SETOR', how='left')

        # Calcular distância usando shapely
        join_passo2['distancia_m'] = join_passo2.apply(
            lambda row: row['centroide_setor'].distance(row['ponto_cnes'])
            if pd.notna(row['ponto_cnes']) and pd.notna(row['centroide_setor'])
            else raio_captura_m,
            axis=1
        )

        # Calcular peso gaussiano
        join_passo2['peso'] = join_passo2['distancia_m'].apply(
            lambda d: peso_gaussiano(d, raio_m=raio_captura_m, beta=beta)
        )

        # Acessibilidade = Σ(R_j × W(d_ij))
        join_passo2['acessibilidade_contrib'] = join_passo2['razao_oferta'] * join_passo2['peso']

        acessibilidade_mun = join_passo2.groupby('CD_SETOR')['acessibilidade_contrib'].sum().reset_index()
        acessibilidade_mun.columns = ['CD_SETOR', 'acessibilidade_e2sfca']

        resultados.append(acessibilidade_mun)

        # Liberar memória a cada lote
        del setores_mun, join_passo2, acessibilidade_mun

        if idx_mun % 50 == 0:
            print(f"   Progresso: {idx_mun}/{len(municipios_unicos)} municípios...")
            gc.collect()

    # Concatenar todos os resultados
    print(f"\n   Processamento concluído. Concatenando resultados...")
    acessibilidade_por_setor = pd.concat(resultados, ignore_index=True)
    del resultados
    gc.collect()

    # Preencher setores sem CNES no raio (acessibilidade = 0)
    todos_setores = gdf_setores[['CD_SETOR']].copy()
    acessibilidade_por_setor = todos_setores.merge(
        acessibilidade_por_setor,
        on='CD_SETOR',
        how='left'
    )
    acessibilidade_por_setor['acessibilidade_e2sfca'] = acessibilidade_por_setor['acessibilidade_e2sfca'].fillna(0)

    print(f"    Acessibilidade E2SFCA calculada para {len(acessibilidade_por_setor):,} setores")
    print(f"    Estatísticas do índice E2SFCA (A_i):")
    print(f"    Média: {acessibilidade_por_setor['acessibilidade_e2sfca'].mean():.6f}")
    print(f"    Mediana: {acessibilidade_por_setor['acessibilidade_e2sfca'].median():.6f}")
    print(f"    Máximo: {acessibilidade_por_setor['acessibilidade_e2sfca'].max():.6f}")
    print(f"    Setores com acessibilidade = 0: {(acessibilidade_por_setor['acessibilidade_e2sfca'] == 0).sum():,}")

    # ============================================================
    # PASSO 3: Classificar em categorias (percentis)
    # ============================================================
    print("\n PASSO 3: Classificando acessibilidade em categorias...")

    percentis = calcular_percentis_e2sfca(acessibilidade_por_setor['acessibilidade_e2sfca'])

    p5, p25, p50, p75, p90 = percentis
    print(f"      Percentis do índice E2SFCA (apenas setores com acesso > 0):")
    print(f"      P5:  {p5:.6f}")
    print(f"      P25: {p25:.6f}")
    print(f"      P50: {p50:.6f}")
    print(f"      P75: {p75:.6f}")
    print(f"      P90: {p90:.6f}")

    acessibilidade_por_setor['categoria_acesso'] = acessibilidade_por_setor['acessibilidade_e2sfca'].apply(
        lambda v: classificar_e2sfca(v, percentis)
    )

    print(f"\n    Classificação concluída")
    print(f"\n    Distribuição por categoria:")
    distribuicao = acessibilidade_por_setor['categoria_acesso'].value_counts().sort_index()
    for categoria, count in distribuicao.items():
        pct = count / len(acessibilidade_por_setor) * 100
        print(f"      {categoria:50s}: {count:>8,} ({pct:.1f}%)")

    return acessibilidade_por_setor


def anexar_metricas_legadas(
    df_e2sfca: pd.DataFrame,
    gdf_medicos_setor: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Anexa métricas complementares ao resultado E2SFCA:
      - dist_minima_metros: distância ao CNES mais próximo (sjoin_nearest)
      - total_medicos_dentro: médicos com ponto dentro do setor
      - total_cnes_dentro: CNES com ponto dentro do setor

    Equivale ao Passo 5 do notebook 03_analise_geoespacial.ipynb.

    Args:
        df_e2sfca: DataFrame com coluna CD_SETOR (merge com shapefile já feito).
        gdf_medicos_setor: GeoDataFrame de médicos com CD_SETOR (resultado do spatial join).

    Returns:
        DataFrame com 3 colunas novas: dist_minima_metros, total_medicos_dentro,
        total_cnes_dentro.
    """
    import warnings as _w

    df = df_e2sfca.copy()

    # --- Distância mínima ao CNES mais próximo ---
    # Preparar centroides dos setores em CRS projetado
    if 'geometry' not in df.columns:
        _w.warn(
            "df_e2sfca não tem coluna 'geometry'; dist_minima_metros será 99999.",
            stacklevel=2,
        )
        df['dist_minima_metros'] = 99999
    else:
        # GeoDataFrame temporário a partir do DataFrame resultante
        gdf_tmp = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        gdf_tmp_proj = gdf_tmp.to_crs('EPSG:31983').copy()
        gdf_tmp_proj['geometry'] = gdf_tmp_proj.centroid

        # CNES projetados (pontos com médicos > 0)
        cnes_agg = (
            gdf_medicos_setor
            .groupby(['cnes', 'municipio', 'nome_fantaia'])
            .agg(
                total_medicos_cnes=('profissional_cns', 'nunique'),
                latitude=('latitude', 'first'),
                longitude=('longitude', 'first'),
            )
            .reset_index()
        )
        gdf_cnes = gpd.GeoDataFrame(
            cnes_agg,
            geometry=gpd.points_from_xy(cnes_agg['longitude'], cnes_agg['latitude']),
            crs='EPSG:4326',
        )
        gdf_cnes_proj = gdf_cnes[gdf_cnes['total_medicos_cnes'] > 0].to_crs('EPSG:31983')

        nearest_result = gpd.sjoin_nearest(
            gdf_tmp_proj[['CD_SETOR', 'geometry']],
            gdf_cnes_proj[['cnes', 'geometry']],
            how='left',
            distance_col='dist_minima_metros',
        )
        dist_min = (
            nearest_result
            .groupby('CD_SETOR')['dist_minima_metros']
            .min()
            .reset_index()
        )
        df = df.merge(dist_min, on='CD_SETOR', how='left')

    df['dist_minima_metros'] = df['dist_minima_metros'].fillna(99999)

    # --- Médicos dentro do setor ---
    medicos_por_setor = (
        gdf_medicos_setor
        .groupby('CD_SETOR')
        .agg(
            total_medicos_dentro=('profissional_cns', 'nunique'),
            total_cnes_dentro=('cnes', 'nunique'),
        )
        .reset_index()
    )
    df = df.merge(medicos_por_setor, on='CD_SETOR', how='left')
    df['total_medicos_dentro'] = df['total_medicos_dentro'].fillna(0).astype(int)
    df['total_cnes_dentro'] = df['total_cnes_dentro'].fillna(0).astype(int)

    return df


def agregar_e2sfca_por_municipio(df_setores_e2sfca: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega métricas E2SFCA por município (a partir do nível de setor).

    Equivale às linhas 645-693 do notebook 03_analise_geoespacial.ipynb.

    Args:
        df_setores_e2sfca: DataFrame com colunas cod_mun_ibge, CD_SETOR,
            v0001, acessibilidade_e2sfca, categoria_acesso, dist_minima_metros,
            total_medicos_dentro.

    Returns:
        DataFrame municipal com colunas: cod_mun_ibge, num_setores,
        populacao_setorial, dist_media_km, acessibilidade_e2sfca_media,
        pct_setores_deserto, pct_acesso_baixo, etc.
    """
    col_pop = next(
        (c for c in ['v0001', 'POPULACAO', 'populacao'] if c in df_setores_e2sfca.columns),
        None,
    )
    col_setor = next(
        (c for c in ['CD_SETOR', 'cd_setor'] if c in df_setores_e2sfca.columns),
        'CD_SETOR',
    )

    agg = df_setores_e2sfca.groupby('cod_mun_ibge').agg(
        num_setores=(col_setor, 'count'),
        populacao_setorial=(col_pop, 'sum') if col_pop else (col_setor, 'count'),
        dist_media=('dist_minima_metros', 'mean'),
        dist_mediana=('dist_minima_metros', 'median'),
        dist_max=('dist_minima_metros', 'max'),
        acessibilidade_e2sfca_media=('acessibilidade_e2sfca', 'mean'),
        acessibilidade_e2sfca_mediana=('acessibilidade_e2sfca', 'median'),
        acessibilidade_e2sfca_max=('acessibilidade_e2sfca', 'max'),
        num_setores_deserto=(
            'categoria_acesso',
            lambda x: (x == '6. Deserto médico (sem acesso)').sum(),
        ),
        num_setores_critico=(
            'categoria_acesso',
            lambda x: (x == '5. Crítico (acesso muito baixo)').sum(),
        ),
        num_setores_limitado=(
            'categoria_acesso',
            lambda x: (x == '4. Limitado (acesso baixo)').sum(),
        ),
        num_setores_moderado=(
            'categoria_acesso',
            lambda x: (x == '3. Moderado (acesso médio)').sum(),
        ),
        num_setores_bom=(
            'categoria_acesso',
            lambda x: (x == '2. Bom (acesso alto)').sum(),
        ),
        num_setores_excelente=(
            'categoria_acesso',
            lambda x: (x == '1. Excelente (acesso muito alto)').sum(),
        ),
        medicos_dentro_setor=('total_medicos_dentro', 'sum'),
    ).reset_index()

    agg['pct_setores_deserto'] = (
        agg['num_setores_deserto'] / agg['num_setores'] * 100
    ).round(1)

    agg['pct_setores_critico'] = (
        agg['num_setores_critico'] / agg['num_setores'] * 100
    ).round(1)

    agg['pct_setores_excelente'] = (
        agg['num_setores_excelente'] / agg['num_setores'] * 100
    ).round(1)

    agg['pct_acesso_baixo'] = (
        (agg['num_setores_deserto'] + agg['num_setores_critico'] + agg['num_setores_limitado'])
        / agg['num_setores'] * 100
    ).round(1)

    agg['dist_media_km'] = (agg['dist_media'] / 1000).round(2)
    agg['dist_mediana_km'] = (agg['dist_mediana'] / 1000).round(2)
    agg['dist_max_km'] = (agg['dist_max'] / 1000).round(2)

    return agg


def comparar_densidade_vs_e2sfca(
    df_municipal: pd.DataFrame,
    df_acessibilidade_mun: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza base municipal (densidade médica) com acessibilidade E2SFCA agregada.

    Equivale ao passo 2 (merge) da célula de comparação do notebook 03.

    Args:
        df_municipal: Saída de cruzar_medicos_populacao (com cod_mun_ibge,
            nm_mun, total_medicos, populacao, medicos_por_1k, categoria_densidade).
        df_acessibilidade_mun: Saída de agregar_e2sfca_por_municipio.

    Returns:
        DataFrame com inner join em cod_mun_ibge.
    """
    colunas_municipal = [
        'cod_mun_ibge', 'nm_mun', 'total_medicos', 'populacao',
        'medicos_por_1k', 'categoria_densidade',
    ]
    colunas_acesso = [
        'cod_mun_ibge', 'num_setores', 'populacao_setorial',
        'dist_media_km', 'dist_mediana_km', 'dist_max_km',
        'acessibilidade_e2sfca_media', 'acessibilidade_e2sfca_mediana',
        'pct_setores_deserto', 'pct_setores_critico', 'pct_setores_excelente',
        'pct_acesso_baixo', 'medicos_dentro_setor',
    ]

    cols_m = [c for c in colunas_municipal if c in df_municipal.columns]
    cols_a = [c for c in colunas_acesso if c in df_acessibilidade_mun.columns]

    return pd.merge(
        df_municipal[cols_m],
        df_acessibilidade_mun[cols_a],
        on='cod_mun_ibge',
        how='inner',
    )
