import streamlit as st
from modules.test_cases import render_test_cases_tab
from modules.bug_reports import render_bug_reports_tab

def render_testing_module(project_id: str):
    if not project_id:
        st.warning("Selecione um projeto para acessar o Módulo de Testes.")
        return

    st.title("🧪 Módulo de Testes & Qualidade")
    tab1, tab2 = st.tabs(["Casos de Teste & Execução", "Bug Reports"])
    
    with tab1:
        render_test_cases_tab(project_id)
    with tab2:
        render_bug_reports_tab(project_id)
