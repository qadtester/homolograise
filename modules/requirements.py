import streamlit as st
from config.database import supabase
from config.ai_config import generate_istqb_content
from utils.export import export_to_csv, export_to_markdown
from utils.permissions import can_create, can_edit, can_delete_items

def render_requirements_module():
    st.header("📋 QA & Requisitos Hub - Gerenciamento de Requisitos e Riscos")

    user_info = st.session_state.get("user")
    project_id = st.session_state.get('current_project_id')
    if not project_id:
        st.warning("Nenhum projeto ativo selecionado.")
        return

    tab_unified, tab_personas, tab_stories, tab_risks = st.tabs([
        "✨ Especificação Completa (IA)", 
        "👤 Personas", 
        "📖 Histórias de Usuário",
        "⚠️ Matriz de Risco"
    ])

    # ------------------------------------------
    # ABA 0: IA UNIFICADA (PADRÃO ISTQB)
    # ------------------------------------------
    with tab_unified:
        st.subheader("Gerar Persona e User Story Integradas (Padrão ISTQB)")
        
        if not can_create(user_info):
            st.info("🔒 Seu perfil possui permissão apenas de leitura. A geração via IA está desabilitada.")
        else:
            st.info("💡 A IA utilizará o PDF e os documentos anexados a este projeto para gerar a especificação completa.")
            context_unificado = st.text_area("Instrução ou foco específico (Opcional):", height=120, placeholder="Ex: Focar no módulo de login e recuperação de senha...")

            if st.button("🚀 Gerar Especificação Completa com IA", type="primary"):
                with st.spinner("IA criando Persona e User Story no padrão ISTQB com base no projeto..."):
                    query_ia = project_id
                    if context_unificado.strip():
                        query_ia += f" | Foco adicional: {context_unificado}"

                    data = generate_istqb_content("user_story", query_ia)
                    
                    if data and isinstance(data, dict):
                        erros = []
                        
                        # 1. Inserção de Persona
                        p_data = data.get("persona", {})
                        if p_data:
                            try:
                                supabase.table('personas').insert({
                                    "project_id": project_id, 
                                    "name": p_data.get("name", "Persona IA"), 
                                    "role": p_data.get("role", "Usuário"),
                                    "goals": p_data.get("goals", ""), 
                                    "pain_points": p_data.get("pain_points", ""), 
                                    "generated_by_ai": True
                                }).execute()
                            except Exception as e:
                                erros.append(f"Erro ao salvar Persona: {e}")

                        # 2. Inserção de User Story
                        us_data = data.get("user_story", {})
                        if us_data:
                            as_a = (us_data.get("as_a") or "").replace("Como um ", "").replace("Como uma ", "").strip()
                            i_want = (us_data.get("i_want_to") or "").replace("Eu quero ", "").replace("eu quero ", "").strip()
                            so_that = (us_data.get("so_that") or "").replace("Para que ", "").replace("para que ", "").strip()

                            try:
                                supabase.table('user_stories').insert({
                                    "project_id": project_id, 
                                    "title": us_data.get("title", "História Gerada por IA"), 
                                    "as_a": as_a,
                                    "i_want_to": i_want, 
                                    "so_that": so_that,
                                    "acceptance_criteria": us_data.get("acceptance_criteria", ""), 
                                    "generated_by_ai": True
                                }).execute()
                            except Exception as e:
                                erros.append(f"Erro ao salvar User Story: {e}")

                        if not erros:
                            st.success("Persona e User Story geradas e salvas com sucesso!")
                            st.rerun()
                        else:
                            for err in erros:
                                st.error(err)
                    else:
                        st.error("Falha ao gerar os requisitos. Verifique sua chave de API e tente novamente.")

# ==========================================
# ABA 1: PERSONAS
# ==========================================
with tab_personas:
    st.header("Personas do Projeto")
    
    # Formulário de Criação (Requer can_create)
    if can_create(user_info):
        with st.expander("➕ Adicionar Nova Persona"):
            with st.form("form_add_persona", clear_on_submit=True):
                p_name = st.text_input("Nome da Persona")
                p_role = st.text_input("Papel / Cargo")
                p_goals = st.text_area("Objetivos")
                p_pain = st.text_area("Dores / Necessidades")
                
                if st.form_submit_button("Salvar Persona"):
                    if p_name.strip():
                        try:
                            supabase.table('personas').insert({
                                "name": p_name,
                                "role": p_role,
                                "goals": p_goals,
                                "pain_points": p_pain
                            }).execute()
                            st.success("Persona criada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar persona: {e}")
                    else:
                        st.warning("O campo Nome é obrigatório.")

    # Listagem de Personas
    try:
        res_personas = supabase.table('personas').select('*').execute()
        personas = res_personas.data if res_personas.data else []
        
        for p in personas:
            with st.container():
                st.subheader(f"👤 {p.get('name', 'Sem Nome')}")
                st.write(f"**Papel:** {p.get('role', 'N/A')}")
                st.write(f"**Objetivos:** {p.get('goals', 'N/A')}")
                st.write(f"**Dores:** {p.get('pain_points', 'N/A')}")
                
                # Ações de Edição e Exclusão separadas por permissão
                c_edit, c_del = st.columns(2)
                
                with c_edit:
                    if can_edit(user_info):
                        with st.popover("✏️ Editar Persona", key=f"pop_edit_p_{p['id']}"):
                            e_name = st.text_input("Nome", value=p.get('name', ''), key=f"e_p_name_{p['id']}")
                            e_role = st.text_input("Papel", value=p.get('role', ''), key=f"e_p_role_{p['id']}")
                            e_goals = st.text_area("Objetivos", value=p.get('goals', ''), key=f"e_p_goals_{p['id']}")
                            e_pain = st.text_area("Dores", value=p.get('pain_points', ''), key=f"e_p_pain_{p['id']}")
                            
                            if st.button("Salvar Alterações", key=f"btn_p_edit_{p['id']}"):
                                if e_name.strip():
                                    try:
                                        supabase.table('personas').update({
                                            "name": e_name, 
                                            "role": e_role, 
                                            "goals": e_goals, 
                                            "pain_points": e_pain
                                        }).eq('id', p['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar: {e}")
                                else:
                                    st.error("O nome é obrigatório.")

                with c_del:
                    if can_delete_items(user_info):
                        if st.button("🗑️ Excluir Persona", key=f"btn_p_del_{p['id']}", type="primary"):
                            try:
                                supabase.table('personas').delete().eq('id', p['id']).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
                
                st.divider()
    except Exception as e:
        st.error(f"Erro ao carregar personas: {e}")

# ==========================================
# ABA 2: USER STORIES
# ==========================================
with tab_stories:
    st.header("User Stories")
    
    # Formulário de Criação (Requer can_create)
    if can_create(user_info):
        with st.expander("➕ Adicionar Nova User Story"):
            with st.form("form_add_us", clear_on_submit=True):
                us_title = st.text_input("Título da História")
                us_as_a = st.text_input("Como um (Perfil)")
                us_want = st.text_input("Eu quero (Ação)")
                us_so = st.text_input("Para que (Benefício)")
                us_crit = st.text_area("Critérios de Aceite")
                
                if st.form_submit_button("Salvar User Story"):
                    if us_title.strip():
                        try:
                            supabase.table('user_stories').insert({
                                "title": us_title,
                                "as_a": us_as_a,
                                "i_want_to": us_want,
                                "so_that": us_so,
                                "acceptance_criteria": us_crit
                            }).execute()
                            st.success("User Story salva com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.warning("O título é obrigatório.")

    # Listagem de User Stories
    try:
        res_us = supabase.table('user_stories').select('*').execute()
        stories = res_us.data if res_us.data else []
        
        for us in stories:
            with st.container():
                st.subheader(f"📖 {us.get('title', 'Sem Título')}")
                st.markdown(f"**Como** {us.get('as_a', '...')} **eu quero** {us.get('i_want_to', '...')} **para que** {us.get('so_that', '...')}.")
                st.caption(f"**Critérios de Aceite:** {us.get('acceptance_criteria', 'N/A')}")
                
                # Ações de Edição e Exclusão separadas por permissão
                c_edit, c_del = st.columns(2)
                
                with c_edit:
                    if can_edit(user_info):
                        with st.popover("✏️ Editar User Story", key=f"pop_edit_us_{us['id']}"):
                            e_title = st.text_input("Título", value=us.get('title', ''), key=f"e_us_t_{us['id']}")
                            e_as_a = st.text_input("Como um", value=us.get('as_a', ''), key=f"e_us_a_{us['id']}")
                            e_want = st.text_input("Eu quero", value=us.get('i_want_to', ''), key=f"e_us_w_{us['id']}")
                            e_so = st.text_input("Para que", value=us.get('so_that', ''), key=f"e_us_s_{us['id']}")
                            e_crit = st.text_area("Critérios de Aceite", value=us.get('acceptance_criteria', ''), key=f"e_us_c_{us['id']}")
                            
                            if st.button("Salvar Alterações", key=f"btn_us_edit_{us['id']}"):
                                if e_title.strip():
                                    try:
                                        supabase.table('user_stories').update({
                                            "title": e_title, 
                                            "as_a": e_as_a, 
                                            "i_want_to": e_want, 
                                            "so_that": e_so, 
                                            "acceptance_criteria": e_crit
                                        }).eq('id', us['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar edições: {e}")
                                else:
                                    st.error("O título é obrigatório.")

                with c_del:
                    if can_delete_items(user_info):
                        if st.button("🗑️ Excluir User Story", key=f"btn_us_del_{us['id']}", type="primary"):
                            try:
                                supabase.table('user_stories').delete().eq('id', us['id']).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
                
                st.divider()
    except Exception as e:
        st.error(f"Erro ao carregar User Stories: {e}")

# ==========================================
# ABA 3: MATRIZ DE RISCO
# ==========================================
with tab_risks:
    st.header("Matriz de Riscos")
    
    # Formulário de Criação (Requer can_create)
    if can_create(user_info):
        with st.expander("➕ Adicionar Novo Risco"):
            with st.form("form_add_risk", clear_on_submit=True):
                r_desc = st.text_input("Descrição do Risco")
                r_prob = st.selectbox("Probabilidade", ["Baixa", "Média", "Alta"])
                r_impact = st.selectbox("Impacto", ["Baixo", "Médio", "Alto"])
                r_mitig = st.text_area("Plano de Mitigação")
                
                if st.form_submit_button("Salvar Risco"):
                    if r_desc.strip():
                        try:
                            supabase.table('risk_matrix').insert({
                                "description": r_desc,
                                "probability": r_prob,
                                "impact": r_impact,
                                "mitigation": r_mitig
                            }).execute()
                            st.success("Risco registrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar risco: {e}")
                    else:
                        st.warning("A descrição é obrigatória.")

    # Listagem e Gestão de Riscos
    try:
        res_risks = supabase.table('risk_matrix').select('*').execute()
        risks = res_risks.data if res_risks.data else []
        
        for r in risks:
            with st.container():
                st.subheader(f"⚠️ {r.get('description', 'Sem descrição')}")
                col_info1, col_info2 = st.columns(2)
                col_info1.write(f"**Probabilidade:** {r.get('probability', 'N/A')}")
                col_info2.write(f"**Impacto:** {r.get('impact', 'N/A')}")
                st.write(f"**Mitigação:** {r.get('mitigation', 'N/A')}")
                
                c_edit, c_del = st.columns(2)
                
                with c_edit:
                    if can_edit(user_info):
                        with st.popover("✏️ Editar Risco", key=f"pop_edit_risk_{r['id']}"):
                            e_desc = st.text_input("Descrição", value=r.get('description', ''), key=f"e_r_desc_{r['id']}")
                            
                            prob_options = ["Baixa", "Média", "Alta"]
                            curr_prob_idx = prob_options.index(r.get('probability', 'Média')) if r.get('probability') in prob_options else 1
                            e_prob = st.selectbox("Probabilidade", prob_options, index=curr_prob_idx, key=f"e_r_prob_{r['id']}")
                            
                            imp_options = ["Baixo", "Médio", "Alto"]
                            curr_imp_idx = imp_options.index(r.get('impact', 'Médio')) if r.get('impact') in imp_options else 1
                            e_imp = st.selectbox("Impacto", imp_options, index=curr_imp_idx, key=f"e_r_imp_{r['id']}")
                            
                            e_mitig = st.text_area("Plano de Mitigação", value=r.get('mitigation', ''), key=f"e_r_mitig_{r['id']}")
                            
                            if st.button("Salvar Alterações", key=f"btn_risk_edit_{r['id']}"):
                                if e_desc.strip():
                                    try:
                                        supabase.table('risk_matrix').update({
                                            "description": e_desc,
                                            "probability": e_prob,
                                            "impact": e_imp,
                                            "mitigation": e_mitig
                                        }).eq('id', r['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar alterações: {e}")
                                else:
                                    st.error("A descrição é obrigatória.")

                with c_del:
                    if can_delete_items(user_info):
                        if st.button("🗑️ Excluir Risco", key=f"btn_risk_del_{r['id']}", type="primary"):
                            try:
                                supabase.table('risk_matrix').delete().eq('id', r['id']).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
                
                st.divider()
    except Exception as e:
        st.error(f"Erro ao carregar Matriz de Risco: {e}")
