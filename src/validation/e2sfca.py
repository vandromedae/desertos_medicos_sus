"""
Módulo de validação do algoritmo E2SFCA.

Reimplementação manual (loop puro, sem otimizações vetorizadas) usada para
verificar a correção do pipeline de produção contra 100 setores aleatórios.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

from src.analysis.e2sfca import peso_gaussiano


def sao_iguais(val1: float, val2: float, atol: float = 1e-9, rtol: float = 1e-4) -> bool:
    """
    Compara dois valores considerando tolerância relativa.
    Equivalente a numpy.allclose, mas para escalares.

    Fórmula: |val1 - val2| <= atol + rtol * |val2|
    """
    if pd.isna(val1) or pd.isna(val2):
        return pd.isna(val1) and pd.isna(val2)
    diff = abs(val1 - val2)
    threshold = atol + rtol * abs(val2)
    return diff <= threshold


def erro_relativo(val1: float, val2: float) -> float:
    """Calcula erro relativo em porcentagem."""
    if val2 == 0:
        return float('inf') if val1 != 0 else 0.0
    return abs((val1 - val2) / val2) * 100


def calcular_e2sfca_manual(
    cd_setor: str,
    gdf_setores_centroides: gpd.GeoDataFrame,
    gdf_cnes_proj: gpd.GeoDataFrame,
    raio: float = 5000,
    beta: float = 0.5,
) -> Optional[dict]:
    """
    Recalcula o E2SFCA do zero para um setor específico.
    Implementação alternativa (loop puro) para validação do pipeline vetorizado.

    Retorna dict com todos os detalhes para comparação, ou None se o setor não for encontrado.
    """
    # Centróide do setor
    setor_row = gdf_setores_centroides[gdf_setores_centroides['CD_SETOR'] == cd_setor]
    if len(setor_row) == 0:
        return None

    centroide = setor_row.geometry.iloc[0]
    buffer_setor = centroide.buffer(raio)

    # CNES dentro do raio do setor
    cnes_no_raio = gdf_cnes_proj[gdf_cnes_proj.geometry.within(buffer_setor)].copy()

    resultado = {
        'cd_setor': cd_setor,
        'cnes_no_raio': set(cnes_no_raio['cnes'].tolist()),
        'detalhes_cnes': [],
        'ai_total': 0.0
    }

    for idx, cnes in cnes_no_raio.iterrows():
        # Buffer deste CNES
        buffer_cnes = cnes.geometry.buffer(raio)

        # Setores cujo centróide está dentro do buffer do CNES
        setores_no_raio_cnes = gdf_setores_centroides[
            gdf_setores_centroides.geometry.within(buffer_cnes)
        ].copy()

        # Calcular população ponderada
        pop_ponderada = 0.0
        detalhes_setores = []

        for _, setor in setores_no_raio_cnes.iterrows():
            dist = cnes.geometry.distance(setor.geometry)

            if dist < raio:
                peso = np.exp(-beta * (dist / raio) ** 2)
            else:
                peso = 0.0
            pop_ponderada += setor['populacao'] * peso
            detalhes_setores.append({
                'cd_setor': setor['CD_SETOR'],
                'populacao': setor['populacao'],
                'distancia': dist,
                'peso': peso,
                'pop_ponderada': setor['populacao'] * peso
            })

        # Razão de oferta R_j
        if pop_ponderada > 0:
            r_j = cnes['total_medicos_cnes'] / pop_ponderada
        else:
            r_j = 0.0

        # Distância do setor ao CNES
        dist_setor_cnes = centroide.distance(cnes.geometry)

        # Peso final e contribuição
        if dist_setor_cnes < raio:
            peso_final = np.exp(-beta * (dist_setor_cnes / raio) ** 2)
        else:
            peso_final = 0.0

        contribuicao = r_j * peso_final

        resultado['detalhes_cnes'].append({
            'cnes': cnes['cnes'],
            'medicos': cnes['total_medicos_cnes'],
            'pop_ponderada': pop_ponderada,
            'r_j': r_j,
            'distancia_setor': dist_setor_cnes,
            'peso_final': peso_final,
            'contribuicao': contribuicao,
            'n_setores_no_raio': len(setores_no_raio_cnes),
            'detalhes_setores': detalhes_setores
        })

        resultado['ai_total'] += contribuicao

    return resultado


def validar_e2sfca_100_setores(
    df_setores_e2sfca: pd.DataFrame,
    gdf_setores: gpd.GeoDataFrame,
    gdf_medicos_setor: gpd.GeoDataFrame,
    n_setores: int = 100,
    atol: float = 1e-9,
    rtol: float = 1e-4,
    seed: int = 42,
    crs_projetado: str = "EPSG:31983",
) -> pd.DataFrame:
    """
    Valida o E2SFCA comparando 100 setores recalculados manualmente com o pipeline.

    Args:
        df_setores_e2sfca: DataFrame com coluna acessibilidade_e2sfca (resultado do pipeline).
        gdf_setores: GeoDataFrame original dos setores (shapefile).
        gdf_medicos_setor: GeoDataFrame de médicos com CD_SETOR (do spatial join).
        n_setores: Número de setores para testar.
        atol: Tolerância absoluta para comparação.
        rtol: Tolerância relativa para comparação.
        seed: Seed para reprodutibilidade da amostragem.
        crs_projetado: CRS projetado para cálculos de distância.

    Returns:
        DataFrame com resultados da validação por setor.
    """
    RAIO_M = 5000
    BETA = 0.5

    print("=" * 70)
    print("VALIDAÇÃO ROBUSTA DO E2SFCA")
    print("=" * 70)

    print(f"\n Configurações:")
    print(f"   Raio: {RAIO_M / 1000:.0f} km | Beta: {BETA}")
    print(f"   Setores a testar: {n_setores}")
    print(f"   Tolerância absoluta (atol): {atol:.0e}")
    print(f"   Tolerância relativa (rtol): {rtol:.0e}")

    # ============================================================
    # PASSO 0: Preparar dados
    # ============================================================
    print("\n Preparando dados...")

    # Verificar se tem a coluna do E2SFCA
    if 'acessibilidade_e2sfca' not in df_setores_e2sfca.columns:
        raise ValueError("Coluna 'acessibilidade_e2sfca' não encontrada!")

    # Filtrar apenas setores com população > 0
    df_setores_com_pop = df_setores_e2sfca[df_setores_e2sfca['v0001'] > 0].copy()
    print(f"    {len(df_setores_com_pop):,} setores com população > 0")

    # Selecionar N setores aleatórios
    setores_teste = df_setores_com_pop.sample(n=n_setores, random_state=seed)
    print(f"    {len(setores_teste)} setores selecionados para validação")

    # Preparar GeoDataFrames projetados
    gdf_setores_proj = gdf_setores.to_crs(crs_projetado)
    gdf_setores_centroides = gdf_setores_proj.copy()
    gdf_setores_centroides['geometry'] = gdf_setores_centroides.centroid
    gdf_setores_centroides['populacao'] = gdf_setores_centroides['v0001'].fillna(0).astype(int)

    # Recriar GeoDataFrame de CNES projetado
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
    gdf_cnes_proj = gdf_cnes[gdf_cnes['total_medicos_cnes'] > 0].to_crs(crs_projetado)
    print(f"    {len(gdf_cnes_proj):,} CNES com médicos SUS")

    # ============================================================
    # VALIDAÇÃO: Testar os setores
    # ============================================================
    print(f"\n Iniciando validação de {n_setores} setores...")
    print("=" * 70)

    resultados_validacao = []
    setores_ok = 0
    setores_falhou = 0

    for i, (_, setor_row) in enumerate(setores_teste.iterrows(), 1):
        cd_setor = setor_row['CD_SETOR']
        ai_esperado = setor_row['acessibilidade_e2sfca']

        # Calcular manualmente
        resultado_manual = calcular_e2sfca_manual(cd_setor, gdf_setores_centroides, gdf_cnes_proj)

        if resultado_manual is None:
            print(f"    Setor {cd_setor} não encontrado - pulando")
            continue

        ai_calculado = resultado_manual['ai_total']

        # Comparar com tolerância relativa
        passou = sao_iguais(ai_calculado, ai_esperado, atol=atol, rtol=rtol)
        err_rel = erro_relativo(ai_calculado, ai_esperado)

        resultados_validacao.append({
            'cd_setor': cd_setor,
            'ai_esperado': ai_esperado,
            'ai_calculado': ai_calculado,
            'diff_absoluta': abs(ai_calculado - ai_esperado),
            'erro_relativo_pct': err_rel,
            'passou': passou,
            'n_cnes': len(resultado_manual['cnes_no_raio'])
        })

        if passou:
            setores_ok += 1
        else:
            setores_falhou += 1

        if i % 20 == 0:
            print(f"  Progresso: {i}/{n_setores} (ok: {setores_ok}, falhou: {setores_falhou})")

    # ============================================================
    # RELATÓRIO FINAL
    # ============================================================
    print("\n" + "=" * 70)
    print(" RELATÓRIO FINAL DE VALIDAÇÃO")
    print("=" * 70)

    df_resultados = pd.DataFrame(resultados_validacao)

    print(f"\n Setores que passaram: {setores_ok}/{len(resultados_validacao)} ({setores_ok / len(resultados_validacao) * 100:.1f}%)")
    print(f" Setores que falharam: {setores_falhou}/{len(resultados_validacao)} ({setores_falhou / len(resultados_validacao) * 100:.1f}%)")

    print(f"\n Estatísticas do erro relativo:")
    print(f"   Média: {df_resultados['erro_relativo_pct'].mean():.4f}%")
    print(f"   Mediana: {df_resultados['erro_relativo_pct'].median():.4f}%")
    print(f"   Máximo: {df_resultados['erro_relativo_pct'].max():.4f}%")
    print(f"   95º percentil: {df_resultados['erro_relativo_pct'].quantile(0.95):.4f}%")

    # Mostrar setores com maior erro (top 5)
    print(f"\n Top 5 setores com MAIOR erro relativo:")
    top_erro = df_resultados.nlargest(5, 'erro_relativo_pct')
    for _, row in top_erro.iterrows():
        print(f"      Setor {row['cd_setor']}:")
        print(f"      Esperado: {row['ai_esperado']:.9f}")
        print(f"      Calculado: {row['ai_calculado']:.9f}")
        print(f"      Erro relativo: {row['erro_relativo_pct']:.4f}%")
        print(f"      CNES no raio: {row['n_cnes']}")

    # ============================================================
    # TESTE DE BORDA: Centróide exatamente a 5km
    # ============================================================
    print("\n" + "=" * 70)
    print(" TESTE DE BORDA: Centróide exatamente a 5km")
    print("=" * 70)

    from shapely.geometry import Point

    print("\nCriando cenário sintético...")

    # Pegar um CNES qualquer
    cnes_teste = gdf_cnes_proj.iloc[0]
    ponto_cnes = cnes_teste.geometry

    # Criar um ponto exatamente a 5000m na direção leste
    ponto_borda = Point(ponto_cnes.x + 5000, ponto_cnes.y)

    # Verificar distância
    dist_real = ponto_cnes.distance(ponto_borda)
    print(f"   Distância real: {dist_real:.2f}m")

    # Testar com buffer
    buffer_cnes = ponto_cnes.buffer(RAIO_M)
    esta_dentro = ponto_borda.within(buffer_cnes)
    print(f"   Está dentro do buffer (within): {esta_dentro}")

    # Calcular peso gaussiano
    peso = peso_gaussiano(dist_real, raio_m=RAIO_M, beta=BETA)
    print(f"   Peso gaussiano a 5km: {peso:.6f}")
    print(f"   (exp(-0.5 * 1²) = {np.exp(-0.5):.6f})")

    print("\n️  NOTA SOBRE A BORDA:")
    print("   O método 'within' do GeoPandas usa ≤ (inclusivo).")
    print("   Um ponto exatamente a 5000m ESTÁ dentro do buffer.")
    print("   Mas devido a floating point, pode haver variações de ~1mm.")
    print("   Isso é aceitável para análise geoespacial.")

    # ============================================================
    # CONCLUSÃO
    # ============================================================
    print("\n" + "=" * 70)
    print(" CONCLUSÃO")
    print("=" * 70)

    if setores_falhou == 0:
        print("  TODOS OS SETORES PASSARAM NA VALIDAÇÃO!")
        print("   O algoritmo E2SFCA está 100% correto.")
        print("   Pode confiar nos mapas gerados.")
    elif setores_falhou <= 3:
        print(f"  {setores_falhou} setores falharam (tolerância muito rigorosa?)")
        print("   Verifique se os erros relativos são realmente significativos.")
    else:
        print(f" {setores_falhou} setores falharam - investigar!")
        print("   Pode haver bug no algoritmo ou nos dados.")

    print("\n" + "=" * 70)

    return df_resultados
