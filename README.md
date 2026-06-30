# 🏥 Desertos Médicos no SUS - São Paulo

> Análise geoespacial para identificar municípios do estado de São Paulo com baixa cobertura de médicos por habitante no Sistema Único de Saúde (SUS).

## 🎯 Objetivo

Identificar regiões críticas ("desertos médicos") no estado de São Paulo, onde a população tem acesso limitado a profissionais de saúde via SUS. O projeto utiliza dados abertos do DATASUS e do IBGE para gerar insights que podem apoiar políticas públicas de alocação de profissionais.

## 📊 Fontes de Dados


- **[CNES - Dados de Equipe](https://datasus.saude.gov.br/transferencia-de-arquivos/)**: Profissionais vinculados aos estabelecimentos de saúde

- **[SEADE Censo 2022](https://repositorio.seade.gov.br/dataset/censo-2022-populacao/)**: População por município

- **[Shapefiles IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html)**: Limites geográficos dos municípios

## 🛠️ Stack Técnica

- **Linguagem:** Python 3.11
- **Dados:** Pandas, NumPy, PyArrow
- **Geoespacial:** GeoPandas, Shapely, Fiona, PyProj
- **Visualização:** Folium, Matplotlib, Seaborn
- **Dados DATASUS:** PySUS
- **Notebooks:** JupyterLab

## 📁 Estrutura do Projeto

```
desertos_medicos_sus/
├── notebooks/          # Análises exploratórias (Jupyter)
│   ├── 01_coleta_e_exploracao.ipynb
│   ├── 02_limpeza_e_transformacao.ipynb
│   ├── 03_analise_geoespacial.ipynb
│   └── 04_visualizacao_e_insights.ipynb
├── src/                # Código reutilizável (Python puro)
│   ├── data_loader.py
│   ├── geospatial.py
│   ├── analysis.py
│   └── visualization.py
├── data/               # Dados (não versionados)
│   ├── raw/            # Dados brutos
│   ├── processed/      # Dados limpos
│   └── external/       # Dados externos (shapefiles, IBGE)
├── output/             # Resultados
│   ├── mapas/          # Mapas interativos HTML
│   └── relatorios/     # Relatórios e imagens
├── tests/              # Testes unitários
└── requirements.txt    # Dependências
```

## 🚀 Como Executar

### Pré-requisitos
- Python 3.11+
- Conda (recomendado) ou venv

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/desertos-medicos-sus.git
cd desertos-medicos-sus

# Criar ambiente virtual (conda)
conda create -n desertos_medicos python=3.11 -y
conda activate desertos_medicos

# Instalar dependências
pip install -r requirements.txt

# Iniciar Jupyter
jupyter lab
```

## 📈 Principais Descobertas

> *Em construção — será preenchido ao longo da análise*

- [ ] Total de municípios analisados
- [ ] Número de municípios classificados como "deserto médico"
- [ ] Regiões mais críticas identificadas
- [ ] Correlações encontradas

## 🗺️ Visualização

> *Em construção — screenshots dos mapas serão adicionados aqui*

## 💡 Próximos Passos

- [ ] Integrar dados de transporte público (tempo real até hospitais)
- [ ] Aplicar clustering (K-Means) para sugerir locais ideais para novas UPAs
- [ ] Criar dashboard interativo com Streamlit
- [ ] Comparar com dados do setor privado (ANS)

## 📄 Licença

Este projeto é de código aberto e está sob a licença MIT.

## 👤 Autora

**Vanessa Batista** - Cientista de Dados & Engenheira de IA
- GitHub: [@vandromedae](https://github.com/vandromedae)
