import streamlit as st
from config.database import supabase
from utils.permissions import can_edit, can_delete_items

def notify_user(user_id: str, title: str, message: str):
    """Envia notificação no banco de dados para o usuário."""
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message
        }).execute()
    except Exception as e:
        st.error(f"Erro ao notificar usuário: {e}")

def get_severity_badge(severity: str) -> str:
    """Mapeia a severidade para a cor/emoji correto."""
    mapping = {
        "Baixa": "🟢 Baixa",
        "Média": "🟡 Média",
        "Alta": "🟠 Alta",
        "Crítica": "🔴 Crítica"
    }
    return mapping.get(severity, "⚪ " + str(severity))

def render_kanban_board(project_id: str):
    st.title("📌 Quadro Kanban")
    
    user_info = st.session_state.get("user", {})
    team_id = st.session_state.get("current_team_id")

    # 1. BUSCA DE MEMBROS DA EQUIPE
    team_members = []
    if team_id:
        res = (
            supabase.table("team_members")
            .select("user_id, users!team_members_user_id_fkey(id, name, email)")
            .eq("team_id", team_id)
            .execute()
        )
        team_members = [row["users"] for row in (res.data or []) if row.get("users")]

    member_options = {m["name"]: m["id"] for m in team_members}
    member_options["Não atribuído"] = None

    # 2. CARREGA AS COLUNAS
    cols_res = (
        supabase.table("kanban_columns")
        .select("*")
        .eq("project_id", project_id)
        .order("position")
        .execute()
    )
    columns_data = cols_res.data or []

    if not columns_data:
        defaults = ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"]
        for idx, name in enumerate(defaults):
            supabase.table("kanban_columns").insert({
                "project_id": project_id, 
                "name": name, 
                "position": idx + 1
            }).execute()
        st.rerun()

    # 3. BARRA DE AÇÕES (ORGANIZAÇÃO DE TELAS E BOTÕES)
    c_act1, c_act2, _ = st.columns([2, 2, 6])
    
    with c_act1:
        if can_edit(user_info) and st.button("➕ Novo Card", use_container_width=True, type="primary"):
            st.session_state["open_new_card_modal"] = True

    with c_act2:
        if can_edit(user_info) and st.button("⚙️ Gerenciar Colunas", use_container_width=True):
            st.session_state["open_manage_cols_modal"] = True

    # --- MODAL: CRIAR CARD ---
    if st.session_state.get("open_new_card_modal", False):
        with st.expander("📝 Criar Novo Card / Bug", expanded=True):
            with st.form("form_create_kanban_card"):
                f_title = st.text_input("Título *")
                f_desc = st.text_area("Descrição")
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    f_sev = st.selectbox("Severidade", ["Baixa", "Média", "Alta", "Crítica"])
                with col_f2:
                    f_col = st.selectbox("Coluna Inicial", [c["name"] for c in columns_data])
                with col_f3:
                    f_assignee = st.selectbox("Atribuir a", list(member_options.keys()))

                f_steps = st.text_area("Passos para reproduzir (opcional)")
                f_expected = st.text_input("Comportamento Esperado (opcional)")
                f_actual = st.text_input("Comportamento Observado (opcional)")

                btn_sub, btn_close = st.columns([2, 2])
                submitted = btn_sub.form_submit_button("Salvar Card")
                
                if submitted:
                    if not f_title.strip():
                        st.error("O título é obrigatório.")
                    else:
                        payload = {
                            "project_id": project_id,
                            "title": f_title.strip(),
                            "description": f_desc.strip(),
                            "severity": f_sev,
                            "status": f_col,
                            "assignee_id": member_options[f_assignee],
                            "steps": f_steps,
                            "expected_behavior": f_expected,
                            "actual_behavior": f_actual
                        }
                        supabase.table("bug_reports").insert(payload).execute()
                        
                        if member_options[f_assignee]:
                            notify_user(member_options[f_assignee], "Novo Card Atribuído 🐛", f"Você foi atribuído ao card: '{f_title}'")

                        st.session_state["open_new_card_modal"] = False
                        st.success("Card criado com sucesso!")
                        st.rerun()

            if st.button("Cancelar", key="cancel_card_create"):
                st.session_state["open_new_card_modal"] = False
                st.rerun()

    # --- MODAL: GERENCIAR COLUNAS ---
    if st.session_state.get("open_manage_cols_modal", False):
        with st.expander("🛠️ Organizar Colunas", expanded=True):
            t_add, t_ord, t_del = st.tabs(["Adicionar Coluna", "Reordenar Colunas", "Excluir Coluna"])
            
            with t_add:
                col_name_input = st.text_input("Nome da nova coluna:")
                if st.button("Salvar Nova Coluna"):
                    if col_name_input.strip():
                        max_p = max([c["position"] for c in columns_data], default=0)
                        supabase.table("kanban_columns").insert({
                            "project_id": project_id,
                            "name": col_name_input.strip(),
                            "position": max_p + 1
                        }).execute()
                        st.rerun()

            with t_ord:
                st.write("Ajuste a ordem das colunas no quadro:")
                for i, col_item in enumerate(columns_data):
                    ca, cb, cc = st.columns([1, 1, 6])
                    if i > 0 and ca.button("⬆️", key=f"up_{col_item['id']}"):
                        prev = columns_data[i-1]
                        supabase.table("kanban_columns").update({"position": prev["position"]}).eq("id", col_item["id"]).execute()
                        supabase.table("kanban_columns").update({"position": col_item["position"]}).eq("id", prev["id"]).execute()
                        st.rerun()
                    if i < len(columns_data) - 1 and cb.button("⬇️", key=f"down_{col_item['id']}"):
                        nxt = columns_data[i+1]
                        supabase.table("kanban_columns").update({"position": nxt["position"]}).eq("id", col_item["id"]).execute()
                        supabase.table("kanban_columns").update({"position": col_item["position"]}).eq("id", nxt["id"]).execute()
                        st.rerun()
                    cc.write(f"**{i+1}. {col_item['name']}**")

            with t_del:
                del_target = st.selectbox("Escolha a coluna para remover:", [c["name"] for c in columns_data])
                if st.button("Remover Coluna", type="primary"):
                    target_obj = next(c for c in columns_data if c["name"] == del_target)
                    supabase.table("kanban_columns").delete().eq("id", target_obj["id"]).execute()
                    st.rerun()

            if st.button("Fechar Gerenciador de Colunas"):
                st.session_state["open_manage_cols_modal"] = False
                st.rerun()

    st.divider()

    # 4. BARRA DE FILTROS APLICAÇÃO
    with st.expander("🔍 Filtros Avançados", expanded=False):
        fl1, fl2, fl3 = st.columns(3)
        with fl1:
            filter_sev = st.multiselect("Filtrar por Severidade", ["Baixa", "Média", "Alta", "Crítica"])
        with fl2:
            filter_assignee = st.multiselect("Filtrar por Atribuído", list(member_options.keys()))
        with fl3:
            filter_search = st.text_input("Buscar por Título / Palavra-chave")

    # 5. CARREGA BUGS/CARDS
    bugs_res = (
        supabase.table("bug_reports")
        .select("*, users!bug_reports_assignee_id_fkey(name)")
        .eq("project_id", project_id)
        .execute()
    )
    bugs = bugs_res.data or []

    # Aplica os filtros
    filtered_bugs = []
    for b in bugs:
        # Filtro Severidade
        if filter_sev and b.get("severity") not in filter_sev:
            continue
        # Filtro Responsável
        b_assignee_name = b.get("users", {}).get("name") if b.get("users") else "Não atribuído"
        if filter_assignee and b_assignee_name not in filter_assignee:
            continue
        # Filtro Texto
        if filter_search and filter_search.lower() not in b.get("title", "").lower():
            continue
        filtered_bugs.append(b)

    # 6. EXIBIÇÃO DAS COLUNAS E CARDS
    ui_cols = st.columns(len(columns_data))

    for idx, col_info in enumerate(columns_data):
        col_name = col_info["name"]
        col_bugs = [b for b in filtered_bugs if b.get("status") == col_name]

        with ui_cols[idx]:
            st.markdown(f"#### **{col_name}** `({len(col_bugs)})`")
            st.markdown("---")

            for bug in col_bugs:
                badge = get_severity_badge(bug.get("severity", "Baixa"))
                assigned_name = bug.get("users", {}).get("name") if bug.get("users") else "Não atribuído"

                with st.expander(f"{badge} {bug['title']}"):
                    st.caption(f"**Atribuído:** {assigned_name}")
                    st.write(bug.get("description") or "*Sem descrição*")

                    if bug.get("steps"):
                        st.markdown("**📋 Passos:**")
                        st.code(bug.get("steps"), language="text")

                    if bug.get("expected_behavior"):
                        st.markdown(f"**🎯 Esperado:** {bug.get('expected_behavior')}")
                    if bug.get("actual_behavior"):
                        st.markdown(f"**⚠️ Observado:** {bug.get('actual_behavior')}")

                    st.divider()

                    # EDIÇÃO RÁPIDA E TROCA DE STATUS
                    if can_edit(user_info):
                        # Mover coluna
                        new_col = st.selectbox(
                            "Mover para:", 
                            [c["name"] for c in columns_data], 
                            index=[c["name"] for c in columns_data].index(col_name), 
                            key=f"mov_{bug['id']}"
                        )
                        if new_col != col_name:
                            supabase.table("bug_reports").update({"status": new_col}).eq("id", bug["id"]).execute()
                            st.rerun()

                        # Reatribuir
                        cur_assignee_key = next((k for k, v in member_options.items() if v == bug.get("assignee_id")), "Não atribuído")
                        new_assignee_key = st.selectbox(
                            "Reatribuir a:", 
                            list(member_options.keys()), 
                            index=list(member_options.keys()).index(cur_assignee_key), 
                            key=f"assign_{bug['id']}"
                        )
                        if member_options[new_assignee_key] != bug.get("assignee_id"):
                            new_uid = member_options[new_assignee_key]
                            supabase.table("bug_reports").update({"assignee_id": new_uid}).eq("id", bug["id"]).execute()
                            if new_uid:
                                notify_user(new_uid, "Reatribuição de Card 🐛", f"O card '{bug['title']}' foi reatribuído a você.")
                            st.rerun()

                    # SEÇÃO DE EVIDÊNCIAS
                    st.markdown("**📎 Anexos:**")
                    attachments = bug.get("attachments") or []
                    for att in attachments:
                        if isinstance(att, dict) and att.get("url"):
                            st.markdown(f"📄 [{att.get('name')}]({att.get('url')})")

                    if can_edit(user_info):
                        up_file = st.file_uploader("Anexar Evidência", key=f"file_{bug['id']}")
                        if up_file and st.button("Salvar Anexo", key=f"btn_file_{bug['id']}"):
                            file_bytes = up_file.read()
                            file_path = f"bug_evidences/{bug['id']}_{up_file.name}"
                            try:
                                supabase.storage.from_("evidences").upload(file_path, file_bytes, {"content-type": up_file.type})
                                file_url = supabase.storage.from_("evidences").get_public_url(file_path)
                                
                                updated_att = attachments + [{"name": up_file.name, "url": file_url}]
                                supabase.table("bug_reports").update({"attachments": updated_att}).eq("id", bug["id"]).execute()
                                st.success("Anexo enviado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro no envio: {e}")

                    st.divider()

                    # EXCLUSÃO RESTRITA (APENAS DONO OU GESTOR)
                    if can_delete_items(user_info):
                        if st.button("🗑️ Excluir Card", key=f"del_card_{bug['id']}", type="secondary"):
                            supabase.table("bug_reports").delete().eq("id", bug["id"]).execute()
                            st.success("Card excluído!")
                            st.rerun()
