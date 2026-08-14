import streamlit as st
from config.database import supabase
from config.ai_config import generate_istqb_content
from utils.export import export_to_csv, export_to_markdown

def render_requirements_module():
    st.header("📋 QA & Requisitos Hub - Gerenciamento de Requisitos e Riscos")

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
        st.info("💡 A IA utilizará o PDF e os documentos anexados a este projeto para gerar a especificação completa.")
        context_unificado = st.text_area("Instrução ou foco específico (Opcional):", height=120, placeholder="Ex: Focar no módulo de login e recuperação de senha...")

        if st.button("🚀 Gerar Especificação Completa com IA", type="primary"):
            with st.spinner("IA criando Persona e User Story no padrão ISTQB com base no projeto..."):
                query_ia = project_id
                if context_unificado.strip():
                    query_ia += f" | Foco adicional: {context_unificado}"

                data = generate_istqb_content("user_story", query_ia)
                
                if data and isinstance(data, dict):
                    p_data = data.get("persona", {})
                    supabase.table('personas').insert({
                        "project_id": project_id, 
                        "name": p_data.get("name", "Persona IA"), 
                        "role": p_data.get("role", "Usuário"),
                        "goals": p_data.get("goals", ""), 
                        "pain_points": p_data.get("pain_points", ""), 
                        "generated_by_ai": True
                    }).execute()

                    us_data = data.get("user_story", {})
                    
                    as_a = us_data.get("as_a", "").replace("Como um ", "").replace("Como uma ", "").strip()
                    i_want = us_data.get("i_want_to", "").replace("Eu quero ", "").replace("eu quero ", "").strip()
                    so_that = us_data.get("so_that", "").replace("Para que ", "").replace("para que ", "").strip()

                    supabase.table('user_stories').insert({
                        "project_id": project_id, 
                        "title": us_data.get("title", "História Gerada por IA"), 
                        "as_a": as_a,
                        "i_want_to": i_want, 
                        "so_that": so_that,
                        "acceptance_criteria": us_data.get("acceptance_criteria", ""), 
                        "generated_by_ai": True
                    }).execute()

                    st.success("Gerados e salvos no padrão ISTQB com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao gerar os requisitos. Verifique sua chave de API e tente novamente.")

    # ------------------------------------------
    # ABA 1: PERSONAS
    # ------------------------------------------
    with tab_personas:
        st.subheader("Personas do Projeto")
        with st.form("form_persona_manual", clear_on_submit=True):
            name = st.text_input("Nome:")
            role = st.text_input("Papel / Função:")
            goals = st.text_area("Objetivos:")
            pain_points = st.text_area("Dores:")
            if st.form_submit_button("Salvar Persona"):
                if name.strip():
                    supabase.table('personas').insert({
                        "project_id": project_id, "name": name, "role": role, "goals": goals, "pain_points": pain_points, "generated_by_ai": False
                    }).execute()
                    st.success("Persona salva com sucesso!")
                    st.rerun()
                else:
                    st.warning("O nome da persona é obrigatório.")

        st.divider()
        personas = supabase.table('personas').select('*').eq('project_id', project_id).execute().data or []
        for p in personas:
            badge = "🤖 IA" if p.get('generated_by_ai') else "✍️ Manual"
            with st.expander(f"👤 {p['name']} - {p['role']} [{badge}]"):
                st.markdown(f"**🎯 Objetivos:**\n{p.get('goals') or 'N/A'}")
                st.markdown(f"**⚡ Dores / Frustrações:**\n{p.get('pain_points') or 'N/A'}")
                
                c_edit, c_del = st.columns(2)
                with c_edit:
                    with st.popover("✏️ Editar Persona", key=f"pop_edit_p_{p['id']}"):
                        e_name = st.text_input("Nome", value=p['name'], key=f"e_p_name_{p['id']}")
                        e_role = st.text_input("Papel", value=p['role'], key=f"e_p_role_{p['id']}")
                        e_goals = st.text_area("Objetivos", value=p.get('goals', ''), key=f"e_p_goals_{p['id']}")
                        e_pain = st.text_area("Dores", value=p.get('pain_points', ''), key=f"e_p_pain_{p['id']}")
                        if st.button("Salvar Alterações", key=f"btn_p_edit_{p['id']}"):
                            supabase.table('personas').update({"name": e_name, "role": e_role, "goals": e_goals, "pain_points": e_pain}).eq('id', p['id']).execute()
                            st.rerun()
                with c_del:
                    if st.button("🗑️ Excluir Persona", key=f"btn_p_del_{p['id']}", type="primary"):
                        supabase.table('personas').delete().eq('id', p['id']).execute()
                        st.rerun()

    # ------------------------------------------
    # ABA 2: HISTÓRIAS DE USUÁRIO
    # ------------------------------------------
    with tab_stories:
        st.subheader("Histórias de Usuário")
        with st.form("form_us_manual", clear_on_submit=True):
            title = st.text_input("Título:")
            as_a = st.text_input("Como um(a)...")
            i_want_to = st.text_input("Eu quero...")
            so_that = st.text_input("Para que...")
            acceptance_criteria = st.text_area("Critérios de Aceite (Dado que... Quando... Então...):")
            if st.form_submit_button("Salvar User Story"):
                if title.strip():
                    supabase.table('user_stories').insert({
                        "project_id": project_id, "title": title, "as_a": as_a, "i_want_to": i_want_to, "so_that": so_that, "acceptance_criteria": acceptance_criteria, "generated_by_ai": False
                    }).execute()
                    st.success("User Story salva com sucesso!")
                    st.rerun()
                else:
                    st.warning("O título da história de usuário é obrigatório.")

        st.divider()
        stories = supabase.table('user_stories').select('*').eq('project_id', project_id).execute().data or []
        for us in stories:
            badge = "🤖 IA" if us.get('generated_by_ai') else "✍️ Manual"
            with st.expander(f"📌 {us.get('title')} [{badge}]"):
                st.markdown(f"**👤 Como um(a):** {us.get('as_a')}")
                st.markdown(f"**🎯 Eu quero:** {us.get('i_want_to')}")
                st.markdown(f"**💡 Para que:** {us.get('so_that')}")
                
                st.markdown("---")
                st.markdown("**✅ Critérios de Aceite (BDD):**")
                
                crit = us.get('acceptance_criteria', 'Sem critérios.')
                if isinstance(crit, str) and crit.strip():
                    formatted = crit
                    keywords = [
                        ("Dado que ", "\n\n**Dado que** "), ("dado que ", "\n\n**Dado que** "),
                        (" Quando ", "\n**Quando** "), (" quando ", "\n**Quando** "),
                        (" Então ", "\n**Então** "), (" então ", "\n**Então** "),
                        (" E ", "\n**E** "), (" e ", "\n**E** ")
                    ]
                    for old, new in keywords:
                        formatted = formatted.replace(old, new)
                    
                    if formatted.startswith("Dado que"):
                        formatted = formatted.replace("Dado que", "**Dado que**", 1)
                    elif formatted.startswith("Quando"):
                        formatted = formatted.replace("Quando", "**Quando**", 1)
                    elif formatted.startswith("Então"):
                        formatted = formatted.replace("Então", "**Então**", 1)

                    st.markdown(formatted.strip())
                else:
                    st.write(crit)

                c_edit, c_del = st.columns(2)
                with c_edit:
                    with st.popover("✏️ Editar User Story", key=f"pop_edit_us_{us['id']}"):
                        e_title = st.text_input("Título", value=us['title'], key=f"e_us_t_{us['id']}")
                        e_as_a = st.text_input("Como um", value=us.get('as_a', ''), key=f"e_us_a_{us['id']}")
                        e_want = st.text_input("Eu quero", value=us.get('i_want_to', ''), key=f"e_us_w_{us['id']}")
                        e_so = st.text_input("Para que", value=us.get('so_that', ''), key=f"e_us_s_{us['id']}")
                        e_crit = st.text_area("Critérios de Aceite", value=us.get('acceptance_criteria', ''), key=f"e_us_c_{us['id']}")
                        if st.button("Salvar Alterações", key=f"btn_us_edit_{us['id']}"):
                            supabase.table('user_stories').update({
                                "title": e_title, "as_a": e_as_a, "i_want_to": e_want, "so_that": e_so, "acceptance_criteria": e_crit
                            }).eq('id', us['id']).execute()
                            st.rerun()
                with c_del:
                    if st.button("🗑️ Excluir User Story", key=f"btn_us_del_{us['id']}", type="primary"):
                        supabase.table('user_stories').delete().eq('id', us['id']).execute()
                        st.rerun()

    # ------------------------------------------
    # ABA 3: MATRIZ DE RISCO
    # ------------------------------------------
    with tab_risks:
        st.subheader("⚠️ Matriz de Risco do Projeto")
        st.write("Gerencie os riscos de produto e projeto conforme o modelo padrão.")

        # BOTÃO DE GERAÇÃO DE RISCOS VIA IA
        with st.expander("✨ Gerar Matriz de Risco Automatizada via IA", expanded=False):
            st.info("💡 A IA fará a leitura de todos os documentos e descrições do projeto para mapear os riscos e estratégias de mitigação automaticamente.")
            if st.button("🚀 Gerar Riscos com IA", type="primary", key="btn_gen_risk_ai"):
                with st.spinner("Analisando o projeto e mapeando riscos potenciais..."):
                    data = generate_istqb_content("risk_matrix", project_id)
                    
                    if data and isinstance(data, list):
                        sucesso_riscos = 0
                        for item in data:
                            prob_str = item.get("probability", "Média")
                            imp_str = item.get("impact", "Médio")
                            
                            # Normaliza para o formato padrão esperado pelo formulário (ex: "2 - Médio")
                            prob_map = {"Baixa": "1 - Baixo", "Média": "2 - Médio", "Alta": "3 - Alto"}
                            imp_map = {"Baixo": "1 - Baixo", "Médio": "2 - Médio", "Alto": "3 - Alto"}
                            
                            prob_formatted = prob_map.get(prob_str, "2 - Médio")
                            imp_formatted = imp_map.get(imp_str, "2 - Médio")
                            
                            p_val = int(prob_formatted.split(" - ")[0])
                            i_val = int(imp_formatted.split(" - ")[0])
                            score = p_val * i_val

                            payload = {
                                "project_id": project_id,
                                "risk_description": item.get("risk_description", "Risco identificado por IA"),
                                "risk_type": "Produto",
                                "probability": prob_formatted,
                                "impact": imp_formatted,
                                "risk_score": score,
                                "strategy": "Mitigar",
                                "correction_plan": item.get("mitigation_strategy", "Monitorar plano de ação"),
                                "risk_owner": "QA / IA",
                                "periodicity": "Sprint",
                                "generated_by_ai": True
                            }
                            
                            try:
                                supabase.table('risk_matrix').insert(payload).execute()
                                sucesso_riscos += 1
                            except Exception:
                                pass
                        
                        if sucesso_riscos > 0:
                            st.success(f"{sucesso_riscos} riscos mapeados e salvos com sucesso na Matriz de Risco!")
                            st.rerun()
                        else:
                            st.error("Erro ao salvar os riscos gerados no banco de dados.")
                    else:
                        st.error("A IA não retornou um formato válido para a matriz de risco. Tente novamente.")

        with st.expander("➕ Cadastrar Novo Risco Manualmente", expanded=False):
            with st.form("form_risk_manual", clear_on_submit=True):
                risk_desc = st.text_area("Descrição do Risco:")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    risk_type = st.selectbox("Tipo", ["Produto", "Projeto"])
                    probability = st.selectbox("Probabilidade", ["1 - Baixo", "2 - Médio", "3 - Alto"])
                with col2:
                    impact = st.selectbox("Impacto", ["1 - Baixo", "2 - Médio", "3 - Alto"])
                    strategy = st.selectbox("Estratégia", ["Mitigar", "Transferir", "Evitar", "Aceitar"])
                with col3:
                    risk_owner = st.text_input("Dono do Risco", placeholder="Ex: QA Lead / PO")
                    periodicity = st.text_input("Periodicidade", placeholder="Ex: Semanal / Sprint")

                correction_plan = st.text_area("Como Corrigir / Plano de Mitigação:")

                if st.form_submit_button("Salvar Risco", type="primary"):
                    if not risk_desc.strip():
                        st.error("A descrição do risco é obrigatória.")
                    else:
                        prob_val = int(probability.split(" - ")[0])
                        imp_val = int(impact.split(" - ")[0])
                        score = prob_val * imp_val

                        supabase.table('risk_matrix').insert({
                            "project_id": project_id,
                            "risk_description": risk_desc,
                            "risk_type": risk_type,
                            "probability": probability,
                            "impact": impact,
                            "risk_score": score,
                            "strategy": strategy,
                            "correction_plan": correction_plan,
                            "risk_owner": risk_owner,
                            "periodicity": periodicity,
                            "generated_by_ai": False
                        }).execute()
                        st.success("Risco cadastrado com sucesso!")
                        st.rerun()

        st.divider()
        
        risks = supabase.table('risk_matrix').select('*').eq('project_id', project_id).execute().data or []
        if not risks:
            st.info("Nenhum risco cadastrado para este projeto.")
        else:
            with st.expander("📊 Visualizar Tabela Consolidada e Relatórios", expanded=False):
                table_data = []
                for r in risks:
                    table_data.append({
                        "ID": r['id'][:8],
                        "Risco": r.get('risk_description'),
                        "Tipo": r.get('risk_type'),
                        "Probabilidade": r.get('probability'),
                        "Impacto": r.get('impact'),
                        "Score (P x I)": r.get('risk_score'),
                        "Estratégia": r.get('strategy'),
                        "Como Corrigir": r.get('correction_plan'),
                        "Dono": r.get('risk_owner'),
                        "Periodicidade": r.get('periodicity')
                    })

                st.dataframe(table_data, use_container_width=True)

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    csv_data = export_to_csv(table_data)
                    st.download_button(
                        label="📥 Baixar Matriz de Risco (CSV)",
                        data=csv_data,
                        file_name="matriz_de_risco.csv",
                        mime="text/csv"
                    )
                with col_d2:
                    md_data = export_to_markdown(table_data, "Matriz de Risco do Projeto")
                    st.download_button(
                        label="📥 Baixar Relatório (Markdown)",
                        data=md_data,
                        file_name="matriz_de_risco.md",
                        mime="text/markdown"
                    )

            st.divider()
            st.subheader("✏️ Gerenciamento Individual (Editar / Excluir)")
            
            for r in risks:
                score = r.get('risk_score', 0)
                score_color = "🔴" if score >= 6 else ("🟡" if score >= 3 else "🟢")
                ai_badge = "🤖 IA" if r.get('generated_by_ai') else "✍️ Manual"
                
                with st.expander(f"{score_color} [{r.get('risk_type', 'Produto')}] Risco (Score: {score}) - {r.get('risk_description', '')[:50]}... [{ai_badge}]"):
                    
                    with st.form(key=f"form_edit_risk_{r['id']}"):
                        e_desc = st.text_area("Descrição do Risco", value=r.get('risk_description', ''))
                        
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            e_type = st.selectbox("Tipo", ["Produto", "Projeto"], index=0 if r.get('risk_type') == "Produto" else 1)
                            probs = ["1 - Baixo", "2 - Médio", "3 - Alto"]
                            p_idx = probs.index(r.get('probability')) if r.get('probability') in probs else 0
                            e_prob = st.selectbox("Probabilidade", probs, index=p_idx)
                        with ec2:
                            imps = ["1 - Baixo", "2 - Médio", "3 - Alto"]
                            i_idx = imps.index(r.get('impact')) if r.get('impact') in imps else 0
                            e_imp = st.selectbox("Impacto", imps, index=i_idx)
                            
                            strats = ["Mitigar", "Transferir", "Evitar", "Aceitar"]
                            s_idx = strats.index(r.get('strategy')) if r.get('strategy') in strats else 0
                            e_strat = st.selectbox("Estratégia", strats, index=s_idx)
                        with ec3:
                            e_owner = st.text_input("Dono do Risco", value=r.get('risk_owner', ''))
                            e_period = st.text_input("Periodicidade", value=r.get('periodicity', ''))

                        e_plan = st.text_area("Como Corrigir", value=r.get('correction_plan', ''))

                        col_save, _ = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                new_p_val = int(e_prob.split(" - ")[0])
                                new_i_val = int(e_imp.split(" - ")[0])
                                new_score = new_p_val * new_i_val

                                supabase.table('risk_matrix').update({
                                    "risk_description": e_desc,
                                    "risk_type": e_type,
                                    "probability": e_prob,
                                    "impact": e_imp,
                                    "risk_score": new_score,
                                    "strategy": e_strat,
                                    "correction_plan": e_plan,
                                    "risk_owner": e_owner,
                                    "periodicity": e_period
                                }).eq('id', r['id']).execute()
                                st.success("Risco atualizado com sucesso!")
                                st.rerun()
                    
                    if st.button("🗑️ Excluir Risco", key=f"btn_risk_del_{r['id']}", type="primary"):
                        supabase.table('risk_matrix').delete().eq('id', r['id']).execute()
                        st.rerun()