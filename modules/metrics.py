import pandas as pd
import plotly.express as px
import streamlit as st
from config.ai_config import call_ai_service
from utils.export import export_to_csv, export_metrics_to_html


def render_metrics_dashboard(
    test_cases: list[dict],
    bug_reports: list[dict],
    risk_matrix: list[dict],
    user_stories: list[dict],
):
    st.title("📊 Dashboard Executivo de Métricas & Qualidade")

    # DataFrames
    df_tc = pd.DataFrame(test_cases)
    df_bugs = pd.DataFrame(bug_reports)
    df_risks = pd.DataFrame(risk_matrix)

    # Inicialização das variáveis de gráfico (evita UnboundLocalError e envio como None)
    fig_tc = None
    fig_bugs = None
    fig_bug_status = None
    fig_type = None
    fig_risks = None

    # ------------------------------------------
    # 0. FILTRO DE ESCOPO (GERAL vs CICLO / RELEASE)
    # ------------------------------------------
    st.markdown("### 🔍 Escopo da Análise")
    
    cycles = ["Geral (Todas as Releases)"]
    if not df_tc.empty and "test_cycle" in df_tc.columns:
        unique_tc_cycles = set(df_tc["test_cycle"].dropna().unique())
        unique_bug_cycles = set(df_bugs["test_cycle"].dropna().unique()) if not df_bugs.empty and "test_cycle" in df_bugs.columns else set()
        all_cycles = sorted(list(unique_tc_cycles.union(unique_bug_cycles)))
        cycles.extend([c for c in all_cycles if c and c != "Geral"])

    selected_cycle = st.selectbox("Selecione o Ciclo de Teste / Release:", cycles, key="metrics_cycle_select")

    # Aplicando os filtros
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

    # Métricas de Testes
    total_tc = len(df_tc_filtered)
    passed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Passou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    failed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Falhou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    blocked_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Bloqueado"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    unexecuted_tc = len(df_tc_filtered[df_tc_filtered["status"].isin(["Não Executado", "Pendente"])]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else (total_tc - passed_tc - failed_tc - blocked_tc)

    rate = (passed_tc / total_tc * 100) if total_tc > 0 else 0.0

    # Métricas de Bugs
    bugs_total = len(df_bugs_filtered)
    bugs_open = len(df_bugs_filtered[df_bugs_filtered["status"].isin(["Aberto", "Em correção", "Reaberto"])]) if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns else bugs_total
    bugs_closed = len(df_bugs_filtered[df_bugs_filtered["status"].isin(["Fechado", "Passou", "Resolvido"])]) if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns else 0
    
    bugs_critical = len(df_bugs_filtered[df_bugs_filtered["severity"].isin(["Crítica", "Alta"]) & df_bugs_filtered["status"].isin(["Aberto", "Em correção", "Reaberto"])]) if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns and "status" in df_bugs_filtered.columns else 0

    # Riscos
    high_risks = len(df_risks[df_risks["risk_score"] >= 15]) if not df_risks.empty and "risk_score" in df_risks.columns else 0

    # ------------------------------------------
    # 1. ANÁLISE DE SAÚDE E PARECER DE IA
    # ------------------------------------------
    st.subheader(f"🤖 Parecer Diagnóstico de Qualidade")
    
    if "ai_analysis_result" not in st.session_state:
        st.session_state["ai_analysis_result"] = None

    col_btn, _ = st.columns([2, 3])
    with col_btn:
        if st.button("✨ Gerar Parecer do QA Lead via IA", type="primary", use_container_width=True):
            with st.spinner("Analisando indicadores do projeto..."):
                prompt = f"""
                Atue como um QA Lead especialista. Analise os dados consolidados para o escopo '{selected_cycle}' e apresente um parecer objetivo:

                - Escopo/Ciclo: {selected_cycle}
                - Casos de Teste: {total_tc} no total ({passed_tc} Passaram, {failed_tc} Falharam, {blocked_tc} Bloqueados, {unexecuted_tc} Pendentes)
                - Taxa de Sucesso: {rate:.1f}%
                - Bugs: {bugs_total} no total ({bugs_open} em Aberto, dos quais {bugs_critical} são de severidade Alta/Crítica)
                - Riscos Críticos do Projeto (Score >= 15): {high_risks}

                Elabore em Markdown neutro e executivo:
                1. **Avaliação para Deploy (Go / No-Go):** Classificação do risco em BAIXO, MÉDIO ou ALTO com justificativa direta.
                2. **Pontos de Atenção:** Impacto dos testes com falha/bloqueios e bugs abertos.
                3. **Recomendações (Top 3):** Próximos passos imediatos para o time.
                """
                try:
                    res = call_ai_service(prompt)
                    st.session_state["ai_analysis_result"] = res
                except Exception as e:
                    st.session_state["ai_analysis_result"] = None
                    st.warning(f"Servidor de IA indisponível. Exibindo diagnóstico automatizado. ({e})")

    if st.session_state["ai_analysis_result"]:
        st.info(st.session_state["ai_analysis_result"])
    else:
        # Avaliação de risco simplificada
        if high_risks > 2 or failed_tc > 3 or bugs_critical > 0:
            risk_badge = "🔴 ALTO RISCO PARA DEPLOY"
            card_border = "#E53E3E"
            card_bg = "rgba(229, 62, 62, 0.05)"
        elif bugs_open > 0 or failed_tc > 0 or blocked_tc > 0 or unexecuted_tc > 0:
            risk_badge = "🟡 MÉDIO RISCO PARA DEPLOY"
            card_border = "#DD6B20"
            card_bg = "rgba(221, 107, 32, 0.05)"
        else:
            risk_badge = "🟢 BAIXO RISCO PARA DEPLOY"
            card_border = "#38A169"
            card_bg = "rgba(56, 161, 105, 0.05)"

        exec_progress = f"{passed_tc} aprovados de {total_tc} executados ({rate:.1f}% de taxa de sucesso)" if total_tc > 0 else "Nenhum teste executado neste ciclo."
        bugs_summary = f"{bugs_open} bug(s) em aberto ({bugs_critical} de severidade Alta/Crítica)" if bugs_open > 0 else "Nenhum bug em aberto no momento."

        st.markdown(f"""
        <div style="background-color: {card_bg}; padding: 18px; border-radius: 8px; border-left: 4px solid {card_border}; margin-bottom: 20px;">
            <div style="font-size: 15px; font-weight: 600; color: #2D3748; margin-bottom: 10px;">
                📊 Resumo Diagnóstico Estatístico
            </div>
            <div style="font-size: 14px; margin-bottom: 12px;">
                <b>Status de Deploy Estimado:</b> &nbsp; <code>{risk_badge}</code>
            </div>
            <div style="font-size: 13.5px; line-height: 1.7;">
                • <b>Execução de Testes:</b> {exec_progress}<br>
                • <b>Gargalos de Execução:</b> {failed_tc} teste(s) falhado(s), {blocked_tc} bloqueado(s) e {unexecuted_tc} pendente(s)<br>
                • <b>Gestão de Defeitos:</b> {bugs_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ------------------------------------------
    # 2. KPIS PRINCIPAIS
    # ------------------------------------------
    st.subheader(f"🚀 Indicadores Chave (KPIs)")
    
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Total de Testes", total_tc)
    k2.metric("Taxa de Sucesso", f"{rate:.1f}%", delta=f"{passed_tc} aprovados", delta_color="normal" if rate >= 70 else "inverse")
    k3.metric("Testes com Falha", failed_tc, delta=f"{blocked_tc} bloqueados", delta_color="inverse" if failed_tc > 0 else "off")
    k4.metric("Bugs Abertos", bugs_open, delta=f"{bugs_critical} críticos/altos", delta_color="inverse" if bugs_open > 0 else "normal")
    k5.metric("Riscos Críticos", high_risks, help="Riscos com pontuação >= 15 na Matriz")

    st.markdown("---")

    # ------------------------------------------
    # 3. PAINEL GRÁFICO
    # ------------------------------------------
    st.subheader("📈 Visualização Geral de Qualidade")

    g1, g2 = st.columns(2)
    
    soft_tc_colors = {
        "Passou": "#48BB78",
        "Falhou": "#F56565",
        "Bloqueado": "#ECC94B",
        "Não Executado": "#CBD5E0",
        "Pendente": "#4299E1"
    }

    soft_sev_colors = {
        "Crítica": "#E53E3E",
        "Alta": "#ED8936",
        "Média": "#ECC94B",
        "Baixa": "#48BB78"
    }

    with g1:
        if not df_tc_filtered.empty and "status" in df_tc_filtered.columns:
            status_counts = df_tc_filtered["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            
            fig_tc = px.pie(
                status_counts, 
                values="count", 
                names="status", 
                title=f"Distribuição do Status dos Testes", 
                hole=0.45,
                color="status",
                color_discrete_map=soft_tc_colors
            )
            fig_tc.update_traces(textposition='inside', textinfo='percent+value')
            fig_tc.update_layout(margin=dict(t=40, b=20, l=10, r=10))
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
                title=f"Bugs por Severidade", 
                color="severity",
                color_discrete_map=soft_sev_colors,
                text_auto=True
            )
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
                title="Status de Resolução dos Bugs",
                color="status",
                color_discrete_sequence=["#4299E1", "#ED8936", "#48BB78", "#A0AEC0"],
                text_auto=True
            )
            fig_bug_status.update_layout(
                xaxis_title="Quantidade", 
                yaxis_title="", 
                showlegend=False,
                margin=dict(t=40, b=20, l=10, r=10)
            )
            st.plotly_chart(fig_bug_status, use_container_width=True)
        else:
            st.info("Sem dados de resolução de bugs no ciclo.")

    with g4:
        if not df_tc_filtered.empty and "test_type" in df_tc_filtered.columns:
            type_counts = df_tc_filtered["test_type"].value_counts().reset_index()
            type_counts.columns = ["test_type", "count"]
            
            fig_type = px.pie(
                type_counts,
                values="count",
                names="test_type",
                title="Tipos de Testes Criados",
                hole=0.45,
                color_discrete_sequence=["#667EEA", "#ED64A6", "#4299E1", "#38B2AC"]
            )
            fig_type.update_traces(textposition='inside', textinfo='percent+value')
            fig_type.update_layout(margin=dict(t=40, b=20, l=10, r=10))
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("Sem dados de tipos de testes.")

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
            color_discrete_sequence=["#E53E3E", "#ED8936", "#4299E1", "#48BB78"]
        )
        fig_risks.update_layout(xaxis=dict(range=[0, 6]), yaxis=dict(range=[0, 6]))
        st.plotly_chart(fig_risks, use_container_width=True)

    st.divider()

    # ------------------------------------------
    # 4. EXPORTAÇÃO DE RELATÓRIOS
    # ------------------------------------------
    st.subheader("📥 Central de Exportação")
    
    analysis_text = st.session_state['ai_analysis_result'] if st.session_state['ai_analysis_result'] else "Análise gerada com base nos dados estatísticos do projeto."

    exp1, exp2, exp3 = st.columns(3)

    # 1. Exportação HTML com Gráficos Incorporados
    with exp1:
        html_report = export_metrics_to_html(
            scope_label=selected_cycle,
            total_tc=total_tc,
            passed_tc=passed_tc,
            failed_tc=failed_tc,
            blocked_tc=blocked_tc,
            unexecuted_tc=unexecuted_tc,
            rate=rate,
            bugs_total=bugs_total,
            bugs_open=bugs_open,
            bugs_closed=bugs_closed,
            high_risks=high_risks,
            analysis_text=analysis_text,
            fig_tc=fig_tc,             # 👈 PASSANDO OS OBJETOS DE GRÁFICO
            fig_bugs=fig_bugs,         # 👈 PASSANDO OS OBJETOS DE GRÁFICO
            fig_status=fig_bug_status, # 👈 PASSANDO OS OBJETOS DE GRÁFICO
            fig_type=fig_type,         # 👈 PASSANDO OS OBJETOS DE GRÁFICO
            fig_risks=fig_risks        # 👈 PASSANDO OS OBJETOS DE GRÁFICO
        )
        st.download_button(
            label="🌐 Baixar Relatório (HTML/PDF)",
            data=html_report.encode("utf-8"),
            file_name=f"relatorio_qa_{selected_cycle.lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True,
            help="Abra o arquivo HTML no navegador e pressione Ctrl+P para salvar em PDF."
        )

    # 2. Exportação Markdown
    with exp2:
        report_md = f"""# Relatório Executivo de QA & Qualidade
## Escopo / Ciclo Analisado: {selected_cycle}

## 📈 Indicadores Chave (KPIs)
- **Total de Casos de Teste:** {total_tc}
- **Aprovados:** {passed_tc} | **Falharam:** {failed_tc} | **Bloqueados:** {blocked_tc} | **Pendentes:** {unexecuted_tc}
- **Taxa de Sucesso:** {rate:.1f}%
- **Bugs Cadastrados:** {bugs_total} ({bugs_open} Abertos / {bugs_closed} Fechados / {bugs_critical} Críticos ou Altos)
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

    # 3. Exportação CSV
    with exp3:
        kpi_list = [{
            "Ciclo": selected_cycle,
            "Total Testes": total_tc,
            "Passaram": passed_tc,
            "Falharam": failed_tc,
            "Bloqueados": blocked_tc,
            "Pendentes": unexecuted_tc,
            "Taxa Sucesso (%)": round(rate, 2),
            "Bugs Totais": bugs_total,
            "Bugs Abertos": bugs_open,
            "Bugs Criticos/Altos": bugs_critical,
            "Bugs Fechados": bugs_closed,
            "Riscos Criticos": high_risks
        }]
        
        csv_metrics = export_to_csv(kpi_list)
        st.download_button(
            label="📊 Baixar Tabela de KPIs (CSV)",
            data=csv_metrics.encode("utf-8-sig"),
            file_name=f"kpis_qa_{selected_cycle.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
