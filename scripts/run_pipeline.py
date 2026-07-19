#!/usr/bin/env python3
"""
Pipeline completo: Desertos Médicos SUS.

Executa as 4 etapas do projeto (coleta → pré-processamento → análise E2SFCA → visualização)
a partir dos módulos src/, sem depender dos notebooks.

Uso:
    python scripts/run_pipeline.py            # pipeline completo (~645 mapas HTML)
    python scripts/run_pipeline.py --sample   # etapas 1-3 + mapas 1 e 3 apenas (~2 HTML)

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT
"""

import argparse
import sys
import time
from pathlib import Path

# Garantir que o projeto está no path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.config import (
    COMPETENCIA_DEFAULT,
    DATA_EXTERNAL,
    DATA_PROCESSED,
    OUTPUT_MAPAS,
    OUTPUT_RELATORIOS,
)


def _timestamp() -> str:
    return time.strftime("%H:%M:%S")


def etapa_1_coleta() -> None:
    """Coleta: download do ElastiCNES + filtragem de médicos."""
    from src.analysis import filtrar_medicos, deduplicar_medicos_por_local
    from src.data_loader import ElasticnesDownloader

    print(f"\n[{_timestamp()}] Etapa 1/4 — Coleta e exploração")
    print("-" * 60)

    downloader = ElasticnesDownloader(output_dir=DATA_EXTERNAL)
    df_profissionais = downloader.download_uf(
        uf="SP",
        competencia=COMPETENCIA_DEFAULT,
        force=False,
    )
    print(f"  Profissionais baixados: {len(df_profissionais):,}")

    df_medicos = filtrar_medicos(df_profissionais)
    print(f"  Vínculos de médicos: {len(df_medicos):,}")

    df_medicos_unicos = deduplicar_medicos_por_local(df_medicos)
    print(f"  Médicos únicos (CNS, CNES): {len(df_medicos_unicos):,}")

    out = DATA_PROCESSED / "medicos_sus_unicos.parquet"
    df_medicos_unicos.to_parquet(out, index=False)
    print(f"  Salvo: {out.name}")
    print("  OK")


def etapa_2_preprocessamento() -> None:
    """Pré-processamento: padronização, coordenadas, censo, agregação municipal."""
    from src.analysis import classificar_densidade_medica
    from src.geospatial import parse_location_wkt
    from src.preprocessing import (
        agregar_medicos_por_municipio,
        carregar_censo_sp,
        cruzar_medicos_populacao,
        padronizar_campos_medicos,
    )

    print(f"\n[{_timestamp()}] Etapa 2/4 — Pré-processamento")
    print("-" * 60)

    # Carregar médicos do passo anterior
    arquivo_medicos = DATA_PROCESSED / "medicos_sus_unicos.parquet"
    if not arquivo_medicos.exists():
        raise FileNotFoundError(
            f"{arquivo_medicos} não encontrado. Execute a Etapa 1 primeiro."
        )
    df_medicos = pd.read_parquet(arquivo_medicos)
    print(f"  Médicos únicos: {len(df_medicos):,}")

    # Padronizar campos
    df = padronizar_campos_medicos(df_medicos)

    # Extrair coordenadas do WKT
    df[['longitude', 'latitude']] = df['location'].apply(
        lambda x: pd.Series(parse_location_wkt(x))
    )
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')

    from src.config import BRAZIL_LAT_RANGE, BRAZIL_LON_RANGE
    mask_lat = df['latitude'].between(BRAZIL_LAT_RANGE[0], BRAZIL_LAT_RANGE[1])
    mask_lon = df['longitude'].between(BRAZIL_LON_RANGE[0], BRAZIL_LON_RANGE[1])
    df['coordenada_valida'] = mask_lat & mask_lon
    com_coords = df['coordenada_valida'].sum()
    print(f"  Coordenadas válidas: {com_coords:,} / {len(df):,}")

    # Carregar censo
    _gdf_censo, df_censo = carregar_censo_sp()
    print(f"  Setores censitários: {len(df_censo):,}")

    # Agregar médicos por município
    df_medicos_mun = agregar_medicos_por_municipio(df)
    print(f"  Municípios com médicos: {len(df_medicos_mun):,}")

    # Cruzar com população
    df_base = cruzar_medicos_populacao(df_medicos_mun, df_censo)
    print(f"  Base municipal: {len(df_base):,} municípios")

    # Salvar base municipal
    out_base = DATA_PROCESSED / "base_municipal_densidade_medica.parquet"
    df_base.to_parquet(out_base, index=False)
    print(f"  Salvo: {out_base.name}")

    # Salvar CSV
    out_csv = DATA_PROCESSED / "base_municipal_densidade_medica.csv"
    df_base.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"  Salvo: {out_csv.name}")

    # Salvar médicos com coordenadas
    df_medicos_geo = df[df['coordenada_valida']].copy()
    out_geo = DATA_PROCESSED / "medicos_sus_com_coordenadas.parquet"
    df_medicos_geo.to_parquet(out_geo, index=False)
    print(f"  Salvo: {out_geo.name} ({len(df_medicos_geo):,} registros)")

    print("  OK")


def etapa_3_analise() -> None:
    """Análise geoespacial: spatial join + E2SFCA + métricas legadas + comparação."""
    from src.analysis import (
        agregar_e2sfca_por_municipio,
        anexar_metricas_legadas,
        calcular_e2sfca,
        comparar_densidade_vs_e2sfca,
    )
    from src.geospatial import criar_geodataframe_pontos

    print(f"\n[{_timestamp()}] Etapa 3/4 — Análise E2SFCA")
    print("-" * 60)

    # Carregar dados
    arquivo_medicos_geo = DATA_PROCESSED / "medicos_sus_com_coordenadas.parquet"
    if not arquivo_medicos_geo.exists():
        raise FileNotFoundError(
            f"{arquivo_medicos_geo} não encontrado. Execute a Etapa 2 primeiro."
        )
    df_medicos = pd.read_parquet(arquivo_medicos_geo)
    print(f"  Médicos com coordenadas: {len(df_medicos):,}")

    # Carregar shapefile de setores
    shapefile_path = DATA_EXTERNAL / "SP_setores_CD2022_IBGE" / "SP_setores_CD2022.shp"
    if not shapefile_path.exists():
        raise FileNotFoundError(
            f"Shapefile não encontrado: {shapefile_path}\n"
            "Baixe de: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
        )
    gdf_setores = gpd.read_file(shapefile_path)
    print(f"  Setores censitários: {len(gdf_setores):,}")

    # Criar código IBGE 6 dígitos
    if 'cod_mun_ibge' not in gdf_setores.columns:
        gdf_setores['cod_mun_ibge'] = gdf_setores['CD_MUN'].astype(str).str[:6]

    # GeoDataFrame de médicos
    gdf_medicos = criar_geodataframe_pontos(
        df_medicos, coluna_lon='longitude', coluna_lat='latitude'
    )
    print(f"  CRS médicos: {gdf_medicos.crs}")

    # Unificar CRS
    if gdf_medicos.crs != gdf_setores.crs:
        gdf_medicos = gdf_medicos.to_crs(gdf_setores.crs)

    # Spatial join: médicos dentro dos setores
    print("  Spatial join (médicos ↔ setores)...")
    gdf_medicos_setor = gpd.sjoin(
        gdf_medicos,
        gdf_setores[['CD_SETOR', 'NM_MUN', 'geometry']],
        how='left',
        predicate='within',
    )
    if 'index_right' in gdf_medicos_setor.columns:
        gdf_medicos_setor = gdf_medicos_setor.drop(columns=['index_right'])
    medicos_com_setor = gdf_medicos_setor['CD_SETOR'].notna().sum()
    print(f"  Médicos associados a setores: {medicos_com_setor:,}")

    # Calcular E2SFCA
    print("  Calculando E2SFCA...")
    acessibilidade_por_setor = calcular_e2sfca(
        gdf_medicos_setor,
        gdf_setores,
        raio_captura_m=5000,
        beta=0.5,
        crs_projetado='EPSG:31983',
    )

    # Merge E2SFCA × shapefile (preserva geometria e colunas originais)
    print("  Integrando E2SFCA ao shapefile...")
    df_setores_com_e2sfca = gdf_setores.merge(
        acessibilidade_por_setor,
        on='CD_SETOR',
        how='left',
    )
    df_setores_com_e2sfca['acessibilidade_e2sfca'] = (
        df_setores_com_e2sfca['acessibilidade_e2sfca'].fillna(0)
    )
    df_setores_com_e2sfca['categoria_acesso'] = (
        df_setores_com_e2sfca['categoria_acesso'].fillna('6. Deserto médico (sem acesso)')
    )

    # Anexar métricas legadas (distância mínima, médicos no setor)
    print("  Calculando métricas legadas...")
    df_setores_com_e2sfca = anexar_metricas_legadas(
        df_setores_com_e2sfca, gdf_medicos_setor
    )
    print(f"  Setores com todas as métricas: {len(df_setores_com_e2sfca):,}")

    # Salvar setores com acessibilidade
    out_setores = DATA_PROCESSED / "setores_com_acessibilidade_real.parquet"
    df_setores_com_e2sfca.to_parquet(out_setores, index=False)
    print(f"  Salvo: {out_setores.name}")

    # CNES agregados (para mapas)
    cnes_agg = (
        gdf_medicos_setor
        .groupby(['cnes', 'municipio', 'nome_fantaia'])
        .agg(
            total_medicos=('profissional_cns', 'nunique'),
            latitude=('latitude', 'first'),
            longitude=('longitude', 'first'),
        )
        .reset_index()
    )
    out_cnes = DATA_PROCESSED / "cnes_agregados.parquet"
    cnes_agg.to_parquet(out_cnes, index=False)
    print(f"  Salvo: {out_cnes.name} ({len(cnes_agg):,} estabelecimentos)")

    # Base municipal para mapa coroplético
    arquivo_municipal = DATA_PROCESSED / "base_municipal_densidade_medica.parquet"
    if arquivo_municipal.exists():
        df_municipal = pd.read_parquet(arquivo_municipal)
        out_municipal = DATA_PROCESSED / "base_municipal_para_mapa.parquet"
        df_municipal.to_parquet(out_municipal, index=False)
        print(f"  Salvo: {out_municipal.name} ({len(df_municipal):,} municípios)")
    else:
        df_municipal = None

    # Comparação municipal vs E2SFCA
    if df_municipal is not None:
        print("  Agregando E2SFCA por município...")
        df_acessibilidade_mun = agregar_e2sfca_por_municipio(df_setores_com_e2sfca)
        df_comparacao = comparar_densidade_vs_e2sfca(df_municipal, df_acessibilidade_mun)
        out_comp = DATA_PROCESSED / "comparacao_municipal_vs_e2sfca.parquet"
        df_comparacao.to_parquet(out_comp, index=False)
        print(f"  Salvo: {out_comp.name} ({len(df_comparacao):,} municípios)")

    print("  OK")


def etapa_4_visualizacao(gerar_mapas_por_municipio: bool = True) -> None:
    """Visualização: gerar mapas HTML (MAPA 1-4)."""
    from src.visualization import (
        mapa_bivariado_municipal,
        mapa_bivariado_setorial_por_municipio,
        mapa_densidade_municipal,
        mapa_densidade_setorial_por_municipio,
    )

    print(f"\n[{_timestamp()}] Etapa 4/4 — Visualização")
    print("-" * 60)

    OUTPUT_MAPAS.mkdir(parents=True, exist_ok=True)
    OUTPUT_RELATORIOS.mkdir(parents=True, exist_ok=True)

    # Carregar dados processados
    df_municipal = pd.read_parquet(DATA_PROCESSED / "base_municipal_para_mapa.parquet")
    df_setores = pd.read_parquet(DATA_PROCESSED / "setores_com_acessibilidade_real.parquet")
    df_cnes = pd.read_parquet(DATA_PROCESSED / "cnes_agregados.parquet")

    arquivo_comparacao = DATA_PROCESSED / "comparacao_municipal_vs_e2sfca.parquet"
    df_comparacao = pd.read_parquet(arquivo_comparacao) if arquivo_comparacao.exists() else None

    # Shapefiles
    shapefile_mun = DATA_EXTERNAL / "SP_Municipios_2025" / "SP_Municipios_2025.shp"
    gdf_municipios = None
    if shapefile_mun.exists():
        gdf_municipios = gpd.read_file(shapefile_mun)
        gdf_municipios['cod_mun_6'] = gdf_municipios['CD_MUN'].astype(str).str[:6]
        print(f"  Shapefile municípios: {len(gdf_municipios):,} polígonos")

    shapefile_set = DATA_EXTERNAL / "SP_setores_CD2022_IBGE" / "SP_setores_CD2022.shp"
    gdf_setores_geo = None
    if shapefile_set.exists():
        gdf_setores_geo = gpd.read_file(shapefile_set)
        print(f"  Shapefile setores: {len(gdf_setores_geo):,} polígonos")

    # MAPA 1: Densidade médica por município (coroplético)
    if gdf_municipios is not None:
        out1 = OUTPUT_MAPAS / 'mapa_01_densidade_municipal.html'
        mapa_densidade_municipal(
            gdf_municipios=gdf_municipios,
            df_municipal=df_municipal,
            output_path=out1,
        )
        print(f"  MAPA 1 salvo: {out1.name}")
    else:
        print("  MAPA 1 pulado (shapefile de municípios não encontrado)")

    # MAPA 3: Bivariado municipal
    if gdf_municipios is not None and df_comparacao is not None:
        out3 = OUTPUT_MAPAS / 'mapa_03_bivariado_municipal.html'
        mapa_bivariado_municipal(
            gdf_municipios=gdf_municipios,
            df_comparacao=df_comparacao,
            output_path=out3,
        )
        print(f"  MAPA 3 salvo: {out3.name}")
    else:
        print("  MAPA 3 pulado (dados insuficientes)")

    if not gerar_mapas_por_municipio:
        print("\n  --sample ativo: MAPA 2 e MAPA 4 pulados")
        print("  OK")
        return

    # MAPA 2: Densidade populacional por município
    if gdf_setores_geo is not None:
        print("  Gerando MAPA 2 (~645 mapas)...")
        arquivos_2 = mapa_densidade_setorial_por_municipio(
            gdf_setores=gdf_setores_geo,
            df_setores=df_setores,
        )
        print(f"  MAPA 2: {len(arquivos_2)} mapas gerados")
    else:
        print("  MAPA 2 pulado (shapefile de setores não encontrado)")

    # MAPA 4: Bivariado setorial por município
    if gdf_setores_geo is not None:
        print("  Gerando MAPA 4 (~645 mapas)...")
        arquivos_4 = mapa_bivariado_setorial_por_municipio(
            gdf_setores=gdf_setores_geo,
            df_setores=df_setores,
        )
        print(f"  MAPA 4: {len(arquivos_4)} mapas gerados")
    else:
        print("  MAPA 4 pulado (shapefile de setores não encontrado)")

    print("  OK")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline completo: Desertos Médicos SUS",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Gera apenas MAPA 1 e MAPA 3 (~2 HTML). Pulam MAPA 2 e 4 (~1290 HTML).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("DESERTOS MÉDICOS SUS — Pipeline Completo")
    print("=" * 60)
    if args.sample:
        print("  Modo: --sample (mapas 2 e 4 pulados)")
    print(f"  Projeto: {PROJECT_ROOT}")

    t0 = time.time()

    etapa_1_coleta()
    etapa_2_preprocessamento()
    etapa_3_analise()
    etapa_4_visualizacao(gerar_mapas_por_municipio=not args.sample)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"Pipeline concluído em {elapsed:.1f}s")
    print(f"  Dados: {DATA_PROCESSED}")
    print(f"  Mapas: {OUTPUT_MAPAS}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
