import streamlit as st
from config.database import supabase
from utils.permissions import can_edit

def notify_user(user_id: str, title: str, message: str):
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message
        }).execute()
    except Exception as e:
        st.error(f"Erro na notificação: {e}")

def render_kanban_board(project_id: str):
    st.title("📌 Quadro Kanban do Projeto")
    user_info = st.session_state.get("user", {})
    team_id = st.session_state.get("current_team_id")

    # 1. BUSCA MEMBROS DA EQUIPE
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
    member_options["Nenhum"] = None

    # 2. CARREGA E ORDENA AS COLUNAS
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

    # 3. CONTROLES DE COLUNA E NOVO CARD
    with st.expander("⚙️ Gerenciar Quadro (Colunas & Novas Tarefas)"):
        tab_new_task, tab_cols = st.tabs(["➕ Criar Nova Tarefa/Bug", "🛠️ Configurar Colunas"])
        
        with tab_new_task:
            with st.form("quick_add_card"):
                c_title = st.text_input("Título do Card / Tarefa")
                c_desc = st.text_area("Descrição / Detalhes")
                c_sev = st.selectbox("Severidade / Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
                c_col = st.selectbox("Coluna Inicial", [c["name"] for c in columns_data])
                
                if st.form_submit_button("Criar Card"):
                    if c_title.strip():
                        supabase.table("bug_reports").insert({
                            "project_id": project_id,
                            "title": c_title.strip(),
                            "description": c_desc.strip(),
                            "severity": c_sev,
                            "status": c_col
                        }).execute()
                        st.success("Card adicionado ao Quadro!")
                        st.rerun()

        with tab_cols:
            c1, c2 = st.columns(2)
            with c1:
                new_col_name = st.text_input("Nome da Nova Coluna:")
                if st.button("➕ Adicionar Coluna"):
                    if new_col_name.strip():
                        max_pos = max([c["position"] for c in columns_data], default=0)
                        supabase.table("kanban_columns").insert({
                            "project_id": project_id,
                            "name": new_col_name.strip(),
                            "position": max_pos + 1
                        }).execute()
                        st.rerun()

            with c2:
                col_to_del = st.selectbox("Remover Coluna:", [c["name"] for c in columns_data])
                if st.button("🗑️ Deletar Coluna", type="primary"):
                    target_col = next(c for c in columns_data if c["name"] == col_to_del)
                    supabase.table("kanban_columns").delete().eq("id", target_col["id"]).execute()
                    st.rerun()

            st.markdown("**Reordenar Colunas:**")
            for i, col_item in enumerate(columns_data):
                col_btn1, col_btn2, col_txt = st.columns([1, 1, 8])
                if i > 0 and col_btn1.button("⬅️", key=f"left_{col_item['id']}"):
                    # Troca posição com o anterior
                    prev_col = columns_data[i-1]
                    supabase.table("kanban_columns").update({"position": prev_col["position"]}).eq("id", col_item["id"]).execute()
                    supabase.table("kanban_columns").update({"position": col_item["position"]}).eq("id", prev_col["id"]).execute()
                    st.rerun()
                if i < len(columns_data) - 1 and col_btn2.button("➡️", key=f"right_{col_item['id']}"):
                    # Troca posição com o próximo
                    next_col = columns_data[i+1]
                    supabase.table("kanban_columns").update({"position": next_col["position"]}).eq("id", col_item["id"]).execute()
                    supabase.table("kanban_columns").update({"position": col_item["position"]}).eq("id", next_col["id"]).execute()
                    st.rerun()
                col_txt.write(f"**{i+1}. {col_item['name']}**")

    # 4. CARREGAMENTO DOS BUGS E RENDERIZAÇÃO
    bugs_res = (
        supabase.table("bug_reports")
        .select("*, users!bug_reports_assignee_id_fkey(name)")
        .eq("project_id", project_id)
        .execute()
    )
    bugs = bugs_res.data or []

    ui_cols = st.columns(len(columns_data))

    for idx, col_info in enumerate(columns_data):
        col_name = col_info["name"]
        col_bugs = [b for b in bugs if b.get("status") == col_name]

        with ui_cols[idx]:
            st.markdown(f"### **{col_name}** ({len(col_bugs)})")
            st.markdown("---")

            for bug in col_bugs:
                sev_color = "🔴" if bug.get("severity") in ["Alta", "Crítica"] else "🟡"
                assigned_name = bug.get("users", {}).get("name") if bug.get("users") else "Não atribuído"

                with st.expander(f"{sev_color} {bug['title']}"):
                    st.caption(f"**Severidade:** {bug.get('severity')} | **Atribuído:** {assigned_name}")
                    
                    # DETALHES COMPLETOS DO BUG
                    st.write(bug.get("description", "Sem descrição."))
                    
                    if bug.get("steps"):
                        st.markdown("**📋 Passos para Reproduzir:**")
                        st.code(bug.get("steps"), language="text")

                    if bug.get("expected_behavior"):
                        st.markdown(f"**🎯 Comportamento Esperado:**\n{bug.get('expected_behavior')}")

                    if bug.get("actual_behavior"):
                        st.markdown(f"**⚠️ Comportamento Observado:**\n{bug.get('actual_behavior')}")

                    st.divider()

                    # CONTROLES DE MOVIMENTAÇÃO E ASSIGNAÇÃO
                    if can_edit(user_info):
                        target_col = st.selectbox(
                            "Mover para:", 
                            [c["name"] for c in columns_data], 
                            index=[c["name"] for c in columns_data].index(col_name), 
                            key=f"mov_{bug['id']}"
                        )
                        if target_col != col_name:
                            supabase.table("bug_reports").update({"status": target_col}).eq("id", bug["id"]).execute()
                            st.rerun()

                        current_assignee = next((k for k, v in member_options.items() if v == bug.get("assignee_id")), "Nenhum")
                        selected_user = st.selectbox(
                            "Atribuir a:", 
                            list(member_options.keys()), 
                            index=list(member_options.keys()).index(current_assignee), 
                            key=f"assign_{bug['id']}"
                        )
                        
                        if member_options[selected_user] != bug.get("assignee_id"):
                            new_assignee_id = member_options[selected_user]
                            supabase.table("bug_reports").update({"assignee_id": new_assignee_id}).eq("id", bug["id"]).execute()
                            if new_assignee_id:
                                notify_user(new_assignee_id, "Novo Bug Atribuído 🐛", f"Você foi atribuído ao bug '{bug['title']}'.")
                            st.rerun()

                    # EVIDÊNCIAS E ANEXOS
                    st.markdown("**📎 Evidências:**")
                    attachments = bug.get("attachments") or []
                    for att in attachments:
                        if isinstance(att, dict) and att.get("url"):
                            st.markdown(f"📄 [{att.get('name')}]({att.get('url')})")

                    if can_edit(user_info):
                        uploaded_file = st.file_uploader("Anexar arquivo/evidência", key=f"att_{bug['id']}")
                        if uploaded_file and st.button("Enviar Anexo", key=f"btn_att_{bug['id']}"):
                            file_bytes = uploaded_file.read()
                            file_path = f"bug_evidences/{bug['id']}_{uploaded_file.name}"
                            
                            try:
                                supabase.storage.from_("evidences").upload(
                                    file_path, file_bytes, {"content-type": uploaded_file.type}
                                )
                                file_url = supabase.storage.from_("evidences").get_public_url(file_path)
                                
                                new_att = {"name": uploaded_file.name, "url": file_url}
                                updated_attachments = attachments + [new_att]
                                supabase.table("bug_reports").update({"attachments": updated_attachments}).eq("id", bug["id"]).execute()
                                st.success("Arquivo anexado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao subir arquivo: {e}")
