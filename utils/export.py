import pandas as pd


def export_to_csv(data: list[dict]) -> str:
    """Converte uma lista de dicionários em uma string formato CSV (compatível com Excel)."""
    if not data:
        return ""

    df = pd.DataFrame(data)
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig")


def export_to_markdown(data: list[dict], title: str = "Relatório") -> str:
    """Converte uma lista de dicionários em formato Markdown estruturado por cards.

    Evita quebras de tabela ao lidar com textos multilinhas.
    """
    if not data:
        return f"# {title}\n\n*Nenhum dado disponível.*"

    md_content = f"# {title}\n\n"

    for item in data:
        status = item.get("status", "Não Executado")
        status_icon = (
            "🟢"
            if status == "Passou"
            else ("🔴" if status == "Falhou" else ("🟡" if status == "Bloqueado" else "⚪"))
        )

        test_type = item.get("test_type", "Funcional")
        tc_title = item.get("title", "")
        cycle = item.get("test_cycle", "Sem Ciclo")
        preconditions = item.get("preconditions") or "N/A"
        steps = item.get("steps") or "N/A"
        expected = item.get("expected_result") or "N/A"

        md_content += f"### {status_icon} [{test_type}] - {tc_title}\n"
        md_content += f"- **Tipo:** `{test_type}`\n"
        md_content += f"- **Ciclo:** `{cycle}`\n"
        md_content += f"- **Pré-condições:** {preconditions}\n\n"
        md_content += f"**Passos:**\n\n{steps}\n\n"
        md_content += f"**Resultado Esperado:**\n\n{expected}\n\n"
        md_content += "---\n\n"

    md_content += "*Gerado automaticamente pelo QA & Requisitos Hub*"
    return md_content


def export_to_html(data: list[dict], title: str = "Relatório") -> str:
    """Converte a lista de casos de teste em um arquivo HTML estilizado

    Suporta automaticamente Dark Mode e Light Mode com base nas preferências do dispositivo/navegador.
    """
    if not data:
        return f"<html><body><h2>{title}</h2><p>Nenhum dado disponível.</p></body></html>"

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        /* === TEMA LIGHT (PADRÃO) === */
        :root {{
            --bg-color: #F0F2F6;
            --text-color: #31333F;
            --title-color: #0E1117;
            --card-bg: #FFFFFF;
            --card-border: #E6E8EB;
            --card-shadow: rgba(0, 0, 0, 0.05);
            --badge-bg: #EAECEF;
            --badge-text: #0E1117;
            --badge-border: #D0D4DC;
            --block-bg: #F8F9FA;
            --block-text: #262730;
            --block-border: #FF4B4B;
            --label-color: #0E1117;
        }}

        /* === TEMA DARK (AUTOMÁTICO SE O NAVEGADOR/OS ESTIVER EM DARK MODE) === */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #0E1117;
                --text-color: #DBDBDB;
                --title-color: #FAFAFA;
                --card-bg: #262730;
                --card-border: #31333F;
                --card-shadow: rgba(0, 0, 0, 0.3);
                --badge-bg: #1A1C24;
                --badge-text: #00D4B1;
                --badge-border: #31333F;
                --block-bg: #1A1C24;
                --block-text: #E0E0E0;
                --block-border: #FF4B4B;
                --label-color: #FAFAFA;
            }}
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: var(--text-color);
            background-color: var(--bg-color);
            padding: 30px;
            max-width: 900px;
            margin: 0 auto;
            transition: background-color 0.3s, color 0.3s;
        }}
        h2 {{
            color: var(--title-color);
            border-bottom: 2px solid var(--card-border);
            padding-bottom: 10px;
            margin-bottom: 25px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            color: var(--text-color);
            box-shadow: 0 4px 6px var(--card-shadow);
        }}
        .card-header {{
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--title-color);
        }}
        .field {{
            margin-bottom: 12px;
            font-size: 14px;
            line-height: 1.6;
        }}
        .badge {{
            background-color: var(--badge-bg);
            color: var(--badge-text);
            padding: 3px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            border: 1px solid var(--badge-border);
        }}
        .content-block {{
            white-space: pre-wrap;
            background-color: var(--block-bg);
            padding: 12px;
            border-radius: 6px;
            margin-top: 6px;
            border-left: 3px solid var(--block-border);
            font-size: 13px;
            color: var(--block-text);
        }}
        .bold {{
            font-weight: 600;
            color: var(--label-color);
        }}
    </style>
</head>
<body>
    <h2>{title}</h2>
"""

    for item in data:
        status = item.get("status", "Não Executado")
        status_icon = (
            "🟢"
            if status == "Passou"
            else ("🔴" if status == "Falhou" else ("🟡" if status == "Bloqueado" else "⚪"))
        )

        test_type = item.get("test_type", "Funcional")
        tc_title = item.get("title", "")
        cycle = item.get("test_cycle", "Sem Ciclo")
        preconditions = item.get("preconditions") or "N/A"
        steps = item.get("steps") or "N/A"
        expected = item.get("expected_result") or "N/A"

        html_content += f"""
    <div class="card">
        <div class="card-header">
            <span>{status_icon}</span>
            <span>[{test_type}] - {tc_title}</span>
        </div>

        <div class="field">
            <span class="bold">Tipo:</span> <span class="badge">{test_type}</span>
        </div>

        <div class="field">
            <span class="bold">Ciclo:</span> <span class="badge">{cycle}</span>
        </div>

        <div class="field">
            <span class="bold">Pré-condições:</span> {preconditions}
        </div>

        <div class="field">
            <span class="bold">Passos:</span>
            <div class="content-block">{steps}</div>
        </div>

        <div class="field">
            <span class="bold">Resultado Esperado:</span>
            <div class="content-block">{expected}</div>
        </div>
    </div>
"""

    html_content += """
</body>
</html>
"""
    return html_content
