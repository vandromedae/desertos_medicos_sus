"""

Módulo de carregamento e download de dados.
Responsável por baixar dados do ElastiCNES via API, carregar CSVs,
Parquets e arquivos .dbc, e gerenciar cache para evitar downloads redundantes.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import time
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from src.config import (
    COMPETENCIA_DEFAULT,
    DATA_EXTERNAL,
    DATA_PROCESSED,
    ELASTICNES_CAMPOS_PROF,
    ELASTICNES_CSV_ENDPOINT,
    ELASTICNES_HEADERS,
    ELASTICNES_INDEX_ID,
    TIMEOUT_DOWNLOAD,
    UFs_BRASIL,
)


class ElasticnesDownloader:
    """
    Cliente para download de dados do ElastiCNES.
    
    Exemplo:
        downloader = ElasticnesDownloader()
        df = downloader.download_uf("SP", competencia="202605")
    """
    
    def __init__(self, output_dir: Path = DATA_EXTERNAL):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _build_payload(
        self,
        uf: Optional[str] = None,
        competencia: str = COMPETENCIA_DEFAULT,
        campos: Optional[list[str]] = None,
        filtros_adicionais: Optional[dict[str, str]] = None,
    ) -> dict:
        """Constrói o payload da requisição ao ElastiCNES."""
        
        campos_selecionados = campos or ELASTICNES_CAMPOS_PROF
        
        # Filtros de data (range amplo para garantir cobertura)
        filtro_data = {
            "meta": {"field": "dt_comp"},
            "query": {
                "range": {
                    "dt_comp": {
                        "format": "strict_date_optional_time",
                        "gte": "2016-01-01T00:00:00.000Z",
                        "lte": "2030-12-31T23:59:59.999Z",
                    }
                }
            },
        }
        
        # Filtros principais (competência, SUS, convênio)
        parent_filters = [
            {
                "meta": {"key": "index_comp.keyword"},
                "query": {"match_phrase": {"index_comp.keyword": competencia}},
            },
            {
                "meta": {"key": "profissional_atende_sus.keyword"},
                "query": {"match_phrase": {"profissional_atende_sus.keyword": "SIM"}},
            },
            {
                "meta": {"key": "convenio_sus.Keyword"},
                "query": {"match_phrase": {"convenio_sus.Keyword": "SIM"}},
            },
        ]
        
        if uf:
            parent_filters.append({
                "meta": {"key": "uf.keyword"},
                "query": {"match_phrase": {"uf.keyword": uf}},
            })
        
        if filtros_adicionais:
            for key, value in filtros_adicionais.items():
                parent_filters.append({
                    "meta": {"key": f"{key}.keyword"},
                    "query": {"match_phrase": {f"{key}.keyword": value}},
                })
        
        return {
            "browserTimezone": "Etc/GMT-3",
            "version": "8.8.2",
            "searchSource": {
                "query": {"query": "", "language": "kuery"},
                "fields": [
                    {"field": campo, "include_unmapped": "true"}
                    for campo in campos_selecionados
                ],
                "index": ELASTICNES_INDEX_ID,
                "sort": [{"_doc": "desc"}],
                "filter": [filtro_data],
                "parent": {
                    "query": {"query": "", "language": "kuery"},
                    "highlightAll": True,
                    "filter": parent_filters,
                    "parent": {"filter": [filtro_data]},
                },
            },
            "columns": campos_selecionados,
            "title": f"CNES - PROFISSIONAIS SUS - {uf or 'BRASIL'} - {competencia}",
        }
    
    def download_uf(
        self,
        uf: str,
        competencia: str = COMPETENCIA_DEFAULT,
        force: bool = False,
        campos: Optional[list[str]] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Baixa profissionais SUS de uma UF específica.
        
        Args:
            uf: Sigla da UF (ex: 'SP')
            competencia: Competência no formato YYYYMM
            force: Se True, baixa mesmo se arquivo existir
            campos: Lista de campos a baixar (default: todos)
        
        Returns:
            DataFrame com os dados ou None em caso de erro
        """
        uf = uf.upper()
        arquivo_saida = self.output_dir / f"profissionais_sus_{uf}_{competencia}.csv"
        
        # Verificar cache
        if arquivo_saida.exists() and not force:
            print(f" Cache encontrado: {arquivo_saida.name}")
            return pd.read_csv(arquivo_saida, low_memory=False)
        
        payload = self._build_payload(uf=uf, competencia=competencia, campos=campos)
        
        print(f"  Baixando dados de {uf} (competência {competencia})...")
        
        try:
            response = requests.post(
                ELASTICNES_CSV_ENDPOINT,
                headers=ELASTICNES_HEADERS,
                json=payload,
                timeout=TIMEOUT_DOWNLOAD,
            )
            
            if response.status_code != 200:
                print(f" Erro HTTP {response.status_code}: {response.text[:200]}")
                return None
            
            # Salvar e carregar
            with open(arquivo_saida, "wb") as f:
                f.write(response.content)
            
            print(f" Download concluído: {arquivo_saida.name}")
            
            df = pd.read_csv(arquivo_saida, low_memory=False)
            print(f"    {len(df):,} registros baixados")
            
            return df
            
        except requests.exceptions.Timeout:
            print(f"  Timeout no download de {uf}")
            return None
        except Exception as e:
            print(f" Erro inesperado: {e}")
            return None
    
    def download_brasil(
        self,
        competencia: str = COMPETENCIA_DEFAULT,
        ufs: Optional[list[str]] = None,
        force: bool = False,
    ) -> pd.DataFrame:
        """
        Baixa profissionais SUS de todas as UFs (ou lista específica).
        
        Returns:
            DataFrame consolidado de todas as UFs
        """
        ufs_selecionadas = ufs or UFs_BRASIL
        dfs = []
        
        print(f" Iniciando download do Brasil ({len(ufs_selecionadas)} UFs)")
        print("=" * 60)
        
        for i, uf in enumerate(ufs_selecionadas, 1):
            print(f"\n[{i}/{len(ufs_selecionadas)}] UF: {uf}")
            df = self.download_uf(uf, competencia=competencia, force=force)
            
            if df is not None:
                dfs.append(df)
            
            # Delay para não sobrecarregar o servidor
            if i < len(ufs_selecionadas):
                time.sleep(2)
        
        if not dfs:
            print(" Nenhum dado foi baixado")
            return pd.DataFrame()
        
        # Consolidar
        df_consolidado = pd.concat(dfs, ignore_index=True)
        arquivo_consolidado = self.output_dir / f"profissionais_sus_brasil_{competencia}.csv"
        df_consolidado.to_csv(arquivo_consolidado, index=False)
        
        print("\n" + "=" * 60)
        print(f" Brasil consolidado: {len(df_consolidado):,} registros")
        print(f"    Salvo em: {arquivo_consolidado.name}")
        
        return df_consolidado


def carregar_parquet(caminho: Path) -> pd.DataFrame:
    """Carrega arquivo Parquet com validação."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    return pd.read_parquet(caminho)


def carregar_csv(caminho: Path, **kwargs) -> pd.DataFrame:
    """Carrega CSV com encoding automático."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    return pd.read_csv(caminho, low_memory=False, **kwargs)