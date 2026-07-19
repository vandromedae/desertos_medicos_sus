"""
Geração de páginas índice HTML para navegação entre mapas.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

from pathlib import Path

from src.visualization.helpers import METADADOS_PROJETO


def gerar_indice_mapas(
    titulo: str,
    subtitulo: str,
    entries: list[dict],
    output_path: Path,
    grid_min_width: str = "250px",
) -> None:
    """
    Gera uma página índice HTML com busca para navegar entre mapas.

    Args:
        titulo: Título principal da página.
        subtitulo: Subtítulo/descrição.
        entries: Lista de dicts com chaves:
            - 'href': caminho relativo do link
            - 'nome': nome do município para exibição
            - 'info': texto auxiliar (ex: "123 setores | 45.678 hab")
            - 'stats' (opcional): dict com chaves 'critico', 'deserto', 'pop_risco'
        output_path: Caminho do arquivo HTML de saída.
        grid_min_width: Largura mínima dos cards no grid CSS.
    """
    entries_html = ""
    for entry in entries:
        stats_html = ""
        if "stats" in entry and entry["stats"]:
            s = entry["stats"]
            stats_html = (
                f'<div class="stats">'
                f'<span class="critico">🔴 {s.get("critico", 0)} setores críticos</span> | '
                f'⚫ {s.get("deserto", 0)} desertos | '
                f'👥 {s.get("pop_risco", 0):,} hab em risco'
                f'</div>'
            )
        entries_html += f"""
        <div class="municipio">
            <a href="{entry['href']}">{entry['nome']}</a>
            <small>{entry['info']}</small>
            {stats_html}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{titulo}</title>
    <meta charset="UTF-8">
    <meta name="author" content="{METADADOS_PROJETO['autor']}" />
    <meta name="description" content="{METADADOS_PROJETO['descricao']}" />
    <meta name="license" content="{METADADOS_PROJETO['licenca']}" />
    <link rel="meta" title="Repositório" href="{METADADOS_PROJETO['repo']}" />
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; text-align: center; }}
        .subtitle {{ text-align: center; color: #666; }}
        .search-box {{ width: 100%; padding: 12px; font-size: 16px; margin: 20px 0; border: 2px solid #ddd; border-radius: 8px; }}
        .municipios {{ display: grid; grid-template-columns: repeat(auto-fill, minmax({grid_min_width}, 1fr)); gap: 10px; margin-top: 20px; }}
        .municipio {{ background: white; padding: 12px; border-radius: 6px; border: 1px solid #ddd; transition: all 0.3s; }}
        .municipio:hover {{ background: #fff5e6; transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .municipio a {{ text-decoration: none; color: #d95f0e; font-weight: bold; }}
        .municipio small {{ display: block; color: #666; margin-top: 4px; font-size: 12px; }}
        .stats {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; font-size: 11px; }}
        .stats .critico {{ color: #800026; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>{titulo}</h1>
    {f'<p class="subtitle">{subtitulo}</p>' if subtitulo else ''}
    <input type="text" class="search-box" placeholder="🔍 Buscar município..." id="searchInput">
    <div class="municipios" id="municipiosList">
        {entries_html}
    </div>
    <script>
    document.getElementById('searchInput').addEventListener('input', function(e) {{
        var filter = e.target.value.toLowerCase();
        var municipios = document.querySelectorAll('.municipio');
        municipios.forEach(function(m) {{
            var text = m.textContent.toLowerCase();
            m.style.display = text.indexOf(filter) > -1 ? 'block' : 'none';
        }});
    }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
