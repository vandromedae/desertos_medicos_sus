"""
Testes unitários e de integração para o módulo E2SFCA.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.analysis.e2sfca import (
    classificar_e2sfca,
    calcular_percentis_e2sfca,
    peso_gaussiano,
    anexar_metricas_legadas,
    agregar_e2sfca_por_municipio,
    comparar_densidade_vs_e2sfca,
)
from src.validation.e2sfca import (
    calcular_e2sfca_manual,
    erro_relativo,
    sao_iguais,
)


# ============================================================
# Testes unitários: peso_gaussiano
# ============================================================

class TestPesoGaussiano:
    """Testes para a função de peso gaussiano."""

    def test_distancia_zero_retorna_um(self):
        assert peso_gaussiano(0) == 1.0

    def test_distancia_no_raio_retorna_zero(self):
        assert peso_gaussiano(5000) == 0.0

    def test_distancia_acima_do_raio_retorna_zero(self):
        assert peso_gaussiano(6000) == 0.0
        assert peso_gaussiano(10000) == 0.0

    def test_distancia_negativa_retorna_peso(self):
        # Distância negativa < raio → retorna peso (comportamento original do notebook)
        # exp(-0.5 * (-100/5000)²) ≈ 0.9998
        resultado = peso_gaussiano(-100)
        assert resultado > 0.99
        assert resultado < 1.0

    def test_valor_conhecido_meio_raio(self):
        # exp(-0.5 * (2500/5000)²) = exp(-0.5 * 0.25) = exp(-0.125)
        esperado = np.exp(-0.125)
        assert peso_gaussiano(2500) == pytest.approx(esperado, rel=1e-10)

    def test_valor_conhecido_90_percento_raio(self):
        # exp(-0.5 * (4500/5000)²) = exp(-0.5 * 0.81) = exp(-0.405)
        esperado = np.exp(-0.405)
        assert peso_gaussiano(4500) == pytest.approx(esperado, rel=1e-10)

    def test_beta_diferente(self):
        # exp(-1.0 * (2500/5000)²) = exp(-0.25)
        esperado = np.exp(-0.25)
        assert peso_gaussiano(2500, beta=1.0) == pytest.approx(esperado, rel=1e-10)

    def test_raio_diferente(self):
        # Raio 10000, distância 5000: exp(-0.5 * (5000/10000)²) = exp(-0.125)
        esperado = np.exp(-0.125)
        assert peso_gaussiano(5000, raio_m=10000) == pytest.approx(esperado, rel=1e-10)

    def test_raio_diferente_no_limite(self):
        assert peso_gaussiano(10000, raio_m=10000) == 0.0


# ============================================================
# Testes unitários: classificar_e2sfca
# ============================================================

class TestClassificarE2sfca:
    """Testes para a classificação E2SFCA."""

    PERCENTIS_PADRAO = (0.1, 0.5, 1.0, 2.0, 3.0)

    def test_deserto_medico(self):
        assert classificar_e2sfca(0, self.PERCENTIS_PADRAO) == '6. Deserto médico (sem acesso)'

    def test_critico(self):
        # 0 < valor < p5 (0.1)
        assert classificar_e2sfca(0.05, self.PERCENTIS_PADRAO) == '5. Crítico (acesso muito baixo)'

    def test_limitado(self):
        # p5 (0.1) <= valor < p25 (0.5)
        assert classificar_e2sfca(0.3, self.PERCENTIS_PADRAO) == '4. Limitado (acesso baixo)'

    def test_moderado(self):
        # p25 (0.5) <= valor < p50 (1.0)
        assert classificar_e2sfca(0.7, self.PERCENTIS_PADRAO) == '3. Moderado (acesso médio)'

    def test_bom(self):
        # p50 (1.0) <= valor < p75 (2.0)
        assert classificar_e2sfca(1.5, self.PERCENTIS_PADRAO) == '2. Bom (acesso alto)'

    def test_excelente(self):
        # valor >= p75 (2.0)
        assert classificar_e2sfca(2.5, self.PERCENTIS_PADRAO) == '1. Excelente (acesso muito alto)'
        assert classificar_e2sfca(10.0, self.PERCENTIS_PADRAO) == '1. Excelente (acesso muito alto)'

    def test_limite_exato_p5(self):
        # valor == p5 → categorizado como Limitado (elif valor < p25)
        assert classificar_e2sfca(0.1, self.PERCENTIS_PADRAO) == '4. Limitado (acesso baixo)'

    def test_limite_exato_p75(self):
        # valor == p75 → Excellent (not < p75)
        assert classificar_e2sfca(2.0, self.PERCENTIS_PADRAO) == '1. Excelente (acesso muito alto)'


# ============================================================
# Testes unitários: calcular_percentis_e2sfca
# ============================================================

class TestCalcularPercentisE2sfca:
    """Testes para cálculo de percentis E2SFCA."""

    def test_valores_conhecidos(self):
        serie = pd.Series([0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        p5, p25, p50, p75, p90 = calcular_percentis_e2sfca(serie)
        # Apenas valores > 0: [1,2,3,4,5,6,7,8,9,10]
        assert p5 == pytest.approx(1.45, abs=0.1)
        assert p50 == pytest.approx(5.5, abs=0.1)

    def test_todos_zeros(self):
        serie = pd.Series([0, 0, 0])
        p5, p25, p50, p75, p90 = calcular_percentis_e2sfca(serie)
        assert p5 == 0.0
        assert p90 == 0.0

    def test_todos_positivos(self):
        serie = pd.Series([1, 2, 3, 4, 5])
        p5, p25, p50, p75, p90 = calcular_percentis_e2sfca(serie)
        assert p50 == pytest.approx(3.0, abs=0.1)


# ============================================================
# Testes unitários: sao_iguais e erro_relativo
# ============================================================

class TestSaoIguais:
    """Testes para comparação com tolerância."""

    def test_valores_identicos(self):
        assert sao_iguais(1.0, 1.0) is True

    def test_dentro_tolerancia(self):
        # diff = 1e-10, threshold = 1e-9 + 1e-4 * 1.0 ≈ 1e-4
        assert sao_iguais(1.0, 1.0 + 1e-10) is True

    def test_fora_tolerancia(self):
        assert sao_iguais(1.0, 2.0) is False

    def test_zero_vs_zero(self):
        assert sao_iguais(0.0, 0.0) is True

    def test_zero_vs_nao_zero(self):
        assert sao_iguais(0.0, 1.0) is False

    def test_nan_vs_nan(self):
        assert sao_iguais(float('nan'), float('nan')) is True

    def test_nan_vs_numero(self):
        assert sao_iguais(float('nan'), 1.0) is False


class TestErroRelativo:
    """Testes para cálculo de erro relativo."""

    def test_valores_identicos(self):
        assert erro_relativo(1.0, 1.0) == 0.0

    def test_diferenca_conhecida(self):
        # |1.0 - 1.5| / 1.5 * 100 = 33.33%
        assert erro_relativo(1.0, 1.5) == pytest.approx(33.33, abs=0.01)

    def test_divisao_por_zero(self):
        assert erro_relativo(1.0, 0.0) == float('inf')

    def test_zero_vs_zero(self):
        assert erro_relativo(0.0, 0.0) == 0.0


# ============================================================
# Teste de integração: validação 100 setores
# ============================================================

class TestIntegracaoE2SFCA:
    """Testes que dependem dos dados reais do projeto."""

    @pytest.fixture(autouse=False)
    def load_data(self):
        """Carrega dados necessários para testes de integração."""
        from src.config import DATA_EXTERNAL, DATA_PROCESSED

        parquet_path = DATA_PROCESSED / "setores_com_acessibilidade_real.parquet"
        shapefile_path = DATA_EXTERNAL / "SP_setores_CD2022_IBGE" / "SP_setores_CD2022.shp"
        medicos_path = DATA_PROCESSED / "medicos_associados_setores_real.parquet"

        if not all(p.exists() for p in [parquet_path, shapefile_path, medicos_path]):
            pytest.skip("Dados de integração não disponíveis")

        import geopandas as gpd

        df_e2sfca = pd.read_parquet(parquet_path)
        gdf_setores = gpd.read_file(shapefile_path)
        gdf_medicos = gpd.read_parquet(medicos_path)

        return df_e2sfca, gdf_setores, gdf_medicos

    def test_validacao_100_setores(self, load_data):
        """Validação completa: 100 setores recalculados manualmente devem bater 100%."""
        from src.validation.e2sfca import validar_e2sfca_100_setores

        df_e2sfca, gdf_setores, gdf_medicos = load_data
        df_resultados = validar_e2sfca_100_setores(
            df_e2sfca, gdf_setores, gdf_medicos, n_setores=100
        )

        # Todos devem passar
        assert df_resultados['passou'].all(), (
            f"Falhou: {df_resultados[~df_resultados['passou']]['cd_setor'].tolist()}"
        )
        assert len(df_resultados) == 100


# ============================================================
# Testes unitários: anexar_metricas_legadas
# ============================================================

class TestAnexarMetricasLegadas:
    """Testes para a função anexar_metricas_legadas."""

    @pytest.fixture()
    def df_e2sfca(self):
        """DataFrame E2SFCA com 3 setores."""
        return pd.DataFrame({
            'CD_SETOR': ['S1', 'S2', 'S3'],
            'NM_MUN': ['MunA', 'MunA', 'MunB'],
            'v0001': [100, 200, 150],
            'acessibilidade_e2sfca': [0.01, 0.0, 0.05],
            'categoria_acesso': [
                '2. Bom (acesso alto)',
                '6. Deserto médico (sem acesso)',
                '1. Excelente (acesso muito alto)',
            ],
            'geometry': [
                Point(-46.6, -23.5),
                Point(-46.7, -23.6),
                Point(-47.0, -23.0),
            ],
        })

    @pytest.fixture()
    def gdf_medicos_setor(self):
        """GeoDataFrame de médicos com 4 registros: 2 em S1, 1 em S2, 1 em S3."""
        return gpd.GeoDataFrame({
            'CD_SETOR': ['S1', 'S1', 'S2', 'S3'],
            'profissional_cns': ['CNS1', 'CNS2', 'CNS3', 'CNS4'],
            'cnes': ['CNES1', 'CNES1', 'CNES2', 'CNES3'],
            'municipio': ['MunA', 'MunA', 'MunA', 'MunB'],
            'nome_fantaia': ['Ubs1', 'Ubs1', 'Ubs2', 'Ubs3'],
            'latitude': [-23.5, -23.5, -23.6, -23.0],
            'longitude': [-46.6, -46.6, -46.7, -47.0],
            'geometry': [
                Point(-46.6, -23.5),
                Point(-46.6, -23.5),
                Point(-46.7, -23.6),
                Point(-47.0, -23.0),
            ],
        }, crs='EPSG:4326')

    def test_medicos_dentro_por_setor(self, df_e2sfca, gdf_medicos_setor):
        """Médicos dentro do setor: S1=2, S2=1, S3=1."""
        result = anexar_metricas_legadas(df_e2sfca, gdf_medicos_setor)
        expected = [2, 1, 1]
        assert result['total_medicos_dentro'].tolist() == expected

    def test_cnes_dentro_por_setor(self, df_e2sfca, gdf_medicos_setor):
        """CNES dentro do setor: S1=1 (mesmo CNES), S2=1, S3=1."""
        result = anexar_metricas_legadas(df_e2sfca, gdf_medicos_setor)
        expected = [1, 1, 1]
        assert result['total_cnes_dentro'].tolist() == expected

    def test_dist_minima_zero_para_ponto_no_setor(self, df_e2sfca, gdf_medicos_setor):
        """Médico no mesmo ponto do setor → distância ~0."""
        result = anexar_metricas_legadas(df_e2sfca, gdf_medicos_setor)
        # S1 tem médico no mesmo ponto → dist = 0
        assert result.loc[result['CD_SETOR'] == 'S1', 'dist_minima_metros'].values[0] == pytest.approx(0.0, abs=1.0)

    def test_colunas_presentes(self, df_e2sfca, gdf_medicos_setor):
        """Saída deve conter as 3 colunas novas."""
        result = anexar_metricas_legadas(df_e2sfca, gdf_medicos_setor)
        assert 'dist_minima_metros' in result.columns
        assert 'total_medicos_dentro' in result.columns
        assert 'total_cnes_dentro' in result.columns

    def test_sem_geometry_fallback(self, gdf_medicos_setor):
        """DataFrame sem coluna geometry → dist_minima_metros = 99999."""
        df = pd.DataFrame({
            'CD_SETOR': ['S1', 'S2'],
            'acessibilidade_e2sfca': [0.01, 0.0],
            'categoria_acesso': ['2. Bom', '6. Deserto'],
        })
        result = anexar_metricas_legadas(df, gdf_medicos_setor)
        assert (result['dist_minima_metros'] == 99999).all()
        assert 'total_medicos_dentro' in result.columns


# ============================================================
# Testes unitários: agregar_e2sfca_por_municipio
# ============================================================

class TestAgregarE2sfcaPorMunicipio:
    """Testes para a função agregar_e2sfca_por_municipio."""

    @pytest.fixture()
    def df_setores(self):
        """6 setores em 2 municípios com categorias variadas."""
        return pd.DataFrame({
            'CD_SETOR': ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'],
            'cod_mun_ibge': ['350001', '350001', '350001', '350002', '350002', '350002'],
            'v0001': [100, 200, 300, 400, 500, 600],
            'acessibilidade_e2sfca': [0.01, 0.02, 0.0, 0.05, 0.03, 0.0],
            'categoria_acesso': [
                '2. Bom (acesso alto)',
                '3. Moderado (acesso médio)',
                '6. Deserto médico (sem acesso)',
                '1. Excelente (acesso muito alto)',
                '2. Bom (acesso alto)',
                '6. Deserto médico (sem acesso)',
            ],
            'dist_minima_metros': [500, 1000, 99999, 200, 800, 99999],
            'total_medicos_dentro': [3, 1, 0, 5, 2, 0],
            'total_cnes_dentro': [2, 1, 0, 3, 1, 0],
        })

    def test_num_setores(self, df_setores):
        """3 setores por município."""
        result = agregar_e2sfca_por_municipio(df_setores)
        assert result.set_index('cod_mun_ibge').loc['350001', 'num_setores'] == 3
        assert result.set_index('cod_mun_ibge').loc['350002', 'num_setores'] == 3

    def test_populacao_setorial(self, df_setores):
        """Soma de v0001 por município."""
        result = agregar_e2sfca_por_municipio(df_setores)
        row = result.set_index('cod_mun_ibge').loc['350001']
        assert row['populacao_setorial'] == 600  # 100+200+300

    def test_pct_setores_deserto(self, df_setores):
        """Município 350001: 1 de 3 em deserto → 33.3%."""
        result = agregar_e2sfca_por_municipio(df_setores)
        row = result.set_index('cod_mun_ibge').loc['350001']
        assert row['pct_setores_deserto'] == pytest.approx(33.3, abs=0.1)

    def test_pct_acesso_baixo(self, df_setores):
        """350001: deserto(1) + crítico(0) + limitado(0) = 1/3 → 33.3%.
        350002: deserto(1) + crítico(0) + limitado(0) = 1/3 → 33.3%."""
        result = agregar_e2sfca_por_municipio(df_setores)
        assert result.set_index('cod_mun_ibge').loc['350001', 'pct_acesso_baixo'] == pytest.approx(33.3, abs=0.1)
        assert result.set_index('cod_mun_ibge').loc['350002', 'pct_acesso_baixo'] == pytest.approx(33.3, abs=0.1)

    def test_medicos_dentro_setor_soma(self, df_setores):
        """Soma de total_medicos_dentro por município."""
        result = agregar_e2sfca_por_municipio(df_setores)
        assert result.set_index('cod_mun_ibge').loc['350001', 'medicos_dentro_setor'] == 4  # 3+1+0
        assert result.set_index('cod_mun_ibge').loc['350002', 'medicos_dentro_setor'] == 7  # 5+2+0

    def test_todos_deserto_pct_100(self):
        """Município com todos os setores em deserto → pct = 100%."""
        df = pd.DataFrame({
            'CD_SETOR': ['S1', 'S2'],
            'cod_mun_ibge': ['350099', '350099'],
            'v0001': [100, 200],
            'acessibilidade_e2sfca': [0.0, 0.0],
            'categoria_acesso': [
                '6. Deserto médico (sem acesso)',
                '6. Deserto médico (sem acesso)',
            ],
            'dist_minima_metros': [99999, 99999],
            'total_medicos_dentro': [0, 0],
            'total_cnes_dentro': [0, 0],
        })
        result = agregar_e2sfca_por_municipio(df)
        assert result['pct_setores_deserto'].values[0] == 100.0

    def test_distancia_km(self, df_setores):
        """dist_media_km = dist_media / 1000, arredondado para 2 casas."""
        result = agregar_e2sfca_por_municipio(df_setores)
        row = result.set_index('cod_mun_ibge').loc['350001']
        # dist_media = (500 + 1000 + 99999) / 3 = 33833.0
        assert row['dist_media_km'] == pytest.approx(33.83, abs=0.01)


# ============================================================
# Testes unitários: comparar_densidade_vs_e2sfca
# ============================================================

class TestCompararDensidadeVsE2sfca:
    """Testes para a função comparar_densidade_vs_e2sfca."""

    @pytest.fixture()
    def df_municipal(self):
        """Base municipal com 3 municípios."""
        return pd.DataFrame({
            'cod_mun_ibge': ['350001', '350002', '350003'],
            'nm_mun': ['MunA', 'MunB', 'MunC'],
            'total_medicos': [10, 20, 5],
            'populacao': [50000, 100000, 20000],
            'medicos_por_1k': [0.20, 0.20, 0.25],
            'categoria_densidade': ['1. Crítico (<1,0)', '1. Crítico (<1,0)', '1. Crítico (<1,0)'],
        })

    @pytest.fixture()
    def df_acessibilidade(self):
        """Acessibilidade agregada com 2 municípios (350003 ausente)."""
        return pd.DataFrame({
            'cod_mun_ibge': ['350001', '350002'],
            'num_setores': [100, 200],
            'acessibilidade_e2sfca_media': [0.005, 0.008],
            'pct_setores_deserto': [10.0, 5.0],
            'pct_acesso_baixo': [30.0, 15.0],
            'medicos_dentro_setor': [8, 18],
        })

    def test_inner_join(self, df_municipal, df_acessibilidade):
        """Inner join: 350003 não tem correspondência → excluído."""
        result = comparar_densidade_vs_e2sfca(df_municipal, df_acessibilidade)
        assert len(result) == 2
        assert '350003' not in result['cod_mun_ibge'].values

    def test_colunas_preservadas(self, df_municipal, df_acessibilidade):
        """Colunas de ambas as bases presentes no resultado."""
        result = comparar_densidade_vs_e2sfca(df_municipal, df_acessibilidade)
        assert 'nm_mun' in result.columns  # do municipal
        assert 'acessibilidade_e2sfca_media' in result.columns  # da acessibilidade

    def test_valores_corretos(self, df_municipal, df_acessibilidade):
        """Valores de 350001 preservados corretamente."""
        result = comparar_densidade_vs_e2sfca(df_municipal, df_acessibilidade)
        row = result.set_index('cod_mun_ibge').loc['350001']
        assert row['nm_mun'] == 'MunA'
        assert row['acessibilidade_e2sfca_media'] == pytest.approx(0.005)
        assert row['pct_setores_deserto'] == pytest.approx(10.0)

    def test_municipio_sem_correspondencia(self, df_municipal, df_acessibilidade):
        """Município 350003 (sem acessibilidade) não aparece no resultado."""
        result = comparar_densidade_vs_e2sfca(df_municipal, df_acessibilidade)
        assert 350003 not in result['cod_mun_ibge'].astype(int).values
