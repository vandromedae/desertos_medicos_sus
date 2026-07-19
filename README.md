# Desertos Médicos no SUS - Estado de São Paulo

> Análise geoespacial para identificar desigualdades de acesso a médicos SUS em setores censitários de São Paulo — revelando desertos médicos mascarados por médias municipais

## Objetivo

Identificar setores censitários do estado de São Paulo com baixa acessibilidade a médicos do SUS, utilizando o método Enhanced Two-Step Floating Catchment Area (E2SFCA), permitindo análises tanto em nível de setor quanto de município.

## Principais Descobertas

A análise em nível setorial revela desigualdades que desaparecem quando os dados são agregados apenas por município. Os principais indicadores para o estado de São Paulo são:

* **Escala da Análise:** 645 municípios e 103.319 setores censitários (~44,4 milhões de habitantes) cruzados com 10.558 CNES ativos com médicos SUS.
* **Acesso Adequado:** Cerca de 72% da população (32,4 milhões de pessoas) reside em setores classificados com acesso "Moderado", "Bom" ou "Excelente".
* **O Desafio Real:** Mais de **10,9 milhões de pessoas** (quase 25% da população do estado) vivem em setores classificados como acesso "Limitado", "Crítico" ou "Deserto Médico".
* **O Paradoxo da Proximidade:** A métrica E2SFCA identificou 125 setores de *alta densidade populacional* em situação crítica. Nestas áreas, a população mora geograficamente perto de estabelecimentos de saúde, mas o acesso efetivo é baixo devido à alta competição por recursos (sobrecarga da demanda). Isso prova que proximidade física não é sinônimo de capacidade de atendimento.

| Métrica | Valor |
| :--- | :--- |
| **Setores Censitários Analisados** | 103.319 |
| **População Total Mapeada** | ~44,4 milhões |
| **CNES com Médicos SUS** | 10.558 |
| **População em Acesso Limitado/Crítico/Deserto** | ~10,9 milhões (25%) |
| **Setores de Alta Densidade em Risco** | 125 |

## Visualização

4 mapas interativos:
1. **Mapa 1**: Densidade médica municipal (coroplético estadual)
2. **Mapa 2**: Densidade populacional setorial (645 mapas individuais)
3. **Mapa 3**: Bivariado municipal (densidade × acessibilidade)
4. **Mapa 4**: Bivariado setorial (desigualdades intra-municipais)

Todos os mapas são gerados em `output/mapas/` com página índice navegável.

### Mapas de Exemplo
- [Densidade Médica Estado de São Paulo](output/exemplos/mapa_01_densidade_municipal.html)
- [Desertos Médicos em SP: Densidade x Acessibilidade (Municipal - E2SFCA)](output/exemplos/mapa_03_bivariado_municipal.html)
- [Densidade Populacional - Osasco](output/exemplos/mapa_osasco.html)
- [Desertos Médicos por Setor - Atibaia](output/exemplos/mapa_bivariado_atibaia.html)

## Metodologia

### Enhanced Two-Step Floating Catchment Area (E2SFCA)

Diferente de análises tradicionais baseadas apenas em distância, este projeto implementa o **E2SFCA** (Luo & Wang, 2003), que considera simultaneamente:

1. **Oferta**: número de médicos em cada CNES
2. **Demanda**: população em cada setor censitário
3. **Distância**: decaimento gaussiano com raio de captura de 5km

Passo 1: Para cada CNES j → R_j = médicos_j / Σ(pop_k × W(d_kj))
Passo 2: Para cada setor i → A_i = Σ(R_j × W(d_ij))

Onde `W(d)` é uma função de decaimento gaussiano com **β = 0.5**, que reduz o peso de médicos distantes. O raio de captura de 5km é aplicado de forma estritamente exclusiva na borda (setores/estabelecimentos a exatamente 5.000m não entram no cálculo), consistente entre o spatial join e a função de decaimento.

### Validação

- **100 setores testados** via reimplementação independente do algoritmo (loop puro em Python, sem as otimizações vetorizadas do pipeline de produção)
- **100% de precisão** (erro relativo < 0.01%, comparado ponto a ponto contra o pipeline de produção)
- Teste de borda dedicado, confirmando o tratamento exclusivo do raio de 5km
- Classificação por percentis para balanceamento estatístico

---

## Fontes de Dados

- [ElastiCNES (DATASUS)](https://elasticnes.saude.gov.br/): Profissionais médicos SUS por estabelecimento
- [IBGE Censo 2022](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html): População por setor censitário e shapefiles

## Stack Técnica

- Linguagem: Python 3.11
- Dados: Pandas, NumPy, PyArrow
- Geoespacial: GeoPandas, Shapely, Fiona, PyProj
- Visualização: Folium, Matplotlib, Seaborn
- API: Requests (ElastiCNES)
- Notebooks: JupyterLab

## Como Executar

### Pré-requisitos
- Python 3.11+
- Conda (recomendado) ou venv
- Shapefiles do IBGE (download manual necessário — automação no roadmap):

```bash
mkdir -p data/external
# Municípios de SP
curl -o data/external/SE_Municipios_2025.zip \
  https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/SE/SE_Municipios_2025.zip
unzip data/external/SE_Municipios_2025.zip -d data/external/SP_Municipios_2025/

# Setores censitários de SP
curl -o data/external/SP_setores_CD2022.zip \
  https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/UF/SP_setores_CD2022.zip
unzip data/external/SP_setores_CD2022.zip -d data/external/SP_setores_CD2022_IBGE/
```

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/vandromedae/desertos-medicos-sus.git
cd desertos-medicos-sus

# Opção 1: Conda (recomendado)
conda env create -f environment.yml
conda activate desertos_medicos_sus

# Opção 2: pip (geopandas/shapely/fiona/pyproj devem vir de conda-forge)
pip install -r requirements.txt
```

### Rodar o Pipeline

```bash
# Pipeline completo: coleta → pré-processamento → E2SFCA → ~1.296 mapas HTML
python scripts/run_pipeline.py

# Modo rápido: etapas 1-3 + 2 mapas (ideal para desenvolvimento)
python scripts/run_pipeline.py --sample
```

Os dados processados ficam em `data/processed/` e os mapas em `output/mapas/`.

### Rodar via Notebooks (interativo)

```bash
jupyter lab
# Seguir na ordem: 01 → 02 → 03 → 04
```

### Rodar Testes

```bash
pytest
```

## Limitações Conhecidas

- Download do shapefile IBGE é manual (automação planejada)
- Legenda definida mas não renderizada nos mapas setoriais (Mapa 2/4) — em correção

## Como Citar

Se você utilizar este código ou dados, por favor, cite:

> Batista, V. (2026). *Desertos Médicos no SUS - Estado de São Paulo (Análise E2SFCA)*. v1.0.0. Disponível em: https://github.com/vandromedae/desertos-medicos-sus

O arquivo [CITATION.cff](CITATION.cff) também está disponível para ferramentas de citation management.

## Licença

Este projeto é de código aberto e está sob a licença MIT.

## Autora

**Vanessa Batista** - Cientista de Dados & Engenheira de IA
- GitHub: [@vandromedae](https://github.com/vandromedae)

## Referências

- **Luo, W., & Wang, F. (2003).** Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. *Environment and Planning B: Planning and Design*, 30(6), 865-884. https://doi.org/10.1068/b29120
- **Instituto Brasileiro de Geografia e Estatística (IBGE). (2022).** *Censo Demográfico 2022: Agregados por Setores Censitários*. Recuperado de https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html
- **Ministério da Saúde / DATASUS. (2026).** *ElastiCNES: Cadastro Nacional de Estabelecimentos de Saúde*. Recuperado de https://elasticnes.saude.gov.br