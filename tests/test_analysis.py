"""Testes unitários para o módulo de análise."""

import sys
from pathlib import Path

# Adicionar src ao path para imports funcionarem
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import pytest

from src.analysis import (
    classificar_densidade_medica,
    filtrar_medicos,
    identificar_desertos_medicos,
)


def test_filtrar_medicos():
    """Testa filtro de médicos por CBO."""
    df = pd.DataFrame({
        "profissional_cbo": ["225125", "223505", "225103", "322205"],
        "nome": ["A", "B", "C", "D"],
    })
    resultado = filtrar_medicos(df)
    assert len(resultado) == 2
    assert set(resultado["nome"]) == {"A", "C"}


def test_classificar_densidade_medica():
    """Testa classificação de densidade médica."""
    assert classificar_densidade_medica(0.5) == "1. Crítico (<1,0)"
    assert classificar_densidade_medica(1.5) == "2. Insuficiente (1-2)"
    assert classificar_densidade_medica(3.0) == "3. Adequado (2-4)"
    assert classificar_densidade_medica(6.0) == "4. Bom (4-8)"
    assert classificar_densidade_medica(10.0) == "5. Excelente (≥8)"


def test_identificar_desertos_medicos():
    """Testa identificação de desertos médicos."""
    df = pd.DataFrame({
        "municipio": ["A", "B", "C"],
        "medicos_por_1k": [0.5, 2.0, 0.8],
    })
    desertos = identificar_desertos_medicos(df, limiar=1.0)
    assert len(desertos) == 2
    assert set(desertos["municipio"]) == {"A", "C"}