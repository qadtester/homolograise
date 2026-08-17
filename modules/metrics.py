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

    # Tratamento inicial dos dataframes
    df_tc = pd.DataFrame(test_cases)
    df_bugs = pd.DataFrame(bug_reports)
    df_risks = pd.DataFrame(risk_matrix)
    df_stories = pd.DataFrame(user_stories)

    # ------------------------------------------
    # 0. FILTRO DE ESCOPO (GERAL vs POR CICLO / RELEASE)
    # ------------------------------------------
    st.markdown("### 🔍 Escopo de Análise")
    
    cycles = ["Geral (Todas as Releases)"]
    if not df_tc.empty and "test_cycle" in df_tc.columns:
        unique_tc_cycles = set(df_tc["test_cycle"].dropna().unique())
        unique_bug_cycles = set(df_bugs["test_cycle"].dropna().unique()) if not df_bugs.empty and "test_cycle" in df_bugs.columns else set()
        all_cycles = sorted(list(unique_tc_cycles.union(unique_bug_cycles)))
        cycles.extend([c for c in all_cycles if c and c != "Geral"])

    selected_cycle = st.selectbox("Selecione o Ciclo de Teste / Release para análise:", cycles, key="metrics_cycle_select")

    # Aplicação de filtros contextuais
    if selected_cycle != "Geral (Todas as Releases)":
        df_tc_filtered = df_tc[df_tc["test_cycle"] == selected_cycle] if not df_tc.empty and "test_cycle" in df_tc.columns else df_tc.copy()
        df_bugs_filtered = df_bugs[df_bugs["test_cycle"] == selected_cycle] if not df_bugs.empty and "test_cycle" in df_bugs.columns else df_bugs.copy()
        scope_label = f"Release / Ciclo: {selected_cycle}"
    else:
        df_tc_filtered = df_tc.copy()
        df_bugs_filtered = df_bugs.copy()
        scope_label = "Visão Geral (Projeto Inteiro)"

    st.info(f"📌 Escopo ativo atual: **{scope_label}**")
    st.divider()

    # Cálculo de Métricas Consolidadas
    total_tc = len(df_tc_filtered)
    passed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Passou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    failed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Falhou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    blocked_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Bloqueado"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    unexecuted_tc = len(df_tc_filtered[df_tc_filtered["status"].isin(["Não Executado", "Pendente"])]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else (total_tc - passed_tc - failed_tc - blocked_tc)

    rate = (passed_tc / total_tc * 100) if total_tc > 0 else 0.0
    
    # Cobertura de Histórias de Usuário (RTM)
    total_stories = len(df_stories)
    stories_with_tc = 0
    if not df_stories.empty and not df_tc.empty and "user_story_id" in df_tc.columns and "id" in df_stories.columns:
        covered_ids = df_tc["user_story_id"].dropna().unique()
        stories_with_tc = len(df_stories[df_stories["id"].isin(covered_ids)])
    coverage_rate = (stories_with_tc / total_stories * 100) if total_stories > 0 else 0.0

    # Bugs
    bugs_total = len(df_bugs_filtered)
    bugs_open = len(df_bugs_filtered[df_bugs_filtered["status"].isin(["Aberto", "Em correção", "Reaberto"])]) if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns else bugs_total
    bugs_closed = len(df_bugs_filtered[df_bugs_filtered["status"].isin(["Fechado", "Passou", "Resolvido"])]) if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns else 0

    # Riscos
    high_risks = len(df_risks[df_risks["risk_score"] >= 15]) if not df_risks.empty and "risk_score" in df_risks.columns else 0

    # ------------------------------------------
    # 1. ANÁLISE DE SAÚDE E RISCOS DA RELEASE (IA)
    # ------------------------------------------
    st.subheader(f"🤖 Parecer Executivo de Qualidade & IA ({scope_label})")
    
    if "ai_analysis_result" not in st.session_state:
        st.session_state["ai_analysis_result"] = None

    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        if st.button("✨ Gerar Parecer Executivo via IA", type="primary", use_container_width=True):
            with st.spinner(f"Consolidando métricas e executando análise diagnóstica..."):
                prompt = f"""
                Atue como um QA Lead especialista sênior. Analise estes dados consolidados do projeto para o escopo '{selected_cycle}' e elabore um parecer executivo de alta qualidade:

                - Escopo/Ciclo Analisado: {selected_cycle}
                - Casos de Teste: {total_tc} total (Passaram: {passed_tc}, Falharam: {failed_tc}, Bloqueados: {blocked_tc}, Pendentes: {unexecuted_tc})
                - Taxa de Sucesso dos Testes: {rate:.1f}%
                - Cobertura de Requisitos (Histórias com Testes): {coverage_rate:.1f}% ({stories_with_tc}/{total_stories})
                - Bugs no Escopo: {bugs_total} total ({bugs_open} Abertos/Pendentes, {bugs_closed} Fechados/Corrigidos)
                - Riscos Críticos do Projeto (Score >= 15): {high_risks}

                Forneça de forma estruturada e profissional em Markdown:
                1. **Parecer Geral de Risco para Deploy (Go / No-Go):** Classifique em BAIXO, MÉDIO ou ALTO risco com justificativa técnica embasada nos dados acima.
                2. **Gargalos e Vulnerabilidades Críticas:** Destaque o impacto de testes falhos/bloqueados ou bugs em aberto na estabilidade do release.
                3. **Plano de Ação (Top 3 Recomendações):** Ações diretas e prioritárias para os times de QA, Desenvolvimento e Produto antes do go-live.
                """
                try:
                    res = call_ai_service(prompt)
                    st.session_state["ai_analysis_result"] = res
                except Exception as e:
                    st.session_state["ai_analysis_result"] = None
                    st.warning(f"Servidor de IA indisponível no momento. Exibindo resumo estatístico automatizado. (Erro: {e})")

    if st.session_state["ai_analysis_result"]:
        st.info(st.session_state["ai_analysis_result"])
    else:
        risk_level = "🔴 ALTO RISCO" if high_risks > 2 or failed_tc > 0 or bugs_open > 3 else ("🟡 MÉDIO RISCO" if bugs_open > 0 or unexecuted_tc > 0 else "🟢 BAIXO RISCO")
        st.markdown(f"""
        <div style="background-color: rgba(13, 110, 253, 0.08); padding: 16px; border-radius: 8px; border-left: 5px solid #0D6EFD;">
            <h4 style="margin-top:0;">📊 Resumo Diagnóstico Estatístico</h4>
            <p><b>Avaliação Estimada de Deploy:</b> {risk_level}</p>
            <ul>
                <li><b>Execução de Testes:</b> {passed_tc} aprovados de {total_tc} criados ({rate:.1f}% de taxa de sucesso).</li>
                <li><b>Rastreabilidade de Requisitos:</b> {coverage_rate:.1f}% das Histórias de Usuário possuem ao menos 1 caso de teste associado.</li>
                <li><b>Gestão de Defeitos:</b> {bugs_open} bug(s) em aberto aguardando correção ou validação no ciclo.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ------------------------------------------
    # 2. KPIS PRINCIPAIS
    # ------------------------------------------
    st.subheader(f"🚀 Indicadores Chave de Desempenho (KPIs) - {selected_cycle}")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    
    kpi_col1.metric("Casos de Teste", total_tc)
    kpi_col2.metric("Taxa de Sucesso", f"{rate:.1f}%", delta=f"{passed_tc} aprovados", delta_color="normal" if rate >= 70 else "inverse")
    kpi_col3.metric("Cobertura Requisitos", f"{coverage_rate:.1f}%", help="% de User Stories cobertas por Casos de Teste")
    kpi_col4.metric("Bugs Pendentes", bugs_open, delta=f"{bugs_total} totais", delta_color="inverse" if bugs_open > 0 else "normal")
    kpi_col5.metric("Riscos Críticos", high_risks, help="Riscos com pontuação >= 15")

    st.markdown("---")

    # ------------------------------------------
    # 3. PAINEL VISUAL DE GRÁFICOS (PLOTLY)
    # ------------------------------------------
    st.subheader("📈 Painel Gráfico de Qualidade")

    g1, g2 = st.columns(2)
    
    with g1:
        if not df_tc_filtered.empty and "status" in df_tc_filtered.columns:
            status_counts = df_tc_filtered["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            
            color_map = {
                "Passou": "#198754",
                "Falhou": "#DC3545",
                "Bloqueado": "#FFC107",
                "Não Executado": "#6C757D",
                "Pendente": "#0D6EFD"
            }
            
            fig_tc = px.pie(
                status_counts, 
                values="count", 
                names="status", 
                title=f"Distribuição de Status dos Testes ({selected_cycle})", 
                hole=0.4,
                color="status",
                color_discrete_map=color_map
            )
            fig_tc.update_traces(textposition='inside', textinfo='percent+label+value')
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("Sem dados de testes suficientes para o gráfico neste ciclo.")

    with g2:
        if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns:
            sev_counts = df_bugs_filtered["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            
            sev_color_map = {
                "Crítica": "#DC3545",
                "Alta": "#FD7E14",
                "Média": "#FFC107",
                "Baixa": "#198754"
            }
            
            fig_bugs = px.bar(
                sev_counts, 
                x="severity", 
                y="count",
                title=f"Bugs por Nível de Severidade ({selected_cycle})", 
                color="severity",
                color_discrete_map=sev_color_map,
                text_auto=True
            )
            fig_bugs.update_layout(xaxis_title="Severidade", yaxis_title="Quantidade de Bugs", showlegend=False)
            st.plotly_chart(fig_bugs, use_container_width=True)
        else:
            st.info("Nenhum bug registrado para exibir neste ciclo.")

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
                text_auto=True
            )
            fig_bug_status.update_layout(xaxis_title="Quantidade", yaxis_title="Status", showlegend=False)
            st.plotly_chart(fig_bug_status, use_container_width=True)
        else:
            st.info("Sem dados de status de bugs para o ciclo.")

    with g4:
        cov_data = pd.DataFrame({
            "Categoria": ["Cobertas com Testes", "Sem Testes Mapeados"],
            "Quantidade": [stories_with_tc, max(0, total_stories - stories_with_tc)]
        })
        fig_cov = px.pie(
            cov_data,
            values="Quantidade",
            names="Categoria",
            title="Cobertura de Requisitos (RTM)",
            hole=0.5,
            color="Categoria",
            color_discrete_map={"Cobertas com Testes": "#0D6EFD", "Sem Testes Mapeados": "#DC3545"}
        )
        fig_cov.update_traces(textposition='inside', textinfo='percent+value')
        st.plotly_chart(fig_cov, use_container_width=True)

    if not df_risks.empty and "risk_score" in df_risks.columns:
        st.markdown("### ⚠️ Matriz de Riscos Globais do Projeto (Probabilidade vs Impacto)")
        fig_risks = px.scatter(
            df_risks, 
            x="probability", 
            y="impact", 
            size="risk_score", 
            color="risk_type",
            hover_name="risk_description" if "risk_description" in df_risks.columns else None,
            title="Distribuição da Matriz de Risco",
            labels={"probability": "Probabilidade", "impact": "Impacto"}
        )
        fig_risks.update_layout(xaxis=dict(range=[0, 6]), yaxis=dict(range=[0, 6]))
        st.plotly_chart(fig_risks, use_container_width=True)

    st.divider()

    # ------------------------------------------
    # 4. EXPORTAÇÃO E DOWNLOADS MULTIFORMATO
    # ------------------------------------------
    st.subheader("📥 Central de Exportação de Relatórios Executivos")
    
    analysis_text = st.session_state['ai_analysis_result'] if st.session_state['ai_analysis_result'] else "Análise gerada estatisticamente pela plataforma."

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    # 1. Exportação HTML (Função dedicada no utils/export.py)
    with col_exp1:
        html_report = export_metrics_to_html(
            scope_label=selected_cycle,
            total_tc=total_tc,
            passed_tc=passed_tc,
            failed_tc=failed_tc,
            blocked_tc=blocked_tc,
            unexecuted_tc=unexecuted_tc,
            rate=rate,
            coverage_rate=coverage_rate,
            bugs_total=bugs_total,
            bugs_open=bugs_open,
            bugs_closed=bugs_closed,
            high_risks=high_risks,
            total_stories=total_stories,
            analysis_text=analysis_text
        )
        st.download_button(
            label="🌐 Baixar Relatório Visual (HTML/PDF)",
            data=html_report.encode("utf-8"),
            file_name=f"relatorio_executivo_qa_{selected_cycle.lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True,
            help="Abra o arquivo HTML no navegador e pressione Ctrl+P para salvar em PDF!"
        )

    # 2. Exportação Markdown
    with col_exp2:
        report_md = f"""# Relatório Executivo de QA & Qualidade
## Escopo / Ciclo Analisado: {selected_cycle}

## 📈 Indicadores Chave (KPIs)
- **Casos de Teste no Escopo:** {total_tc}
- **Aprovados:** {passed_tc} | **Falharam:** {failed_tc} | **Bloqueados:** {blocked_tc} | **Pendentes:** {unexecuted_tc}
- **Taxa de Sucesso:** {rate:.1f}%
- **Cobertura de Requisitos:** {coverage_rate:.1f}% ({stories_with_tc}/{total_stories} User Stories)
- **Bugs no Escopo:** {bugs_total} ({bugs_open} Abertos / {bugs_closed} Fechados)
- **Riscos Críticos Mapeados:** {high_risks}

## 🤖 Avaliação de Saúde e Risco da Release
{analysis_text}
"""
        st.download_button(
            label="📄 Baixar Relatório (Markdown)",
            data=report_md,
            file_name=f"relatorio_qa_{selected_cycle.lower().replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # 3. Exportação de Dados em CSV/Excel (Usando a export_to_csv do utils/export.py)
    with col_exp3:
        kpi_list = [{
            "Ciclo": selected_cycle,
            "Total Testes": total_tc,
            "Passaram": passed_tc,
            "Falharam": failed_tc,
            "Bloqueados": blocked_tc,
            "Pendentes": unexecuted_tc,
            "Taxa Sucesso (%)": round(rate, 2),
            "Cobertura Requisitos (%)": round(coverage_rate, 2),
            "Bugs Totais": bugs_total,
            "Bugs Abertos": bugs_open,
            "Bugs Fechados": bugs_closed,
            "Riscos Criticos": high_risks
        }]
        
        csv_metrics = export_to_csv(kpi_list)
        st.download_button(
            label="📊 Baixar Tabela de KPIs (CSV/Excel)",
            data=csv_metrics.encode("utf-8-sig"),
            file_name=f"kpis_qa_{selected_cycle.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
