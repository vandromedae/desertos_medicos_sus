"""
Módulo de validação do projeto Desertos Médicos SUS.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT
"""

from src.validation.e2sfca import (
    calcular_e2sfca_manual,
    erro_relativo,
    sao_iguais,
    validar_e2sfca_100_setores,
)

__all__ = [
    "calcular_e2sfca_manual",
    "erro_relativo",
    "sao_iguais",
    "validar_e2sfca_100_setores",
]
