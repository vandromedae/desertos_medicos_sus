"""
Testes unitários para o módulo de pré-processamento.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from src.preprocessing import (
    agregar_medicos_por_municipio,
    cruzar_medicos_populacao,
    padronizar_campos_medicos,
)


class TestPadronizarCamposMedicos:
    """Testes para padronizar_campos_medicos."""

    def test_cnes_zfill(self):
        df = pd.DataFrame({
            "cnes": ["123", "12345678", "  0001234  "],
            "municipio": ["são paulo", "Campinas", "  Ribeirão Preto  "],
            "uf": ["sp", "SP", "  Sp  "],
            "profissional_cns": ["12345", " 67890 ", "11111"],
            "ibge": ["3550308", "3509502", "3543402"],
        })
        result = padronizar_campos_medicos(df)

        assert result["cnes"].iloc[0] == "0000123"
        assert result["cnes"].iloc[1] == "12345678"  # zfill(7) only pads shorter strings
        assert result["municipio"].iloc[0] == "SÃO PAULO"
        assert result["uf"].iloc[0] == "SP"
        assert result["cod_mun_ibge"].iloc[0] == "3550308"

    def test_no_ibge_column(self):
        df = pd.DataFrame({
            "cnes": ["1234567"],
            "municipio": ["Teste"],
            "uf": ["SP"],
            "profissional_cns": ["12345"],
        })
        result = padronizar_campos_medicos(df)
        assert result["cod_mun_ibge"].iloc[0] is None

    def test_does_not_modify_original(self):
        df = pd.DataFrame({
            "cnes": ["123"],
            "municipio": ["teste"],
            "uf": ["sp"],
            "profissional_cns": ["12345"],
            "ibge": ["3550308"],
        })
        _ = padronizar_campos_medicos(df)
        assert df["cnes"].iloc[0] == "123"


class TestAgregarMedicosPorMunicipio:
    """Testes para agregar_medicos_por_municipio."""

    def test_basic_aggregation(self):
        df = pd.DataFrame({
            "cod_mun_ibge": ["3550308", "3550308", "3509502"],
            "municipio": ["SÃO PAULO", "SÃO PAULO", "CAMPINAS"],
            "uf": ["SP", "SP", "SP"],
            "profissional_cns": ["111", "222", "333"],
            "cnes": ["A", "A", "B"],
        })
        result = agregar_medicos_por_municipio(df)
        assert len(result) == 2
        sp_row = result[result["cod_mun_ibge"] == "3550308"].iloc[0]
        assert sp_row["total_medicos"] == 2
        assert sp_row["total_cnes"] == 1
        assert sp_row["total_vinculos"] == 2

    def test_empty_dataframe(self):
        df = pd.DataFrame({
            "cod_mun_ibge": pd.Series(dtype="str"),
            "municipio": pd.Series(dtype="str"),
            "uf": pd.Series(dtype="str"),
            "profissional_cns": pd.Series(dtype="str"),
            "cnes": pd.Series(dtype="str"),
        })
        result = agregar_medicos_por_municipio(df)
        assert len(result) == 0


class TestCruzarMedicosPopulacao:
    """Testes para cruzar_medicos_populacao."""

    @pytest.fixture
    def sample_medicos_mun(self):
        return pd.DataFrame({
            "cod_mun_ibge": ["3550308", "3509502"],
            "municipio": ["SÃO PAULO", "CAMPINAS"],
            "uf": ["SP", "SP"],
            "total_medicos": [100, 20],
            "total_cnes": [50, 15],
            "total_vinculos": [120, 25],
        })

    @pytest.fixture
    def sample_censo(self):
        return pd.DataFrame({
            "CD_SETOR": ["001", "002", "003"],
            "CD_MUN": ["3550308001", "3550308002", "3509502001"],
            "NM_MUN": ["SÃO PAULO", "SÃO PAULO", "CAMPINAS"],
            "v0001": [1000, 2000, 3000],
            "AREA_KM2": [1.5, 2.0, 3.0],
            "cod_mun_ibge": ["3550308", "3550308", "3509502"],
        })

    def test_basic_cross(self, sample_medicos_mun, sample_censo):
        result = cruzar_medicos_populacao(sample_medicos_mun, sample_censo)
        assert len(result) == 2
        assert "medicos_por_1k" in result.columns
        assert "categoria_densidade" in result.columns
        assert "uf" in result.columns

    def test_density_calculation(self, sample_medicos_mun, sample_censo):
        result = cruzar_medicos_populacao(sample_medicos_mun, sample_censo)
        sp_row = result[result["cod_mun_ibge"] == "3550308"].iloc[0]
        expected_density = round(100 / 3000 * 1000, 2)
        assert sp_row["medicos_por_1k"] == expected_density

    def test_municipality_without_doctors(self):
        med = pd.DataFrame({
            "cod_mun_ibge": ["3550308"],
            "municipio": ["SÃO PAULO"],
            "uf": ["SP"],
            "total_medicos": [10],
            "total_cnes": [5],
            "total_vinculos": [10],
        })
        censo = pd.DataFrame({
            "CD_SETOR": ["001", "002"],
            "CD_MUN": ["3550308001", "3509502001"],
            "NM_MUN": ["SÃO PAULO", "CAMPINAS"],
            "v0001": [1000, 2000],
            "AREA_KM2": [1.0, 2.0],
            "cod_mun_ibge": ["3550308", "3509502"],
        })
        result = cruzar_medicos_populacao(med, censo)
        campinas = result[result["cod_mun_ibge"] == "3509502"].iloc[0]
        assert campinas["total_medicos"] == 0
