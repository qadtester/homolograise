import re
import streamlit as st
import datetime
from config.database import supabase
from config.ai_config import generate_istqb_content
from utils.export import export_to_csv, export_to_markdown, export_to_html
from utils.permissions import can_create, can_edit, can_delete_items

TEST_TYPES = ["Funcional", "Regressão", "Smoke", "Não-Funcional"]

def format_regression_title(original_title: str) -> str:
    """Garante que o prefixo [Regressão] apareça apenas uma vez, limpando acumulados."""
    clean_title = re.sub(r'(\s*\[Regressão\]\s*)+', ' ', original_title, flags=re.IGNORECASE).strip()
    return f"[Regressão] {clean_title}"


# ==========================================
# ABA 1: CASOS DE TESTE (ISTQB)
# ==========================================

def render_test_cases_tab(project_id: str):
    st.subheader("📋 Gestão e Execução de Casos de Teste")
    
    user_info = st.session_state.get("user", {})
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        current_cycle = st.text_input(
            "🏷️ Ciclo de Teste / Release (para novas criações)", 
            value="", 
            placeholder="Ex: Release 1.0, Sprint 12, Pós-Deploy v1.1",
            help="Preencha este campo caso vá criar ou gerar novos casos de teste."
        )
    
    active_cycle = current_cycle.strip()

    with col_c2:
        try:
            existing_cycles_res = supabase.table("test_cases").select("test_cycle").eq("project_id", project_id).execute()
            cycles_list = sorted(list(set([row.get("test_cycle") for row in (existing_cycles_res.data or []) if row.get("test_cycle") and row.get("test_cycle").strip()])))
        except Exception as e:
            cycles_list = []
            st.error(f"Erro ao carregar ciclos de teste: {e}")

    # Geração IA e Criação apenas para quem possui permissão de criação
    if can_create(user_info):
        with st.expander("🚀 Geração Inteligente de Suíte Completa via IA (Múltiplos Testes)", expanded=False):
            if not active_cycle:
                st.warning("⚠️ Preencha o **Ciclo de Teste / Release** acima para usar a geração por IA.")
            else:
                st.info(f"💡 A IA fará a leitura completa do documento do projeto e gerará a suíte atribuindo ao ciclo: **{active_cycle}**")
                foco_lote = st.text_input("Foco opcional para a suíte (ex: Priorizar testes de segurança e login):", key="batch_ai_foco")
                
                if st.button("✨ Gerar Suíte Completa de Testes com IA", type="primary", key="btn_gen_batch_tc"):
                    with st.spinner("A IA está analisando o documento do projeto e estruturando os casos de teste..."):
                        query_lote = project_id
                        if foco_lote.strip():
                            query_lote += f" | Foco da suíte: {foco_lote}"
                        
                        data = generate_istqb_content("test_cases_batch", query_lote)
                        
                        if data and isinstance(data, list):
                            sucesso_count = 0
                            erros_count = 0
                            for item in data:
                                payload = {
                                    "project_id": project_id,
                                    "test_type": item.get("test_type", "Funcional"),
                                    "title": item.get("title", "Caso de Teste Gerado por IA"),
                                    "preconditions": item.get("preconditions", ""),
                                    "steps": item.get("steps", ""),
                                    "expected_result": item.get("expected_result", ""),
                                    "status": "Não Executado",
                                    "test_cycle": active_cycle
                                }
                                try:
                                    supabase.table("test_cases").insert(payload).execute()
                                    sucesso_count += 1
                                except Exception as db_err:
                                    erros_count += 1
                                    st.warning(f"Falha ao salvar o caso '{item.get('title')}': {db_err}")
                            
                            if sucesso_count > 0:
                                st.success(f"Suíte gerada com sucesso! {sucesso_count} casos de teste adicionados ao ciclo `{active_cycle}`.")
                                if erros_count > 0:
                                    st.warning(f"{erros_count} itens falharam ao ser salvos.")
                                st.rerun()
                            else:
                                st.error("Houve um erro ao salvar os casos de teste gerados no Supabase.")
                        else:
                            st.error("A IA não retornou uma lista válida. Verifique a configuração da IA.")

        with st.expander("➕ Criar Caso de Teste Individual (Manual ou Unitário com IA)", expanded=False):
            mode = st.radio("Modo de Criação", ["Sem IA (Manual)", "Com IA (Unitário)"], horizontal=True, key="tc_mode_radio")
            test_type = st.selectbox("Tipo de Teste", TEST_TYPES, key="tc_type_select")
            
            if mode == "Com IA (Unitário)":
                if not active_cycle:
                    st.warning("⚠️ Preencha o **Ciclo de Teste / Release** acima para criar o teste.")
                else:
                    st.info(f"💡 A IA lerá o documento e salvará no ciclo: **{active_cycle}**")
                    user_story = st.text_area("O que deseja testar? (ex: tela de login, fluxo de carrinho...):", placeholder="Ex: Validar se o usuário consegue logar com credenciais inválidas...", key="tc_ai_prompt")
                    
                    if st.button("✨ Gerar e Salvar Caso de Teste via IA", type="primary", key="btn_gen_tc_ai"):
                        with st.spinner("IA lendo o documento e gerando o caso de teste..."):
                            query_ia = project_id
                            if user_story.strip():
                                query_ia += f" | Contexto/Foco: {user_story}"

                            data = generate_istqb_content("test_case", query_ia)
                            
                            if data and isinstance(data, dict):
                                payload = {
                                    "project_id": project_id, 
                                    "test_type": test_type,
                                    "title": data.get("title", "Caso de Teste Gerado por IA"), 
                                    "preconditions": data.get("preconditions", ""),
                                    "steps": data.get("steps", ""),
                                    "expected_result": data.get("expected_result", ""),
                                    "status": "Não Executado",
                                    "test_cycle": active_cycle
                                }
                                
                                try:
                                    supabase.table("test_cases").insert(payload).execute()
                                    st.success("Caso de teste salvo com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar no Supabase: {e}")
                            else:
                                st.error("Falha ao gerar o caso de teste pela IA.")
            else:
                with st.form("manual_tc_form", clear_on_submit=True):
                    st.markdown("📝 **Preencha os campos abaixo seguindo as boas práticas ISTQB:**")
                    title = st.text_input("Título do Caso de Teste *", placeholder="Ex: CT01 - Validação de login com senha inválida")
                    preconditions = st.text_area("Pré-condições", placeholder="Ex: O usuário deve estar cadastrado na base e na tela de login.")
                    steps = st.text_area("Passos para Execução *", placeholder="1. Inserir email válido.\n2. Inserir senha incorreta.\n3. Clicar em Entrar.")
                    expected_result = st.text_area("Resultado Esperado *", placeholder="Ex: O sistema deve exibir mensagem de erro 'Credenciais inválidas' e impedir o acesso.")
                    
                    if st.form_submit_button("💾 Salvar Caso de Teste"):
                        if not active_cycle:
                            st.error("O campo **Ciclo de Teste / Release** no topo da página deve ser preenchido para salvar um novo teste.")
                        elif title.strip() and steps.strip() and expected_result.strip():
                            payload = {
                                "project_id": project_id, 
                                "test_type": test_type, 
                                "title": title, 
                                "preconditions": preconditions, 
                                "steps": steps,
                                "expected_result": expected_result, 
                                "status": "Não Executado",
                                "test_cycle": active_cycle
                            }
                            try:
                                supabase.table("test_cases").insert(payload).execute()
                                st.success("Salvo com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar no Supabase: {e}")
                        else:
                            st.error("Os campos Título, Passos e Resultado Esperado são obrigatórios.")
    else:
        st.info("🔒 Seu perfil possui permissão apenas de leitura. A criação e geração de testes estão desabilitadas.")

    st.divider()
    
    st.markdown("### Suíte de Testes")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_cycle = st.selectbox("Filtrar por Ciclo:", ["Todos"] + cycles_list, key="tc_filter_cycle")
    with col_f2:
        filter_type = st.selectbox("Filtrar por Tipo:", ["Todos"] + TEST_TYPES, key="tc_filter_select")
    with col_f3:
        filter_status = st.selectbox(
            "Filtrar por Status:", 
            ["Todos", "Não Executado", "Passou", "Falhou", "Bloqueado"], 
            key="tc_filter_status"
        )
    
    try:
        query = supabase.table("test_cases").select("*").eq("project_id", project_id)
        if filter_cycle != "Todos":
            query = query.eq("test_cycle", filter_cycle)
        if filter_type != "Todos":
            query = query.eq("test_type", filter_type)
        if filter_status != "Todos":
            query = query.eq("status", filter_status)
        
        test_cases = query.execute().data or []
    except Exception as e:
        test_cases = []
        st.error(f"Erro ao buscar casos de teste: {e}")
        
    if not test_cases:
        st.info("Nenhum caso de teste encontrado com os filtros selecionados.")
    else:
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            csv_data = export_to_csv(test_cases)
            st.download_button(
                label="📥 Baixar (CSV)",
                data=csv_data.encode("utf-8-sig"),
                file_name=f"casos_de_teste_{project_id[:8]}.csv",
                mime="text/csv; charset=utf-8-sig",
                key="btn_dl_tc_csv"
            )
        with col_dl2:
            md_data = export_to_markdown(test_cases, title=f"Casos de Teste - Ciclo: {filter_cycle}")
            st.download_button(
                label="📥 Baixar (Markdown)",
                data=md_data,
                file_name=f"casos_de_teste_{project_id[:8]}.md",
                mime="text/markdown",
                key="btn_dl_tc_md"
            )
        with col_dl3:
            html_data = export_to_html(test_cases, title=f"Casos de Teste - Ciclo: {filter_cycle}")
            st.download_button(
                label="🌐 Baixar (Visual do App)",
                data=html_data.encode("utf-8"),
                file_name=f"casos_de_teste_{project_id[:8]}.html",
                mime="text/html",
                key="btn_dl_tc_html"
            )
            
        st.markdown("---")

        grouped_tc = {}
        for tc in test_cases:
            c_name = tc.get("test_cycle") or "Sem Ciclo"
            grouped_tc.setdefault(c_name, []).append(tc)

        for cycle_name, tc_list in grouped_tc.items():
            with st.expander(f"📦 **Ciclo / Release: {cycle_name}** ({len(tc_list)} testes)", expanded=True):
                for tc in tc_list:
                    status = tc.get("status", "Não Executado")
                    cycle_tag = tc.get("test_cycle", "Sem Ciclo")
                    status_icon = "🟢" if status == "Passou" else ("🔴" if status == "Falhou" else ("🟡" if status == "Bloqueado" else "⚪"))

                    with st.expander(f"{status_icon} [{tc.get('test_type', 'Teste')}] - {tc.get('title')}"):
                        col_det, col_act = st.columns([3, 1])
                        
                        with col_det:
                            st.markdown(f"**Tipo:** `{tc.get('test_type', 'N/A')}`")
                            st.markdown(f"**Ciclo:** `{cycle_tag}`")
                            st.markdown(f"**Pré-condições:** {tc.get('preconditions') or 'N/A'}")
                            st.markdown(f"**Passos:**\n\n{tc.get('steps') or 'N/A'}")
                            st.markdown(f"**Resultado Esperado:**\n\n{tc.get('expected_result') or 'N/A'}")
                            
                            st.divider()
                            c_edit, c_clone, c_del = st.columns(3)
                            
                            with c_edit:
                                if can_edit(user_info):
                                    with st.popover("✏️ Editar", key=f"pop_edit_tc_{tc['id']}"):
                                        e_title = st.text_input("Título", value=tc['title'], key=f"e_tc_t_{tc['id']}")
                                        current_type = tc.get('test_type', 'Funcional')
                                        type_idx = TEST_TYPES.index(current_type) if current_type in TEST_TYPES else 0
                                        e_type = st.selectbox("Tipo de Teste *", TEST_TYPES, index=type_idx, key=f"e_tc_tp_{tc['id']}")
                                        e_cycle = st.text_input("Ciclo *", value=cycle_tag, key=f"e_tc_c_{tc['id']}")
                                        e_pre = st.text_area("Pré-condições", value=tc.get('preconditions', ''), key=f"e_tc_p_{tc['id']}")
                                        e_steps = st.text_area("Passos", value=tc.get('steps', ''), key=f"e_tc_s_{tc['id']}")
                                        e_exp = st.text_area("Esperado", value=tc.get('expected_result', ''), key=f"e_tc_e_{tc['id']}")
                                        
                                        if st.button("Salvar Alterações", key=f"btn_tc_edit_{tc['id']}"):
                                            if e_cycle.strip():
                                                try:
                                                    supabase.table("test_cases").update({
                                                        "title": e_title,
                                                        "test_type": e_type,
                                                        "test_cycle": e_cycle.strip(),
                                                        "preconditions": e_pre,
                                                        "steps": e_steps,
                                                        "expected_result": e_exp
                                                    }).eq('id', tc['id']).execute()
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Erro ao atualizar: {e}")
                                            else:
                                                st.error("O campo Ciclo é obrigatório.")

                            with c_clone:
                                if can_edit(user_info):
                                    if st.button("📋 Duplicar Teste", key=f"btn_tc_clone_{tc['id']}", help="Duplica este caso de teste"):
                                        new_title = format_regression_title(tc['title']) if tc.get('test_type') == "Regressão" else f"{tc['title']} (Cópia)"
                                        clone_payload = {
                                            "project_id": project_id,
                                            "test_type": tc.get('test_type', 'Funcional'),
                                            "title": new_title,
                                            "preconditions": tc.get('preconditions', ''),
                                            "steps": tc.get('steps', ''),
                                            "expected_result": tc.get('expected_result', ''),
                                            "status": "Não Executado",
                                            "test_cycle": tc.get('test_cycle', active_cycle)
                                        }
                                        try:
                                            supabase.table("test_cases").insert(clone_payload).execute()
                                            st.success("Caso de teste duplicado!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao duplicar: {e}")
                            
                            with c_del:
                                if can_delete_items(user_info):
                                    if st.button("🗑️ Excluir", key=f"btn_tc_del_{tc['id']}", type="primary"):
                                        try:
                                            supabase.table("test_cases").delete().eq('id', tc['id']).execute()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao excluir: {e}")
                                else:
                                    st.caption("🔒 Exclusão restrita")

                        with col_act:
                            st.write(f"**Status:** {status}")
                            st.write("**Executar Ciclo:**")
                            if can_edit(user_info):
                                if st.button("🟢 Passou", key=f"p_{tc['id']}", use_container_width=True):
                                    try:
                                        supabase.table("test_cases").update({"status": "Passou"}).eq("id", tc['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                                if st.button("🔴 Falhou", key=f"f_{tc['id']}", use_container_width=True):
                                    try:
                                        supabase.table("test_cases").update({"status": "Falhou"}).eq("id", tc['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                                if st.button("🟡 Bloqueado", key=f"b_{tc['id']}", use_container_width=True):
                                    try:
                                        supabase.table("test_cases").update({"status": "Bloqueado"}).eq("id", tc['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                                        
                                if status != "Não Executado":
                                    if st.button("⚪ Resetar (Não Executado)", key=f"r_{tc['id']}", use_container_width=True):
                                        try:
                                            supabase.table("test_cases").update({"status": "Não Executado"}).eq("id", tc['id']).execute()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao resetar status: {e}")

# ==========================================
# ABA 2: BUG REPORTS (ISTQB / IEEE 829)
# ==========================================

def render_bug_reports_tab(project_id: str):
    st.subheader("🐛 Registro e Gestão de Bugs")
    
    user_info = st.session_state.get("user", {})
    
    bug_cycle_input = st.text_input(
        "🏷️ Ciclo de Teste do Bug / Release (para novos registros)", 
        value="", 
        placeholder="Ex: Release 1.0, Sprint 12...",
        key="bug_active_cycle_input",
        help="Informe a release ou ciclo onde o novo bug foi encontrado."
    )
    
    active_bug_cycle = bug_cycle_input.strip()

    # --- REGISTRO DE BUG ---
    if can_create(user_info):
        with st.expander("🚨 Registrar Novo Bug", expanded=False):
            bug_mode = st.radio("Modo de Registro:", ["Sem IA (Manual)", "Com IA (Automático)"], horizontal=True, key="bug_mode_radio")
            
            if bug_mode == "Com IA (Automático)":
                if not active_bug_cycle:
                    st.warning("⚠️ Preencha o **Ciclo de Teste do Bug / Release** acima para registrar.")
                else:
                    st.info(f"💡 A IA analisará os documentos do projeto para montar o Bug Report atribuído ao ciclo: **{active_bug_cycle}**")
                    raw_bug = st.text_area("Descreva o problema encontrado:", key="bug_ai_prompt")
                    
                    if st.button("✨ Gerar e Salvar Bug Report via IA", type="primary", key="btn_gen_bug_ai"):
                        if raw_bug.strip():
                            with st.spinner("IA criando o Bug Report no padrão ISTQB..."):
                                query_bug_ia = f"{project_id} | Falha relatada: {raw_bug}"
                                data = generate_istqb_content("bug_report", query_bug_ia)
                                
                                if data and isinstance(data, dict):
                                    steps_content = data.get("steps_to_reproduce") or ""
                                    payload = {
                                        "project_id": project_id, 
                                        "title": data.get("title", "Bug Relatado por IA"), 
                                        "description": data.get("description", raw_bug),
                                        "severity": data.get("severity", "Média"),
                                        "steps": steps_content, 
                                        "expected_behavior": data.get("expected_behavior", ""), 
                                        "actual_behavior": data.get("actual_behavior", ""),
                                        "status": "Aberto",
                                        "test_cycle": active_bug_cycle
                                    }
                                    try:
                                        supabase.table("bug_reports").insert(payload).execute()
                                        st.success("Bug ISTQB registrado com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar no Supabase: {e}")
                                else:
                                    st.error("Falha ao gerar o bug report pela IA. Tente novamente.")
                        else:
                            st.warning("Escreva a descrição do problema encontrado.")
            else:
                with st.form("bug_report_form", clear_on_submit=True):
                    st.markdown("📝 **Preencha os dados do defeito conforme as diretrizes ISTQB/IEEE 829:**")
                    title = st.text_input("Título do Bug *", placeholder="Ex: Erro 500 ao submeter o formulário de cadastro")
                    severity = st.selectbox("Severidade *", ["Baixa", "Média", "Alta", "Crítica"])
                    description = st.text_area("Descrição do Problema", placeholder="Resumo e contexto geral do bug...")
                    steps = st.text_area("Passos para Reproduzir *", placeholder="1. Acessar a página...\n2. Preencher...\n3. Clicar em...")
                    expected_behavior = st.text_area("Comportamento Esperado *", placeholder="O cadastro deve ser efetuado com sucesso...")
                    actual_behavior = st.text_area("Comportamento Atual *", placeholder="A tela trava e exibe erro 500...")
                    
                    if st.form_submit_button("🚨 Registrar Bug"):
                        if not active_bug_cycle:
                            st.error("O campo **Ciclo de Teste do Bug / Release** no topo da aba deve ser preenchido.")
                        elif title.strip() and steps.strip() and expected_behavior.strip() and actual_behavior.strip():
                            payload = {
                                "project_id": project_id, 
                                "title": title, 
                                "description": description.strip(),
                                "severity": severity,
                                "steps": steps, 
                                "expected_behavior": expected_behavior, 
                                "actual_behavior": actual_behavior,
                                "status": "Aberto",
                                "test_cycle": active_bug_cycle
                            }
                            try:
                                supabase.table("bug_reports").insert(payload).execute()
                                st.success("Bug registrado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar no Supabase: {e}")
                        else:
                            st.error("Os campos Título, Passos, Comportamento Esperado e Atual são obrigatórios.")
    else:
        st.info("🔒 Seu perfil possui permissão apenas de leitura. O registro de novos bugs está desabilitado.")

    st.divider()
    
    # --- FILTROS DE BUGS ---
    col_bf1, col_bf2, col_bf3 = st.columns(3)
    with col_bf1:
        try:
            existing_bug_cycles_res = supabase.table("bug_reports").select("test_cycle").eq("project_id", project_id).execute()
            bug_cycles_list = sorted(list(set([row.get("test_cycle") for row in (existing_bug_cycles_res.data or []) if row.get("test_cycle") and row.get("test_cycle").strip()])))
        except Exception as e:
            bug_cycles_list = []
            st.error(f"Erro ao carregar ciclos de bugs: {e}")
            
        bug_cycle_filter = st.selectbox("Filtrar por Ciclo do Bug:", ["Todos"] + bug_cycles_list, key="bug_cycle_filter_select")
    
    with col_bf2:
        bug_status_filter = st.selectbox("Filtrar por Status do Bug:", ["Todos", "Aberto", "Em correção", "Pronto para Teste", "Passou", "Fechado"], key="bug_status_filter_select")

    with col_bf3:
        bug_severity_filter = st.selectbox("Filtrar por Severidade:", ["Todos", "Baixa", "Média", "Alta", "Crítica"], key="bug_severity_filter_select")
    
    try:
        b_query = supabase.table("bug_reports").select("*").eq("project_id", project_id)
        if bug_cycle_filter != "Todos":
            b_query = b_query.eq("test_cycle", bug_cycle_filter)
        if bug_status_filter != "Todos":
            b_query = b_query.eq("status", bug_status_filter)
        if bug_severity_filter != "Todos":
            b_query = b_query.eq("severity", bug_severity_filter)
            
        bugs = b_query.execute().data or []
    except Exception as e:
        bugs = []
        st.error(f"Erro ao buscar relatórios de bug: {e}")
    
    if not bugs:
        st.info("Nenhum bug registrado com estes filtros.")
    else:
        # --- EXPORTAÇÃO ---
        col_bdl1, col_bdl2, col_bdl3 = st.columns(3)
        with col_bdl1:
            csv_bugs = export_to_csv(bugs)
            st.download_button(
                label="📥 Baixar Bugs (CSV)",
                data=csv_bugs.encode("utf-8-sig"),
                file_name=f"bug_reports_{project_id[:8]}.csv",
                mime="text/csv; charset=utf-8-sig",
                key="btn_dl_bug_csv"
            )
        with col_bdl2:
            md_bugs = export_to_markdown(bugs, title=f"Relatório de Bugs - Ciclo: {bug_cycle_filter}", is_bug_report=True)
            st.download_button(
                label="📥 Baixar Bugs (Markdown)",
                data=md_bugs,
                file_name=f"bug_reports_{project_id[:8]}.md",
                mime="text/markdown",
                key="btn_dl_bug_md"
            )
        with col_bdl3:
            html_bugs = export_to_html(bugs, title=f"Relatório de Bugs - Ciclo: {bug_cycle_filter}", is_bug_report=True)
            st.download_button(
                label="🌐 Baixar Bugs (Visual do App)",
                data=html_bugs.encode("utf-8"),
                file_name=f"bug_reports_{project_id[:8]}.html",
                mime="text/html",
                key="btn_dl_bug_html"
            )
            
        st.markdown("---")

        # --- LISTAGEM E AGRUPAMENTO ---
        grouped_bugs = {}
        for bug in bugs:
            bc_name = bug.get("test_cycle") or "Sem Ciclo"
            grouped_bugs.setdefault(bc_name, []).append(bug)

        for b_cycle_name, b_list in grouped_bugs.items():
            with st.expander(f"📦 **Ciclo / Release: {b_cycle_name}** ({len(b_list)} bugs)", expanded=True):
                for bug in b_list:
                    sev = bug.get("severity", "Média")
                    bug_status = bug.get('status', 'Aberto')
                    bug_cycle_tag = bug.get('test_cycle', 'Sem Ciclo')
                    sev_color = "🔴" if sev in ["Alta", "Crítica"] else ("🟡" if sev == "Média" else "🟢")
                    
                    with st.expander(f"{sev_color} [{sev}] {bug.get('title')} - Status: `{bug_status}`"):
                        st.markdown(f"**Ciclo / Release:** `{bug_cycle_tag}`")
                        if bug.get("description"):
                            st.markdown(f"**Descrição:**\n\n{bug.get('description')}")
                        st.markdown(f"**Passos para Reproduzir:**\n\n{bug.get('steps') or 'N/A'}")
                        st.markdown(f"**Comportamento Esperado:** {bug.get('expected_behavior') or 'N/A'}")
                        st.markdown(f"**Comportamento Atual:** {bug.get('actual_behavior') or 'N/A'}")
                        
                        st.divider()
                        c_status, c_edit, c_clone, c_del = st.columns([2, 1, 1, 1])
                        
                        # --- MODIFICAR STATUS ---
                        with c_status:
                            if can_edit(user_info):
                                status_options = ["Aberto", "Em correção", "Pronto para Teste", "Passou", "Fechado"]
                                current_idx = status_options.index(bug_status) if bug_status in status_options else 0
                                
                                new_b_status = st.selectbox(
                                    "Atualizar Status:", 
                                    status_options,
                                    index=current_idx,
                                    key=f"st_bug_{bug['id']}"
                                )
                                if new_b_status != bug_status:
                                    if st.button("💾 Salvar Status", key=f"btn_save_st_{bug['id']}"):
                                        try:
                                            supabase.table("bug_reports").update({"status": new_b_status}).eq("id", bug['id']).execute()
                                            st.success("Status atualizado!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar status: {e}")

                        # --- EDITAR BUG ---
                        with c_edit:
                            if can_edit(user_info):
                                with st.popover("✏️ Editar", key=f"pop_edit_bug_{bug['id']}"):
                                    e_title = st.text_input("Título", value=bug['title'], key=f"e_b_t_{bug['id']}")
                                    e_cycle = st.text_input("Ciclo / Release *", value=bug_cycle_tag, key=f"e_b_c_{bug['id']}")
                                    e_sev = st.selectbox(
                                        "Severidade", 
                                        ["Baixa", "Média", "Alta", "Crítica"], 
                                        index=["Baixa", "Média", "Alta", "Crítica"].index(sev) if sev in ["Baixa", "Média", "Alta", "Crítica"] else 1, 
                                        key=f"e_b_s_{bug['id']}"
                                    )
                                    e_desc = st.text_area("Descrição do Problema", value=bug.get('description', ''), key=f"e_b_d_{bug['id']}")
                                    e_steps = st.text_area("Passos", value=bug.get('steps', ''), key=f"e_b_st_{bug['id']}")
                                    e_exp = st.text_area("Esperado", value=bug.get('expected_behavior', ''), key=f"e_b_ex_{bug['id']}")
                                    e_act = st.text_area("Atual", value=bug.get('actual_behavior', ''), key=f"e_b_ac_{bug['id']}")
                                    
                                    if st.button("Salvar Alterações", key=f"btn_bug_edit_{bug['id']}"):
                                        if e_cycle.strip():
                                            try:
                                                supabase.table("bug_reports").update({
                                                    "title": e_title, 
                                                    "test_cycle": e_cycle.strip(), 
                                                    "severity": e_sev, 
                                                    "description": e_desc,
                                                    "steps": e_steps,
                                                    "expected_behavior": e_exp, 
                                                    "actual_behavior": e_act
                                                }).eq('id', bug['id']).execute()
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro ao salvar edições: {e}")
                                        else:
                                            st.error("O campo Ciclo é obrigatório.")

                        # --- DUPLICAR / CLONAR BUG ---
                        with c_clone:
                            if can_edit(user_info):
                                if st.button("📋 Duplicar Bug", key=f"btn_bug_clone_{bug['id']}", help="Duplica este bug para reutilização em outro ciclo ou reabertura em novo módulo"):
                                    bug_clone_payload = {
                                        "project_id": project_id,
                                        "title": f"{bug['title']} (Cópia)",
                                        "description": bug.get("description", ""),
                                        "severity": bug.get("severity", "Média"),
                                        "steps": bug.get("steps", ""),
                                        "expected_behavior": bug.get("expected_behavior", ""),
                                        "actual_behavior": bug.get("actual_behavior", ""),
                                        "status": "Aberto",
                                        "test_cycle": active_bug_cycle if active_bug_cycle else bug_cycle_tag
                                    }
                                    try:
                                        supabase.table("bug_reports").insert(bug_clone_payload).execute()
                                        st.success("Bug duplicado com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao duplicar bug: {e}")

                        # --- EXCLUIR BUG ---
                        with c_del:
                            if can_delete_items(user_info):
                                if st.button("🗑️ Excluir", key=f"btn_bug_del_{bug['id']}", type="primary"):
                                    try:
                                        supabase.table("bug_reports").delete().eq('id', bug['id']).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao excluir bug: {e}")
                            else:
                                st.caption("🔒 Restrito")

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
