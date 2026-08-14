import pandas as pd
import plotly.express as px
import streamlit as st
from config.ai_config import call_ai_service

def render_metrics_dashboard(
    test_cases: list[dict],
    bug_reports: list[dict],
    risk_matrix: list[dict],
    user_stories: list[dict],
):
    st.title("📊 Dashboard de Métricas & Exportação")

    # Tratamento inicial dos dataframes
    df_tc = pd.DataFrame(test_cases)
    df_bugs = pd.DataFrame(bug_reports)
    df_risks = pd.DataFrame(risk_matrix)
    df_stories = pd.DataFrame(user_stories)

    # ------------------------------------------
    # 0. FILTRO DE ESCOPO (GERAL vs POR CICLO / RELEASE)
    # ------------------------------------------
    st.markdown("### 🔍 Filtro de Escopo e Ciclo de Teste")
    
    cycles = ["Geral (Todas as Releases)"]
    if not df_tc.empty and "test_cycle" in df_tc.columns:
        unique_cycles = sorted(list(df_tc["test_cycle"].dropna().unique()))
        cycles.extend([c for c in unique_cycles if c != "Geral"])

    selected_cycle = st.selectbox("Selecione o Ciclo de Teste / Release para análise:", cycles, key="metrics_cycle_select")

    # Aplicação de filtros contextuais
    if selected_cycle != "Geral (Todas as Releases)":
        # Filtra Casos de Teste pelo ciclo selecionado
        df_tc_filtered = df_tc[df_tc["test_cycle"] == selected_cycle] if not df_tc.empty and "test_cycle" in df_tc.columns else df_tc.copy()
        
        # Se as tabelas de bugs também tiverem associação por ciclo, filtramos. Caso contrário, mantemos o escopo geral do projeto.
        df_bugs_filtered = df_bugs[df_bugs["test_cycle"] == selected_cycle] if not df_bugs.empty and "test_cycle" in df_bugs.columns else df_bugs.copy()
        
        scope_label = f"Release / Ciclo: {selected_cycle}"
    else:
        df_tc_filtered = df_tc.copy()
        df_bugs_filtered = df_bugs.copy()
        scope_label = "Visão Geral (Projeto Inteiro)"

    st.info(f"📌 Escopo ativo atual: **{scope_label}**")
    st.divider()

    # ------------------------------------------
    # 1. ANÁLISE DE SAÚDE E RISCOS DA RELEASE
    # ------------------------------------------
    st.subheader(f"🤖 Análise Inteligente de Qualidade ({scope_label})")
    
    if "ai_analysis_result" not in st.session_state:
        st.session_state["ai_analysis_result"] = None

    # Métricas agregadas baseadas no filtro ativo
    total_tc = len(df_tc_filtered)
    passed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Passou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    failed_tc = len(df_tc_filtered[df_tc_filtered["status"] == "Falhou"]) if not df_tc_filtered.empty and "status" in df_tc_filtered.columns else 0
    
    bugs_open = len(df_bugs_filtered[df_bugs_filtered["status"].isin(["Aberto", "Em correção"])]) if not df_bugs_filtered.empty and "status" in df_bugs_filtered.columns else len(df_bugs_filtered)
    high_risks = len(df_risks[df_risks["risk_score"] >= 15]) if not df_risks.empty and "risk_score" in df_risks.columns else 0

    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        if st.button("✨ Analisar Saúde com IA", type="primary", use_container_width=True):
            with st.spinner(f"IA consolidando dados para '{selected_cycle}'..."):
                prompt = f"""
                Atue como um QA Lead especialista sênior. Analise estes dados consolidados do projeto para o escopo '{selected_cycle}' e elabore um parecer executivo:

                - Escopo/Ciclo Analisado: {selected_cycle}
                - Casos de Teste: {total_tc} total (Passaram: {passed_tc}, Falharam: {failed_tc})
                - Bugs Abertos/Em Correção: {bugs_open}
                - Riscos Críticos na Matriz (Score >= 15): {high_risks}
                - Histórias de Usuário Mapeadas no Projeto: {len(df_stories)}

                Forneça de forma estruturada:
                1. Parecer Geral de Risco para Deploy (Baixo, Médio ou Alto) com justificativa técnica.
                2. Correlação entre os riscos identificados e a cobertura de testes atual deste escopo.
                3. Top 3 Recomendações Críticas para a equipe de QA/Dev antes do Go-Live.
                """
                try:
                    res = call_ai_service(prompt)
                    st.session_state["ai_analysis_result"] = res
                except Exception as e:
                    st.session_state["ai_analysis_result"] = None
                    st.warning(f"Servidor de IA indisponível. Exibindo estatísticas estruturadas locais. (Erro: {e})")

    # Exibe resultado da IA ou fallback estatístico inteligente
    if st.session_state["ai_analysis_result"]:
        st.info(st.session_state["ai_analysis_result"])
    else:
        st.markdown("### 📊 Relatório Estatístico Automatizado")
        risk_level = "🔴 ALTO" if high_risks > 2 or failed_tc > 0 else ("🟡 MÉDIO" if bugs_open > 0 else "🟢 BAIXO")
        st.write(f"**Nível Estimado de Risco:** {risk_level}")
        st.markdown(f"""
        - **Resumo de Cobertura ({selected_cycle}):** {passed_tc} de {total_tc} testes aprovados com sucesso.
        - **Atenção a Bugs:** Existem `{bugs_open}` bugs pendentes de resolução no escopo selecionado.
        - **Mitigação de Riscos:** Há `{high_risks}` riscos mapeados com alta pontuação na Matriz de Risco do projeto.
        """)

    st.divider()

    # ------------------------------------------
    # 2. KPIS E GRÁFICOS EXECUTIVOS
    # ------------------------------------------
    st.subheader(f"🚀 Indicadores Chave de Desempenho (KPIs) - {selected_cycle}")
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Casos de Teste (Escopo)", total_tc)
    
    rate = (passed_tc / total_tc * 100) if total_tc > 0 else 0.0
    c2.metric("Taxa de Sucesso", f"{rate:.1f}%")
    
    c3.metric("Bugs no Escopo", len(df_bugs_filtered))
    c4.metric("Riscos Globais", len(df_risks))

    st.markdown("---")
    
    # Gráficos Visuais Avançados (Plotly) com dados filtrados
    g1, g2 = st.columns(2)
    with g1:
        if not df_tc_filtered.empty and "status" in df_tc_filtered.columns:
            fig_tc = px.pie(df_tc_filtered, names="status", title=f"Distribuição de Status ({selected_cycle})", hole=0.4)
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("Sem dados de testes suficientes para o gráfico neste ciclo.")

    with g2:
        if not df_bugs_filtered.empty and "severity" in df_bugs_filtered.columns:
            fig_bugs = px.bar(df_bugs_filtered, x="severity", title=f"Bugs por Nível de Severidade ({selected_cycle})", color="severity")
            st.plotly_chart(fig_bugs, use_container_width=True)
        else:
            st.info("Sem dados de bugs suficientes para o gráfico neste ciclo.")

    # Terceira linha de gráficos: Matriz de Risco cruzada (Global do Projeto)
    if not df_risks.empty and "risk_score" in df_risks.columns:
        st.markdown("### ⚠️ Distribuição de Riscos do Projeto (Global)")
        fig_risks = px.scatter(
            df_risks, 
            x="probability", 
            y="impact", 
            size="risk_score", 
            color="risk_type",
            hover_name="risk_description",
            title="Matriz de Risco (Probabilidade vs Impacto)"
        )
        st.plotly_chart(fig_risks, use_container_width=True)

    st.divider()

    # ------------------------------------------
    # 3. EXPORTAÇÃO E DOWNLOADS
    # ------------------------------------------
    st.subheader("📥 Exportação de Relatórios Executivos")
    
    analysis_text = st.session_state['ai_analysis_result'] if st.session_state['ai_analysis_result'] else "Análise gerada estatisticamente pela plataforma sem IA."
    
    report_text = f"""# Relatório Executivo de QA & Qualidade
## Escopo / Ciclo Analisado: {selected_cycle}

## 📈 KPIs Gerais ({selected_cycle})
- **Casos de Teste no Escopo:** {total_tc}
- **Taxa de Sucesso:** {rate:.1f}%
- **Bugs Registrados:** {len(df_bugs_filtered)}
- **Riscos Mapeados (Global):** {len(df_risks)}
- **Histórias de Usuário:** {len(df_stories)}

## 🤖 Avaliação de Saúde da Release
{analysis_text}
"""

    st.download_button(
        label=f"📄 Baixar Relatório Executivo ({selected_cycle}) (Markdown)",
        data=report_text,
        file_name=f"relatorio_qa_{selected_cycle.lower().replace(' ', '_').replace('(', '').replace(')', '')}.md",
        mime="text/markdown",
        use_container_width=True
    )