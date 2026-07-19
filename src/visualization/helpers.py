"""
Funções auxiliares de UI para mapas Folium.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import warnings

import folium


METADADOS_PROJETO: dict[str, str] = {
    "autor": "Vanessa Batista (@vandromedae)",
    "repo": "https://github.com/vandromedae/desertos-medicos-sus",
    "licenca": "MIT",
    "descricao": (
        "Análise geoespacial de desertos médicos no estado de São Paulo. "
        "Metodologia E2SFCA com decaimento gaussiano (β=0,5) e raio de captura de 5 km."
    ),
}


def adicionar_metadados(m: folium.Map, titulo_mapa: str) -> None:
    """Injeta metadados de autoria no <head> do HTML gerado pelo Folium.

    Adiciona <title>, <meta name="author">, <meta name="description">,
    <meta name="license"> e <link> para o repositório.
    """
    tags = (
        f'<title>{titulo_mapa}</title>\n'
        f'    <meta name="author" content="{METADADOS_PROJETO["autor"]}" />\n'
        f'    <meta name="description" content="{METADADOS_PROJETO["descricao"]}" />\n'
        f'    <meta name="license" content="{METADADOS_PROJETO["licenca"]}" />\n'
        f'    <link rel="meta" title="Repositório" href="{METADADOS_PROJETO["repo"]}" />'
    )
    m.get_root().header.add_child(folium.Element(tags))


def criar_mapa_base(lat: float, lon: float, zoom: int = 11) -> folium.Map:
    """Cria mapa base com tema escuro."""
    return folium.Map(
        location=[lat, lon],
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
    )


def adicionar_titulo(m: folium.Map, titulo: str) -> None:
    """Adiciona título flutuante ao mapa."""
    html = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                background-color: rgba(255,255,255,0.95); border: 2px solid #333;
                border-radius: 8px; padding: 12px 24px; font-size: 16px;
                font-weight: bold; z-index: 9999; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);">
        {titulo}
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))


def adicionar_legenda(m: folium.Map, titulo: str, itens: dict[str, str]) -> None:
    """Adiciona legenda customizada ao mapa."""
    itens_html = ""
    for label, cor in itens.items():
        itens_html += f"""
        <i style="background:{cor};width:16px;height:16px;float:left;
                  margin-right:8px;opacity:0.8;border:1px solid #333;"></i>
        {label}<br>
        """

    html = f"""
    <div style="position: fixed; bottom: 30px; left: 30px;
                width: 260px; background-color: rgba(255,255,255,0.95);
                border: 2px solid #333; border-radius: 8px; padding: 12px;
                font-size: 12px; z-index: 9999; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);">
        <b style="font-size:14px;">{titulo}</b><br><br>
        {itens_html}
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))


def adicionar_barra_inferior(m: folium.Map, texto: str) -> None:
    """Adiciona barra de informação na parte inferior do mapa.

    .. deprecated:: 4.0
        Não é usada por nenhum mapa atualmente.
    """
    warnings.warn(
        "adicionar_barra_inferior() está obsoleta e não é usada por nenhum mapa.",
        DeprecationWarning,
        stacklevel=2,
    )
    html = f"""
    <div style="position: fixed; bottom: 0; left: 0; right: 0;
                background-color: rgba(0,0,0,0.7); color: white;
                padding: 6px 12px; font-size: 11px; z-index: 9999;
                text-align: center;">
        {texto}
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))
