import streamlit as st
from config.database import supabase
from utils.permissions import can_edit, can_create, can_delete_items

def notify_user(user_id: str, title: str, message: str):
    """Envia notificação no banco de dados para o usuário atribuído."""
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message
        }).execute()
    except Exception as e:
        st.error(f"Erro ao disparar notificação: {e}")

def render_kanban_board(project_id: str):
    st.subheader("📋 Quadro Kanban de Defeitos & Bugs")
    user_info = st.session_state.get("user", {})
    team_id = st.session_state.get("current_team_id")

    # CORREÇÃO 1: Consulta ajustada para o relacionamento exato de team_members -> users
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

    # 1. GERENCIAMENTO DINÂMICO DE COLUNAS
    cols_res = (
        supabase.table("kanban_columns")
        .select("*")
        .eq("project_id", project_id)
        .order("position")
        .execute()
    )
    columns_data = cols_res.data or []

    if not columns_data:
        st.warning("Nenhuma coluna encontrada para o Kanban. Inicializando colunas padrão...")
        defaults = ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"]
        for idx, name in enumerate(defaults):
            supabase.table("kanban_columns").insert({
                "project_id": project_id, 
                "name": name, 
                "position": idx + 1
            }).execute()
        st.rerun()

    # Gerenciador de Estrutura de Colunas (Criar/Deletar)
    if can_edit(user_info):
        with st.expander("⚙️ Configurar Colunas do Quadro"):
            c_add, c_del = st.columns(2)
            with c_add:
                new_col_name = st.text_input("Nova Coluna:")
                if st.button("➕ Adicionar Coluna"):
                    if new_col_name.strip():
                        max_pos = max([c["position"] for c in columns_data], default=0)
                        supabase.table("kanban_columns").insert({
                            "project_id": project_id,
                            "name": new_col_name.strip(),
                            "position": max_pos + 1
                        }).execute()
                        st.success("Coluna criada!")
                        st.rerun()

            with c_del:
                col_to_del = st.selectbox("Remover Coluna:", [c["name"] for c in columns_data])
                if st.button("🗑️ Deletar Coluna", type="primary"):
                    target_col = next(c for c in columns_data if c["name"] == col_to_del)
                    supabase.table("kanban_columns").delete().eq("id", target_col["id"]).execute()
                    st.success("Coluna removida!")
                    st.rerun()

    # 2. CARREGAMENTO DOS BUGS
    bugs_res = (
        supabase.table("bug_reports")
        .select("*, users!bug_reports_assignee_id_fkey(name)")
        .eq("project_id", project_id)
        .execute()
    )
    bugs = bugs_res.data or []

    # 3. RENDERIZAÇÃO DAS COLUNAS KANBAN
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
                    st.write(bug.get("description", "Sem descrição."))

                    # Mover Card para Outra Coluna
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

                        # Atribuir Membro + Notificação
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
                                notify_user(
                                    user_id=new_assignee_id,
                                    title="Novo Bug Atribuído 🐛",
                                    message=f"Você foi atribuído ao bug '{bug['title']}' no quadro Kanban."
                                )
                            st.rerun()

                    # CORREÇÃO 2: Exibição e Upload Efetivo de Evidências via Supabase Storage
                    st.markdown("**📎 Evidências:**")
                    attachments = bug.get("attachments") or []
                    for att in attachments:
                        if att.get("url"):
                            st.markdown(f"📄 [{att.get('name')}]({att.get('url')})")
                        else:
                            st.caption(f"📄 {att.get('name')}")

                    if can_edit(user_info):
                        uploaded_file = st.file_uploader("Anexar arquivo/evidência", key=f"att_{bug['id']}")
                        if uploaded_file:
                            file_bytes = uploaded_file.read()
                            file_path = f"bug_evidences/{bug['id']}_{uploaded_file.name}"
                            
                            try:
                                # Envia o arquivo para o Storage no bucket "evidences"
                                supabase.storage.from_("evidences").upload(
                                    file_path, 
                                    file_bytes, 
                                    {"content-type": uploaded_file.type}
                                )
                                file_url = supabase.storage.from_("evidences").get_public_url(file_path)
                            except Exception:
                                file_url = None

                            new_att = {
                                "name": uploaded_file.name, 
                                "type": uploaded_file.type,
                                "url": file_url
                            }
                            updated_attachments = attachments + [new_att]
                            supabase.table("bug_reports").update({"attachments": updated_attachments}).eq("id", bug["id"]).execute()
                            st.success("Evidência anexada com sucesso!")
                            st.rerun()
