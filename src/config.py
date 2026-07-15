"""
Configurações globais do projeto Desertos Médicos SUS.

Centraliza todos os caminhos, constantes da API e parâmetros
de análise para evitar duplicação e facilitar manutenção.
"""

from pathlib import Path
from typing import Final

# ============================================================
#  CAMINHOS DO PROJETO
# ============================================================

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
DATA_RAW: Final[Path] = DATA_DIR / "raw"
DATA_PROCESSED: Final[Path] = DATA_DIR / "processed"
DATA_EXTERNAL: Final[Path] = DATA_DIR / "external"

OUTPUT_DIR: Final[Path] = PROJECT_ROOT / "output"
OUTPUT_MAPAS: Final[Path] = OUTPUT_DIR / "mapas"
OUTPUT_RELATORIOS: Final[Path] = OUTPUT_DIR / "relatorios"

# Garantir que os diretórios existam
for path in [DATA_RAW, DATA_PROCESSED, DATA_EXTERNAL, OUTPUT_MAPAS, OUTPUT_RELATORIOS]:
    path.mkdir(parents=True, exist_ok=True)


# ============================================================
# 🏥 API ELASTICNES
# ============================================================

ELASTICNES_BASE_URL: Final[str] = "https://elasticnes.saude.gov.br"
ELASTICNES_CSV_ENDPOINT: Final[str] = (
    f"{ELASTICNES_BASE_URL}/kibana/api/reporting/v1/generate/immediate/csv_searchsource"
)

ELASTICNES_INDEX_ID: Final[str] = "5f8beb41-8708-4bdc-a7da-5d658f07d25f"
ELASTICNES_KBN_VERSION: Final[str] = "8.8.2"

# Headers padrão para requisições à API
ELASTICNES_HEADERS: Final[dict] = {
    "Accept": "text/csv",
    "Content-Type": "application/json",
    "kbn-version": ELASTICNES_KBN_VERSION,
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Origin": ELASTICNES_BASE_URL,
    "Referer": f"{ELASTICNES_BASE_URL}/kibana/app/dashboards",
    "x-kbn-context": (
        "%7B%22type%22%3A%22application%22%2C%22name%22%3A%22dashboards%22%2C"
        "%22url%22%3A%22%2Fkibana%2Fapp%2Fdashboards%22%2C%22page%22%3A%22app%22%2C"
        "%22id%22%3A%22b7b75ee0-3b4a-11ed-9d84-171ed86536ee%22%7D"
    ),
}

# Campos disponíveis no ElastiCNES para profissionais
ELASTICNES_CAMPOS_PROF: Final[list[str]] = [
    "dt_ano", "dt_comp", "regiao", "uf", "ibge", "municipio", "cnes",
    "nome_fantaia", "cnpj_mantenedora", "cnpj", "tipo_unidade",
    "subtipo_unidade", "natureza_juridica", "gestao", "profissional_nome",
    "profissional_cns", "profissional_atende_sus", "profissional_cbo",
    "carga_horaria_hospitalar_sus", "carga_horaria_ambulatorial_sus",
    "carga_horaria_outros", "profissional_vinculo", "equipe_ine",
    "TIPO EQUIPE", "equipe_subtipo", "equipe_nome", "equipe_area",
    "equipe_dt_ativacao", "equipe_dt_desativacao", "equipe_dt_entrada",
    "equipe_dt_desligamento", "atendimento_prestado", "nivel_atencao",
    "convenio_sus", "telefone", "logradouro", "complemento", "location",
]


# ============================================================
# 🩺 PARÂMETROS DE ANÁLISE
# ============================================================

# Prefixo CBO para médicos (conforme MTE/SEPRT)
CBO_MEDICOS_PREFIX: Final[str] = "225"

# Competência padrão (YYYYMM)
COMPETENCIA_DEFAULT: Final[str] = "202605"

# Lista de UFs do Brasil
UFs_BRASIL: Final[list[str]] = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

# Código IBGE de São Paulo capital
IBGE_SP_CAPITAL: Final[str] = "3550308"

# Limiares de densidade médica (médicos por 1.000 habitantes)
# Referência: CFM recomenda mínimo de 2,0 médicos/1000 hab
LIMIAR_DENSIDADE_MEDICA: Final[dict[str, float]] = {
    "critico": 1.0,       # < 1,0 médico/1000 hab
    "insuficiente": 2.0,  # 1,0 - 2,0
    "adequado": 4.0,      # 2,0 - 4,0
    "bom": 8.0,           # 4,0 - 8,0
    # >= 8,0 é excelente
}


# ============================================================
# 🎨 PALETAS DE CORES PARA MAPAS
# ============================================================

PALETA_DENSIDADE_POPULACIONAL: Final[dict[str, str]] = {
    "1. Muito baixa": "#08519c",
    "2. Baixa": "#3182bd",
    "3. Média": "#6baed6",
    "4. Alta": "#fd8d3c",
    "5. Muito alta": "#d7301f",
}

PALETA_DENSIDADE_MEDICA: Final[dict[str, str]] = {
    "1. Crítico (<1,0)": "#d73027",
    "2. Insuficiente (1-2)": "#fc8d59",
    "3. Adequado (2-4)": "#fee08b",
    "4. Bom (4-8)": "#91cf60",
    "5. Excelente (≥8)": "#1a9850",
}

COR_CNES: Final[str] = "#e74c3c"  # Vermelho para estabelecimentos
COR_SETOR: Final[str] = "#3498db"  # Azul para setores censitários


# ============================================================
# ️ PARÂMETROS DE DOWNLOAD
# ============================================================

TIMEOUT_DOWNLOAD: Final[int] = 300  # 5 minutos
DELAY_ENTRE_UFS: Final[int] = 2     # segundos entre downloads
TAMANHO_BATCH: Final[int] = 10000   # registros por página (Elasticsearch)