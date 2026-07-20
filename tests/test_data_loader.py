"""Testes unitários para o módulo de carregamento e download de dados."""

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from src.data_loader import ShapefileDownloader


class TestShapefileDownloader:
    """Testes para ShapefileDownloader."""

    def test_garantir_shapefiles_sp_skip_when_exists(self, tmp_path):
        """Se .shp já existe, não baixa nada."""
        shp_mun = tmp_path / "SP_Municipios_2025" / "SP_Municipios_2025.shp"
        shp_mun.parent.mkdir(parents=True)
        shp_mun.touch()
        shp_set = tmp_path / "SP_setores_CD2022_IBGE" / "SP_setores_CD2022.shp"
        shp_set.parent.mkdir(parents=True)
        shp_set.touch()

        dl = ShapefileDownloader(output_dir=tmp_path)
        with mock.patch("src.data_loader.requests.get") as mock_get:
            dl.garantir_shapefiles_sp()
            mock_get.assert_not_called()

    def test_baixar_municipios_sp_downloads_when_missing(self, tmp_path):
        """Se .shp de municípios não existe, baixa e extrai."""
        dl = ShapefileDownloader(output_dir=tmp_path)

        fake_content = b"fake zip content"
        mock_response = mock.MagicMock()
        mock_response.content = fake_content
        mock_response.raise_for_status = mock.MagicMock()

        with (
            mock.patch("src.data_loader.requests.get", return_value=mock_response) as mock_get,
            mock.patch("src.data_loader.zipfile.ZipFile") as mock_zip,
        ):
            mock_zip.return_value.__enter__ = mock.MagicMock(return_value=mock.MagicMock())
            mock_zip.return_value.__exit__ = mock.MagicMock(return_value=False)

            result = dl.baixar_municipios_sp()

            mock_get.assert_called_once()
            assert "SE_Municipios_2025.zip" in mock_get.call_args[0][0] or \
                   "SE_Municipios_2025" in mock_get.call_args[1].get("url", mock_get.call_args[0][0])
            assert result.name == "SP_Municipios_2025.shp"

    def test_baixar_setores_sp_downloads_when_missing(self, tmp_path):
        """Se .shp de setores não existe, baixa e extrai."""
        dl = ShapefileDownloader(output_dir=tmp_path)

        fake_content = b"fake zip content"
        mock_response = mock.MagicMock()
        mock_response.content = fake_content
        mock_response.raise_for_status = mock.MagicMock()

        with (
            mock.patch("src.data_loader.requests.get", return_value=mock_response) as mock_get,
            mock.patch("src.data_loader.zipfile.ZipFile") as mock_zip,
        ):
            mock_zip.return_value.__enter__ = mock.MagicMock(return_value=mock.MagicMock())
            mock_zip.return_value.__exit__ = mock.MagicMock(return_value=False)

            result = dl.baixar_setores_sp()

            mock_get.assert_called_once()
            assert result.name == "SP_setores_CD2022.shp"

    def test_baixar_municipios_sp_force_redownloads(self, tmp_path):
        """Com force=True, baixa mesmo se .shp já existe."""
        shp_mun = tmp_path / "SP_Municipios_2025" / "SP_Municipios_2025.shp"
        shp_mun.parent.mkdir(parents=True)
        shp_mun.touch()

        dl = ShapefileDownloader(output_dir=tmp_path)

        mock_response = mock.MagicMock()
        mock_response.content = b"fake zip"
        mock_response.raise_for_status = mock.MagicMock()

        with (
            mock.patch("src.data_loader.requests.get", return_value=mock_response) as mock_get,
            mock.patch("src.data_loader.zipfile.ZipFile") as mock_zip,
        ):
            mock_zip.return_value.__enter__ = mock.MagicMock(return_value=mock.MagicMock())
            mock_zip.return_value.__exit__ = mock.MagicMock(return_value=False)

            dl.baixar_municipios_sp(force=True)
            mock_get.assert_called_once()

    def test_baixar_e_extrair_raises_on_http_error(self, tmp_path):
        """Se HTTP retorna erro, propagar exceção."""
        import requests as req

        dl = ShapefileDownloader(output_dir=tmp_path)

        mock_response = mock.MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("404")

        with mock.patch("src.data_loader.requests.get", return_value=mock_response):
            with pytest.raises(req.exceptions.HTTPError):
                dl.baixar_municipios_sp()
