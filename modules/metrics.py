import pandas as pd
import plotly.express as px
import streamlit as st
from config.ai_config import call_ai_service
from utils.export import export_metrics_to_html, export_to_csv


def render_metrics_dashboard(
    test_cases: list[dict],
    bug_reports: list[dict],
    risk_matrix: list[dict],
    user_stories: list[dict],
):
    st.title("📊 Dashboard Executivo de Métricas & Qualidade")

    # DataFrames base
    df_tc = pd.DataFrame(test_cases)
    df_bugs = pd.DataFrame(bug_reports)
    df_risks = pd.DataFrame(risk_matrix)

    # --------------------------------------------------------------------------
    # PALETA DE CORES ELEGANTES E SUAVES (Design System / Modern Palette)
    # --------------------------------------------------------------------------
    COLOR_MAP = {
        "Passou": "#4ADE80",        # Verde Menta Suave
        "Fechado": "#22C55E",       # Verde Sólido
        "Resolvido": "#10B981",     # Esmeralda
        "Falhou": "#F87171",        # Vermelho Coral Suave
        "Bloqueado": "#FBBF24",     # Âmbar / Amarelo
        "Não Executado": "#9CA3AF", # Cinza Neutro
        "Pendente": "#60A5FA",      # Azul Celeste
        "Aberto": "#3B82F6",       # Azul Royal
        "Em correção": "#818CF8",   # Índigo Suave
        "Reaberto": "#FB923C",     # Laranja Suave
    }

    SEVERITY_COLORS = {
        "Crítica": "#EF4444",      # Vermelho Suave
        "Alta": "#F97316",         # Laranja
        "Média": "#FBBF24",        # Âmbar
        "Baixa": "#34D399",        # Menta
    }

    # Inicialização dos gráficos
    fig_tc = None
    fig_bugs = None
    fig_bug_status = None
    fig_type = None
    fig_risks = None

    # --------------------------------------------------------------------------
    # 0. FILTRO DE ESCOPO
    # --------------------------------------------------------------------------
    st.markdown("### 🔍 Escopo da Análise")

    cycles = ["Geral (Todas as Releases)"]
    if not df_tc.empty and "test_cycle" in df_tc.columns:
        tc_cycles = set(df_tc["test_cycle"].dropna().unique())
        bug_cycles = set(df_bugs["test_cycle"].dropna().unique()) if not df_bugs.empty and "test_cycle" in df_bugs.columns else set()
        all_cycles = sorted(list(tc_cycles.union(bug_cycles)))
        cycles.extend([c for c in all_cycles if c and c != "Geral"])

    selected_cycle = st.selectbox("Selecione o Ciclo de Teste / Release:", cycles, key="metrics_cycle_select")

    # Aplicando escopo
    if selected_cycle != "Geral (Todas as Releases)":
        df_tc_filtered = df_tc[df_tc["test_cycle"] == selected_cycle] if not df_tc.empty and "test_cycle" in df_tc.columns else df_tc.copy()
        df_bugs_filtered = df_bugs[df_bugs["test_cycle"] == selected_cycle] if not df_bugs.empty and "test_cycle" in df_bugs.columns else df_bugs.copy()
        scope_label = f"Release / Ciclo: {selected_cycle}"
    else:
        df_tc_filtered = df_tc.copy()
        df_bugs_filtered = df_bugs.copy()
        scope_label = "Visão Geral (Projeto Inteiro)"

    st.caption(f"📌 Escopo ativo: **{scope_label}**")
    st.divider()

    # --------------------------------------------------------------------------
    # 1. PROCESSAMENTO ESTATÍSTICO DE DADOS
    # --------------------------------------------------------------------------
    
    # --- A. CASOS DE TESTE ---
    total_tc = len(df_tc_filtered)
    passed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Passou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    failed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Falhou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    blocked_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Bloqueado"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    unexecuted_tc = len(df_tc_filtered[df_tc_filtered["status"].isin(["Não Executado", "Pendente"])]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else (total_tc - passed_tc - failed_tc - blocked_tc)

    executed_tc = passed_tc + failed_tc + blocked_tc
    execution_rate = (executed_tc / total_tc * 100) if total_tc > 0 else 0.0
    pass_rate = (passed_tc / executed_tc * 100) if executed_tc > 0 else 0.0

    # --- B. DEFEYTOS / BUGS (MODELO RIGOROSO DE CICLO DE VIDA) ---
    bugs_total_mapped = len(df_bugs_filtered) # MANTÉM O HISTÓRICO COMPLETO DA RELEASE
    
    STATUS_OPEN = ["Aberto", "Em correção", "Reaberto", "Em Andamento"]
    STATUS_CLOSED = ["Fechado", "Passou", "Resolvido", "Concluído", "Cancelado"]

    if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns:
        bugs_open = len(df_bugs_filtered[df_bugs_filtered["status"].isin(STATUS_OPEN)])
        bugs_closed = len(df_bugs_filtered[df_bugs_filtered["status"].isin(STATUS_CLOSED)])
    else:
        bugs_open = 0
        bugs_closed = 0

    if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns and "status" in df_bugs_filtered.columns:
        bugs_critical_open = len(df_bugs_filtered[
            df_bugs_filtered["severity"].isin(["Crítica", "Alta"]) & 
            df_bugs_filtered["status"].isin(STATUS_OPEN)
        ])
    else:
        bugs_critical_open = 0

    fix_rate = (bugs_closed / bugs_total_mapped * 100) if bugs_total_mapped > 0 else 100.0

    # Cálculo do Índice Ponderado de Severidade (PDR - Weighted Defect Score)
    weights = {"Crítica": 4, "Alta": 3, "Média": 2, "Baixa": 1}
    weighted_defect_score = 0
    if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns:
        open_bugs_df = df_bugs_filtered[df_bugs_filtered["status"].isin(STATUS_OPEN)]
        weighted_defect_score = open_bugs_df["severity"].map(weights).fillna(1).sum()

    # --- C. RISCOS ---
    high_risks = len(df_risks[df_risks["risk_score"] >= 15]) if not df_risks.empty and "risk_score" in df_risks.columns else 0

    # --------------------------------------------------------------------------
    # 2. ANÁLISE DE SAÚDE E PARECER DE IA
    # --------------------------------------------------------------------------
    st.subheader("🤖 Parecer Diagnóstico de Qualidade")

    if "ai_analysis_result" not in st.session_state:
        st.session_state["ai_analysis_result"] = None

    col_btn, _ = st.columns([2, 3])
    with col_btn:
        if st.button("✨ Gerar Parecer do QA Lead via IA", type="primary", use_container_width=True):
            with st.spinner("Calculando modelo preditivo e análise de riscos..."):
                prompt = f"""
                Atue como um Lead Data Analyst & QA Director. Analise os indicadores do escopo '{selected_cycle}':

                - Cobertura/Execução: {executed_tc}/{total_tc} testes executados ({execution_rate:.1f}% de avanço).
                - Qualidade de Execução: Taxa de Aprovação de {pass_rate:.1f}% nos testes rodados ({passed_tc} Ok, {failed_tc} Falhas, {blocked_tc} Bloqueios).
                - Volume Mapeado de Bugs: {bugs_total_mapped} defeitos associados a esta release.
                - Resolução de Defeitos: {bugs_closed} corrigidos/fechados ({fix_rate:.1f}% de taxa de resolução).
                - Defeitos em Aberto: {bugs_open} pendentes, dos quais {bugs_critical_open} são Críticos/Altos.
                - Carga do Peso de Gravidade de Bugs (PDR Score): {weighted_defect_score} pontos acumulados.
                - Riscos Globais da Matriz (Score >= 15): {high_risks} riscos em nível crítico.

                Instruções de Resposta (Markdown Executivo):
                1. **Decisão de Go / No-Go:** Classificação de Risco (BAIXO, MÉDIO, ALTO) com justificativa baseada nos dados.
                2. **Gargalos e Vulnerabilidades:** Análise combinada de testes falhos/bloqueados e da severidade dos bugs abertos.
                3. **Plano de Ação Sugerido (3 passos):** Ações direcionadas e imediatas.
                """
                try:
                    res = call_ai_service(prompt)
                    st.session_state["ai_analysis_result"] = res
                except Exception as e:
                    st.session_state["ai_analysis_result"] = None
                    st.warning(f"Falha na consulta à IA. Exibindo diagnóstico algorítmico local. ({e})")

    if st.session_state["ai_analysis_result"]:
        st.info(st.session_state["ai_analysis_result"])
    else:
        # Algoritmo Local de Avaliação de Risco
        if high_risks > 2 or bugs_critical_open > 0 or pass_rate < 60.0 or weighted_defect_score >= 12:
            risk_badge = "🔴 ALTO RISCO PARA DEPLOY"
            card_border = "#EF4444"
            card_bg = "rgba(239, 68, 68, 0.12)"
        elif bugs_open > 0 or failed_tc > 0 or blocked_tc > 0 or execution_rate < 80.0:
            risk_badge = "🟡 MÉDIO RISCO PARA DEPLOY"
            card_border = "#F59E0B"
            card_bg = "rgba(245, 158, 11, 0.12)"
        else:
            risk_badge = "🟢 BAIXO RISCO PARA DEPLOY"
            card_border = "#10B981"
            card_bg = "rgba(16, 185, 129, 0.12)"

        st.markdown(f"""
        <div style="background-color: {card_bg}; padding: 18px; border-radius: 8px; border-left: 4px solid {card_border}; margin-bottom: 20px;">
            <div style="font-size: 15px; font-weight: 600; color: var(--text-color, #FAFAFA); margin-bottom: 8px;">
                📊 Avaliação Algorítmica da Release
            </div>
            <div style="font-size: 14px; margin-bottom: 12px; color: var(--text-color, #FAFAFA);">
                <b>Parecer Técnico:</b> &nbsp; <code>{risk_badge}</code>
            </div>
            <div style="font-size: 13.5px; line-height: 1.7; color: rgba(255, 255, 255, 0.85);">
                • <b style="color: #FFFFFF;">Progresso da Suíte:</b> {execution_rate:.1f}% executado ({passed_tc} aprovados de {executed_tc} testados). Taxa de Sucesso: <b style="color: #FFFFFF;">{pass_rate:.1f}%</b>.<br>
                • <b style="color: #FFFFFF;">Saúde dos Defeitos:</b> {bugs_total_mapped} total de bugs reportados na release — <b style="color: #FFFFFF;">{bugs_closed} resolvidos ({fix_rate:.1f}%)</b> e {bugs_open} ativos ({bugs_critical_open} graves).<br>
                • <b style="color: #FFFFFF;">Gravidade Acumulada (PDR):</b> {weighted_defect_score} pontos de severidade ativa.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --------------------------------------------------------------------------
    # 3. KPIS PRINCIPAIS (COM DELTAS E MÉTRICAS RELATIVAS)
    # --------------------------------------------------------------------------
    st.subheader("🚀 Indicadores Chave (KPIs)")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric(
        "Progresso de Execução", 
        f"{execution_rate:.1f}%", 
        delta=f"{executed_tc}/{total_tc} testes",
        delta_color="normal"
    )
    k2.metric(
        "Taxa de Sucesso (Pass)", 
        f"{pass_rate:.1f}%", 
        delta=f"{passed_tc} aprovados", 
        delta_color="normal" if pass_rate >= 80 else "inverse"
    )
    k3.metric(
        "Gargalos de Teste", 
        f"{failed_tc + blocked_tc}", 
        delta=f"{failed_tc} falhas / {blocked_tc} bloq.", 
        delta_color="inverse" if (failed_tc + blocked_tc) > 0 else "off"
    )
    k4.metric(
        "Bugs Mapeados (Abertos)", 
        f"{bugs_open}", 
        delta=f"{bugs_closed} de {bugs_total_mapped} resolvidos", 
        delta_color="normal" if bugs_closed >= bugs_open else "inverse"
    )
    k5.metric(
        "Peso de Severidade (PDR)", 
        weighted_defect_score, 
        delta=f"{bugs_critical_open} críticos/altos", 
        delta_color="inverse" if weighted_defect_score > 5 else "off"
    )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 4. PAINEL GRÁFICO AVANÇADO
    # --------------------------------------------------------------------------
    st.subheader("📈 Visualização de Qualidade & Tendências")

    g1, g2 = st.columns(2)

    with g1:
        if not df_tc_filtered.empty and "status" in df_tc_filtered.columns:
            status_counts = df_tc_filtered["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]

            fig_tc = px.pie(
                status_counts,
                values="count",
                names="status",
                title="Distribuição do Status dos Testes",
                hole=0.5,
                color="status",
                color_discrete_map=COLOR_MAP
            )
            fig_tc.update_traces(textposition='inside', textinfo='percent+value', marker=dict(line=dict(color='#FFFFFF', width=2)))
            fig_tc.update_layout(margin=dict(t=40, b=20, l=10, r=10), showlegend=True)
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("Sem dados de testes no ciclo selecionado.")

    with g2:
        if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns:
            sev_counts = df_bugs_filtered["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]

            fig_bugs = px.bar(
                sev_counts,
                x="severity",
                y="count",
                title="Distribuição de Bugs por Severidade (Total Mapeado)",
                color="severity",
                color_discrete_map=SEVERITY_COLORS,
                text_auto=True
            )
            fig_bugs.update_traces(marker_line_color='rgb(0,0,0)', marker_line_width=0.5, opacity=0.9)
            fig_bugs.update_layout(
                xaxis_title="",
                yaxis_title="Quantidade",
                showlegend=False,
                margin=dict(t=40, b=20, l=10, r=10)
            )
            st.plotly_chart(fig_bugs, use_container_width=True)
        else:
            st.info("Nenhum bug cadastrado neste ciclo.")

    g3, g4 = st.columns(2)

    with g3:
        if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns:
            bug_status_df = df_bugs_filtered["status"].value_counts().reset_index()
            bug_status_df.columns = ["status", "count"]

            fig_bug_status = px.bar(
                bug_status_df,
                x="count",
                y="status",
                orientation="h",
                title="Funil de Resolução dos Bugs da Release",
                color="status",
                color_discrete_map=COLOR_MAP,
                text_auto=True
            )
            fig_bug_status.update_layout(
                xaxis_title="Quantidade de Defeitos",
                yaxis_title="",
                showlegend=False,
                margin=dict(t=40, b=20, l=10, r=10)
            )
            st.plotly_chart(fig_bug_status, use_container_width=True)
        else:
            st.info("Sem dados de status de bugs no ciclo.")

    with g4:
        if not df_tc_filtered.empty and "test_type" in df_tc_filtered.columns:
            type_counts = df_tc_filtered["test_type"].value_counts().reset_index()
            type_counts.columns = ["test_type", "count"]

            fig_type = px.pie(
                type_counts,
                values="count",
                names="test_type",
                title="Distribuição por Tipo de Teste",
                hole=0.5,
                color_discrete_sequence=["#818CF8", "#34D399", "#FBBF24", "#60A5FA"]
            )
            fig_type.update_traces(textposition='inside', textinfo='percent+value', marker=dict(line=dict(color='#FFFFFF', width=2)))
            fig_type.update_layout(margin=dict(t=40, b=20, l=10, r=10))
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("Sem dados de tipos de testes.")

    # Matriz de Riscos
    if not df_risks.empty and "risk_score" in df_risks.columns:
        st.markdown("### ⚠️ Matriz de Riscos Globais do Projeto")
        fig_risks = px.scatter(
            df_risks,
            x="probability",
            y="impact",
            size="risk_score",
            color="risk_type",
            hover_name="risk_description" if "risk_description" in df_risks.columns else None,
            title="Distribuição de Riscos (Probabilidade vs Impacto)",
            labels={"probability": "Probabilidade", "impact": "Impacto"},
            color_discrete_sequence=["#EF4444", "#F97316", "#3B82F6", "#10B981"]
        )
        fig_risks.update_layout(
            xaxis=dict(range=[0, 6], dtick=1), 
            yaxis=dict(range=[0, 6], dtick=1),
            margin=dict(t=40, b=20, l=10, r=10)
        )
        st.plotly_chart(fig_risks, use_container_width=True)

    st.divider()

    # --------------------------------------------------------------------------
    # 5. CENTRAL DE EXPORTAÇÃO
    # --------------------------------------------------------------------------
    st.subheader("📥 Central de Exportação de Relatórios")

    analysis_text = st.session_state['ai_analysis_result'] if st.session_state['ai_analysis_result'] else "Relatório gerado automaticamente com base na análise estatística."

    exp1, exp2, exp3 = st.columns(3)

    with exp1:
        html_report = export_metrics_to_html(
            scope_label=selected_cycle,
            total_tc=total_tc,
            passed_tc=passed_tc,
            failed_tc=failed_tc,
            blocked_tc=blocked_tc,
            unexecuted_tc=unexecuted_tc,
            rate=pass_rate,
            bugs_total=bugs_total_mapped,
            bugs_open=bugs_open,
            bugs_closed=bugs_closed,
            high_risks=high_risks,
            analysis_text=analysis_text,
            fig_tc=fig_tc,
            fig_bugs=fig_bugs,
            fig_status=fig_bug_status,
            fig_type=fig_type,
            fig_risks=fig_risks
        )
        st.download_button(
            label="🌐 Baixar Relatório (HTML / PDF)",
            data=html_report.encode("utf-8"),
            file_name=f"relatorio_qa_{selected_cycle.lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True
        )

    with exp2:
        report_md = f"""# Relatório Executivo de QA & Qualidade
## Escopo / Ciclo Analisado: {selected_cycle}

## 📈 Indicadores Chave (KPIs)
- **Total de Casos de Teste:** {total_tc} ({execution_rate:.1f}% Executados)
- **Aprovados:** {passed_tc} | **Falharam:** {failed_tc} | **Bloqueados:** {blocked_tc} | **Pendentes:** {unexecuted_tc}
- **Taxa de Aprovação:** {pass_rate:.1f}%
- **Total Mapeado de Bugs na Release:** {bugs_total_mapped}
- **Bugs Resolvidos/Fechados:** {bugs_closed} ({fix_rate:.1f}% de taxa de resolução)
- **Bugs em Aberto:** {bugs_open} ({bugs_critical_open} Críticos/Altos)
- **Peso Ponderado de Gravidade (PDR Score):** {weighted_defect_score}
- **Riscos Críticos Mapeados:** {high_risks}

## 🤖 Avaliação Diagnóstica
{analysis_text}
"""
        st.download_button(
            label="📄 Baixar Relatório (Markdown)",
            data=report_md,
            file_name=f"relatorio_qa_{selected_cycle.lower().replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with exp3:
        kpi_list = [{
            "Ciclo": selected_cycle,
            "Total Testes": total_tc,
            "Execucao (%)": round(execution_rate, 2),
            "Taxa Sucesso (%)": round(pass_rate, 2),
            "Passaram": passed_tc,
            "Falharam": failed_tc,
            "Bloqueados": blocked_tc,
            "Pendentes": unexecuted_tc,
            "Bugs Totais Mapeados": bugs_total_mapped,
            "Bugs Resolvidos": bugs_closed,
            "Bugs Abertos": bugs_open,
            "Bugs Criticos Abertos": bugs_critical_open,
            "Taxa Resolucao Defeitos (%)": round(fix_rate, 2),
            "Peso Severidade (PDR)": weighted_defect_score,
            "Riscos Criticos": high_risks
        }]

        csv_metrics = export_to_csv(kpi_list)
        st.download_button(
            label="📊 Baixar KPIs (CSV)",
            data=csv_metrics.encode("utf-8-sig"),
            file_name=f"kpis_qa_{selected_cycle.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
