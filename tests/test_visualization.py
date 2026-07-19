"""
Testes unitários para o pacote src.visualization.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import json
import tempfile
from pathlib import Path

import folium
import pandas as pd
import pytest


class TestClassificarAcessoPorCategoria:
    """Testes para classificar_acesso_por_categoria."""

    def test_excelente_returns_alto(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Excelente") == "Alto"

    def test_bom_returns_alto(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Bom") == "Alto"

    def test_moderado_returns_medio(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Moderado") == "Médio"

    def test_limitado_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Limitado") == "Baixo"

    def test_critico_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Crítico") == "Baixo"

    def test_deserto_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("Deserto") == "Baixo"

    def test_nan_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria(float('nan')) == "Baixo"

    def test_none_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria(None) == "Baixo"

    def test_empty_string_returns_baixo(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("") == "Baixo"

    def test_full_category_string(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("3. Moderado (acesso médio)") == "Médio"

    def test_bom_with_details(self):
        from src.visualization import classificar_acesso_por_categoria
        assert classificar_acesso_por_categoria("2. Bom (acesso alto)") == "Alto"


class TestClassificarDensidadeBivariada:
    """Testes para classificar_densidade_bivariada."""

    def test_zero_returns_baixa(self):
        from src.visualization import classificar_densidade_bivariada
        quartis = pd.Series([1.0, 3.0], index=[0.33, 0.66])
        assert classificar_densidade_bivariada(0, quartis) == "Baixa"

    def test_nan_returns_baixa(self):
        from src.visualization import classificar_densidade_bivariada
        quartis = pd.Series([1.0, 3.0], index=[0.33, 0.66])
        assert classificar_densidade_bivariada(float('nan'), quartis) == "Baixa"

    def test_below_first_tercile_returns_baixa(self):
        from src.visualization import classificar_densidade_bivariada
        quartis = pd.Series([1.0, 3.0], index=[0.33, 0.66])
        assert classificar_densidade_bivariada(0.5, quartis) == "Baixa"

    def test_between_terciles_returns_media(self):
        from src.visualization import classificar_densidade_bivariada
        quartis = pd.Series([1.0, 3.0], index=[0.33, 0.66])
        assert classificar_densidade_bivariada(2.0, quartis) == "Média"

    def test_above_second_tercile_returns_alta(self):
        from src.visualization import classificar_densidade_bivariada
        quartis = pd.Series([1.0, 3.0], index=[0.33, 0.66])
        assert classificar_densidade_bivariada(5.0, quartis) == "Alta"


class TestClassificarAcessoPorTercisComQuartis:
    """Testes para classificar_acesso_por_tercis_com_quartis."""

    def test_e2sfca_zero_returns_baixo(self):
        from src.visualization import classificar_acesso_por_tercis_com_quartis
        serie = pd.Series([0.0, 0.01, 0.02, 0.03, 0.05])
        resultado = classificar_acesso_por_tercis_com_quartis(serie, tipo="e2sfca")
        assert resultado.iloc[0] == "Baixo"

    def test_e2sfca_all_baixo_medio_alto(self):
        from src.visualization import classificar_acesso_por_tercis_com_quartis
        serie = pd.Series([0.0, 0.001, 0.005, 0.01, 0.05])
        resultado = classificar_acesso_por_tercis_com_quartis(serie, tipo="e2sfca")
        assert set(resultado.unique()) == {"Baixo", "Médio", "Alto"}

    def test_distancia_inverted_logic(self):
        from src.visualization import classificar_acesso_por_tercis_com_quartis
        serie = pd.Series([0.5, 1.0, 2.0, 5.0, 10.0])
        resultado = classificar_acesso_por_tercis_com_quartis(serie, tipo="distancia")
        assert set(resultado.unique()) == {"Baixo", "Médio", "Alto"}

    def test_invalid_tipo_raises(self):
        from src.visualization import classificar_acesso_por_tercis_com_quartis
        serie = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="Tipo desconhecido"):
            classificar_acesso_por_tercis_com_quartis(serie, tipo="invalido")


class TestGerarIndiceMapas:
    """Testes para gerar_indice_mapas."""

    def test_basic_generation(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        entries = [
            {"href": "mapa_a.html", "nome": "Municipio A", "info": "10 setores | 1.000 hab"},
            {"href": "mapa_b.html", "nome": "Municipio B", "info": "20 setores | 2.000 hab"},
        ]
        gerar_indice_mapas("Titulo Teste", "Subtitulo", entries, output)
        assert output.exists()
        content = output.read_text(encoding='utf-8')
        assert "Titulo Teste" in content
        assert "mapa_a.html" in content
        assert "Municipio A" in content
        assert "10 setores" in content

    def test_with_stats(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        entries = [
            {
                "href": "mapa_a.html",
                "nome": "Municipio A",
                "info": "10 setores",
                "stats": {"critico": 5, "deserto": 2, "pop_risco": 1000},
            },
        ]
        gerar_indice_mapas("Titulo", "", entries, output)
        content = output.read_text(encoding='utf-8')
        assert "5 setores críticos" in content
        assert "1,000" in content

    def test_search_js_present(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        gerar_indice_mapas("T", "", [], output)
        content = output.read_text(encoding='utf-8')
        assert "searchInput" in content
        assert "addEventListener" in content


class TestClassificarDensidadePorMunicipio:
    """Testes para classificar_densidade_por_municipio."""

    def test_small_group_uses_fixed_bins(self):
        from src.visualization.per_municipality import classificar_densidade_por_municipio
        grupo = pd.DataFrame({
            'densidade_pop': [50, 200, 800, 1500, 5000],
        })
        resultado = classificar_densidade_por_municipio(grupo)
        assert len(resultado) == 5
        assert set(resultado.unique()).issubset({"Baixa", "Média", "Alta"})

    def test_large_group_uses_qcut(self):
        from src.visualization.per_municipality import classificar_densidade_por_municipio
        grupo = pd.DataFrame({
            'densidade_pop': list(range(100, 200)),
        })
        resultado = classificar_densidade_por_municipio(grupo)
        assert set(resultado.unique()).issubset({"Baixa", "Média", "Alta"})


class TestAdicionarMetadados:
    """Testes para adicionar_metadados (injeção de metadados de autoria no <head>)."""

    def _save_and_read(self, m, tmp_path):
        out = tmp_path / "map.html"
        m.save(out)
        return out.read_text(encoding="utf-8")

    def test_injects_title_tag(self, tmp_path):
        from src.visualization.helpers import adicionar_metadados
        m = folium.Map(location=[0, 0], zoom_start=2)
        adicionar_metadados(m, "MAPA 1: Teste")
        html = self._save_and_read(m, tmp_path)
        assert "<title>MAPA 1: Teste</title>" in html

    def test_injects_author_meta(self, tmp_path):
        from src.visualization.helpers import adicionar_metadados
        m = folium.Map(location=[0, 0], zoom_start=2)
        adicionar_metadados(m, "Teste")
        html = self._save_and_read(m, tmp_path)
        assert 'name="author"' in html
        assert "Vanessa Batista" in html

    def test_injects_license_meta(self, tmp_path):
        from src.visualization.helpers import adicionar_metadados
        m = folium.Map(location=[0, 0], zoom_start=2)
        adicionar_metadados(m, "Teste")
        html = self._save_and_read(m, tmp_path)
        assert 'name="license"' in html
        assert "MIT" in html

    def test_injects_repo_link(self, tmp_path):
        from src.visualization.helpers import adicionar_metadados
        m = folium.Map(location=[0, 0], zoom_start=2)
        adicionar_metadados(m, "Teste")
        html = self._save_and_read(m, tmp_path)
        assert "vandromedae/desertos-medicos-sus" in html


class TestGerarIndiceMetadados:
    """Testes para metadados de autoria nas páginas índice."""

    def test_index_contains_author_meta(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        gerar_indice_mapas("Título Teste", "", [{"href": "a.html", "nome": "A", "info": "1"}], output)
        content = output.read_text(encoding="utf-8")
        assert 'name="author"' in content
        assert "Vanessa Batista" in content

    def test_index_contains_license_meta(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        gerar_indice_mapas("Título Teste", "", [], output)
        content = output.read_text(encoding="utf-8")
        assert 'name="license"' in content
        assert "MIT" in content

    def test_index_contains_description_meta(self, tmp_path):
        from src.visualization import gerar_indice_mapas
        output = tmp_path / "indice.html"
        gerar_indice_mapas("Título Teste", "", [], output)
        content = output.read_text(encoding="utf-8")
        assert 'name="description"' in content
        assert "E2SFCA" in content
