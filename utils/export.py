import base64
import pandas as pd
import plotly.io as pio


def export_to_csv(data: list[dict]) -> str:
    """Converte a lista em formato CSV (compatível com Excel)."""
    if not data:
        return ""

    df = pd.DataFrame(data)
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig")


def export_to_markdown(data: list[dict], title: str = "Relatório", is_bug_report: bool = False) -> str:
    """Converte em Markdown estruturado."""
    if not data:
        return f"# {title}\n\n*Nenhum dado disponível.*"

    md_content = f"# {title}\n\n"

    if is_bug_report:
        for bug in data:
            sev = bug.get("severity", "Média")
            sev_color = "🔴" if sev in ["Alta", "Crítica"] else ("🟡" if sev == "Média" else "🟢")
            bug_title = bug.get("title", "")
            status = bug.get("status", "Aberto")
            cycle = bug.get("test_cycle", "Sem Ciclo")
            description = bug.get("description") or "N/A"
            steps = bug.get("steps") or "N/A"
            expected = bug.get("expected_behavior") or "N/A"
            actual = bug.get("actual_behavior") or "N/A"

            md_content += f"### {sev_color} [{sev}] {bug_title} - Status: `{status}`\n"
            md_content += f"- **Ciclo / Release:** `{cycle}`\n\n"
            md_content += f"**Descrição:**\n\n{description}\n\n"
            md_content += f"**Passos para Reproduzir:**\n\n{steps}\n\n"
            md_content += f"**Comportamento Esperado:** {expected}\n\n"
            md_content += f"**Comportamento Atual:** {actual}\n\n"
            md_content += "---\n\n"
    else:
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


def export_to_html(data: list[dict], title: str = "Relatório", is_bug_report: bool = False) -> str:
    """Converte em HTML idêntico à tela do software (com suporte automático a Dark/Light mode)."""
    if not data:
        return f"<!DOCTYPE html><html><body><h2>{title}</h2><p>Nenhum dado disponível.</p></body></html>"

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
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

    if is_bug_report:
        for bug in data:
            sev = bug.get("severity", "Média")
            sev_color = "🔴" if sev in ["Alta", "Crítica"] else ("🟡" if sev == "Média" else "🟢")
            bug_title = bug.get("title", "")
            status = bug.get("status", "Aberto")
            cycle = bug.get("test_cycle", "Sem Ciclo")
            description = bug.get("description") or "N/A"
            steps = bug.get("steps") or "N/A"
            expected = bug.get("expected_behavior") or "N/A"
            actual = bug.get("actual_behavior") or "N/A"

            html_content += f"""
    <div class="card">
        <div class="card-header">
            <span>{sev_color}</span>
            <span>[{sev}] {bug_title} - Status: <span class="badge">{status}</span></span>
        </div>

        <div class="field">
            <span class="bold">Ciclo / Release:</span> <span class="badge">{cycle}</span>
        </div>

        <div class="field">
            <span class="bold">Descrição:</span>
            <div class="content-block">{description}</div>
        </div>

        <div class="field">
            <span class="bold">Passos para Reproduzir:</span>
            <div class="content-block">{steps}</div>
        </div>

        <div class="field">
            <span class="bold">Comportamento Esperado:</span> {expected}
        </div>

        <div class="field">
            <span class="bold">Comportamento Atual:</span> {actual}
        </div>
    </div>
"""
    else:
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
    return html_content  # 👈 ADICIONADO: Retorno explícito para evitar AttributeError no Streamlit


def export_metrics_to_html(
    scope_label: str,
    total_tc: int,
    passed_tc: int,
    failed_tc: int,
    blocked_tc: int,
    unexecuted_tc: int,
    rate: float,
    bugs_total: int,
    bugs_open: int,
    bugs_closed: int,
    high_risks: int,
    analysis_text: str,
    fig_tc=None,
    fig_bugs=None,
    fig_status=None,
    fig_type=None,
    fig_risks=None,
) -> str:
    """Gera um relatório executivo de métricas em HTML com gráficos totalmente incorporados."""

    rate_color = "#2E7D32" if rate >= 80 else ("#ED6C02" if rate >= 60 else "#D32F2F")
    bugs_color = "#D32F2F" if bugs_open > 0 else "#2E7D32"

    def fig_to_html_div(fig):
        if fig is None:
            return '<div class="graph-box" style="display:flex;align-items:center;justify-content:center;height:250px;color:#A0AEC0;">Sem dados para exibir</div>'
        
        try:
            # Força o fundo limpo para o relatório exportado
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                template="plotly_white"
            )
            # Converte com div responsiva
            div_html = pio.to_html(
                fig,
                include_plotlyjs=False,
                full_html=False,
                config={"responsive": True, "displayModeBar": False},
            )
            return f'<div class="graph-box">{div_html}</div>'
        except Exception as e:
            return f'<div class="graph-box" style="color:#E53E3E;padding:20px;">Não foi possível renderizar o gráfico ({e})</div>'

    html_fig_tc = fig_to_html_div(fig_tc)
    html_fig_bugs = fig_to_html_div(fig_bugs)
    html_fig_status = fig_to_html_div(fig_status)
    html_fig_type = fig_to_html_div(fig_type)
    html_fig_risks = fig_to_html_div(fig_risks) if fig_risks is not None else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Executivo de QA - {scope_label}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg-color: #F8F9FA;
            --text-color: #2D3748;
            --title-color: #1A202C;
            --card-bg: #FFFFFF;
            --card-border: #E2E8F0;
            --card-shadow: rgba(0, 0, 0, 0.03);
            --primary-color: #3182CE;
            --primary-bg-light: #EBF8FF;
            --block-bg: #EDF2F7;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #12161A;
                --text-color: #CBD5E0;
                --title-color: #F7FAFC;
                --card-bg: #1A202C;
                --card-border: #2D3748;
                --card-shadow: rgba(0, 0, 0, 0.2);
                --primary-color: #63B3ED;
                --primary-bg-light: #1A2634;
                --block-bg: #2D3748;
            }}
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: var(--text-color);
            background-color: var(--bg-color);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 15px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 22px; color: var(--title-color); font-weight: 600; }}
        .badge-scope {{
            background: var(--primary-bg-light);
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
            padding: 5px 12px;
            border-radius: 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 4px var(--card-shadow);
        }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.75; font-weight: 600; }}
        .kpi-value {{ font-size: 26px; font-weight: 700; margin: 6px 0; color: var(--primary-color); }}
        .section-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px var(--card-shadow);
        }}
        .section-title {{ font-size: 16px; margin-top: 0; margin-bottom: 12px; color: var(--title-color); font-weight: 600; }}
        .analysis-content {{
            white-space: pre-wrap;
            background: var(--block-bg);
            padding: 14px;
            border-left: 3px solid var(--primary-color);
            border-radius: 4px;
            font-size: 13.5px;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .graph-box {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 2px 4px var(--card-shadow);
            overflow: hidden;
            min-height: 300px;
        }}
        ul.detail-list {{ padding-left: 20px; margin: 0; }}
        ul.detail-list li {{ margin-bottom: 6px; font-size: 13.5px; }}
        .footer {{ text-align: center; font-size: 12px; opacity: 0.5; margin-top: 30px; }}
        
        @media print {{
            body {{ padding: 0; background: #FFF; color: #000; }}
            .charts-grid {{ page-break-inside: avoid; display: block; }}
            .graph-box {{ page-break-inside: avoid; margin-bottom: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Relatório Executivo de Qualidade (QA)</h1>
        <span class="badge-scope">{scope_label}</span>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Taxa de Sucesso</div>
            <div class="kpi-value" style="color: {rate_color};">{rate:.1f}%</div>
            <small>{passed_tc} de {total_tc} testes passados</small>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Bugs Abertos</div>
            <div class="kpi-value" style="color: {bugs_color};">{bugs_open}</div>
            <small>{bugs_total} bugs cadastrados</small>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Testes Com Falha</div>
            <div class="kpi-value" style="color: #D32F2F;">{failed_tc}</div>
            <small>{blocked_tc} bloqueados / {unexecuted_tc} pendentes</small>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Riscos Críticos</div>
            <div class="kpi-value" style="color: #E53E3E;">{high_risks}</div>
            <small>Score de Risco &ge; 15</small>
        </div>
    </div>

    <div class="section-card">
        <h2 class="section-title">🤖 Parecer Executivo de Qualidade</h2>
        <div class="analysis-content">{analysis_text}</div>
    </div>

    <h2 style="font-size: 18px; color: var(--title-color); margin-top: 25px; margin-bottom: 15px;">📈 Painel de Gráficos de Qualidade</h2>
    <div class="charts-grid">
        {html_fig_tc}
        {html_fig_bugs}
        {html_fig_status}
        {html_fig_type}
    </div>

    {f'<div style="margin-bottom: 20px;">{html_fig_risks}</div>' if html_fig_risks else ""}

    <div class="section-card">
        <h2 class="section-title">📋 Resumo de Execução do Escopo</h2>
        <ul class="detail-list">
            <li><b>Total de Casos de Teste:</b> {total_tc}</li>
            <li><b>Aprovados (Passou):</b> {passed_tc}</li>
            <li><b>Falhas Detectadas:</b> {failed_tc}</li>
            <li><b>Bloqueios de Execução:</b> {blocked_tc}</li>
            <li><b>Pendentes de Execução:</b> {unexecuted_tc}</li>
            <li><b>Bugs Resolvidos / Corrigidos:</b> {bugs_closed}</li>
        </ul>
    </div>

    <div class="footer">
        Gerado pela plataforma QA & Requisitos Hub
    </div>
</body>
</html>"""
