import streamlit as st
from config.database import supabase
from config.ai_config import is_master_user

def render_master_admin_panel():
    # Validação estrita do Usuário Master via MASTER_EMAIL
    if not is_master_user():
        st.error("⛔ Acesso negado. Esta área é restrita exclusivamente ao Usuário Master.")
        return

    st.title("👑 Painel Administrativo Master")
    st.markdown("Gerenciamento global de usuários e projetos da plataforma.")

    tab_users, tab_projects = st.tabs(["👥 Gerenciar Usuários", "📁 Gerenciar Projetos"])

    # -------------------------------------------------------------
    # ABA 1: GERENCIAMENTO DE USUÁRIOS & EXCLUSÃO EM CASCATA
    # -------------------------------------------------------------
    with tab_users:
        st.subheader("Lista de Usuários Cadastrados")
        
        users_res = supabase.table("users").select("*").execute()
        users = users_res.data or []

        if not users:
            st.info("Nenhum usuário cadastrado.")
        else:
            for u in users:
                with st.expander(f"👤 {u['name']} ({u['email']}) - Criado em: {u.get('created_at', '')[:10]}"):
                    st.write(f"**ID:** `{u['id']}`")
                    st.write(f"**Papel:** `{u.get('role', 'editor')}`")
                    
                    # Identifica equipes em que ele é owner
                    teams_owned = supabase.table("teams").select("id, name").eq("owner_id", u["id"]).execute().data or []
                    team_ids_owned = [t["id"] for t in teams_owned]
                    
                    exclusive_projects = []
                    if team_ids_owned:
                        proj_res = supabase.table("projects").select("id, name").in_("team_id", team_ids_owned).execute()
                        exclusive_projects = proj_res.data or []

                    st.markdown(f"**Projetos exclusivos da conta:** {len(exclusive_projects)}")
                    if exclusive_projects:
                        for ep in exclusive_projects:
                            st.caption(f"- 📁 {ep['name']} (`{ep['id']}`)")

                    st.divider()
                    
                    # Botão de exclusão com confirmação em cascata
                    del_key = f"del_user_{u['id']}"
                    if st.button(f"🗑️ Excluir Usuário e Dados Relacionados", key=del_key, type="primary"):
                        try:
                            # A. Apagar dependências dos projetos exclusivos (Personas, User Stories, Test Cases, Bugs, Riscos, Documentos)
                            for ep in exclusive_projects:
                                p_id = ep["id"]
                                supabase.table("personas").delete().eq("project_id", p_id).execute()
                                supabase.table("user_stories").delete().eq("project_id", p_id).execute()
                                supabase.table("test_cases").delete().eq("project_id", p_id).execute()
                                supabase.table("bug_reports").delete().eq("project_id", p_id).execute()
                                supabase.table("risk_matrix").delete().eq("project_id", p_id).execute()
                                supabase.table("project_documents").delete().eq("project_id", p_id).execute()
                            
                            # B. Apagar os projetos exclusivos vinculados às equipes do owner
                            if team_ids_owned:
                                supabase.table("projects").delete().in_("team_id", team_ids_owned).execute()

                            # C. Remover vínculos de team_members do usuário
                            supabase.table("team_members").delete().eq("user_id", u["id"]).execute()

                            # D. Apagar as equipes das quais ele era owner
                            if team_ids_owned:
                                supabase.table("teams").delete().in_("id", team_ids_owned).execute()

                            # E. Por fim, deletar o registro principal do usuário
                            supabase.table("users").delete().eq("id", u["id"]).execute()

                            st.success(f"Usuário {u['name']} e todos os dados relacionados foram excluídos com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao executar exclusão em cascata: {e}")

    # -------------------------------------------------------------
    # ABA 2: GERENCIAMENTO DE PROJETOS GLOBAIS
    # -------------------------------------------------------------
    with tab_projects:
        st.subheader("Todos os Projetos no Banco de Dados")
        projects_res = supabase.table("projects").select("*, teams(name)").execute()
        all_projects = projects_res.data or []

        if not all_projects:
            st.info("Nenhum projeto encontrado no sistema.")
        else:
            for proj in all_projects:
                team_name = proj.get("teams", {}).get("name", "Desconhecido") if proj.get("teams") else "Desconhecido"
                with st.expander(f"📁 {proj['name']} (Equipe: {team_name})"):
                    st.write(f"**Descrição:** {proj.get('description', 'Sem descrição')}")
                    st.write(f"**ID do Projeto:** `{proj['id']}`")
                    
                    if st.button(f"🗑️ Excluir Projeto Individualmente", key=f"del_proj_{proj['id']}"):
                        p_id = proj["id"]
                        supabase.table("personas").delete().eq("project_id", p_id).execute()
                        supabase.table("user_stories").delete().eq("project_id", p_id).execute()
                        supabase.table("test_cases").delete().eq("project_id", p_id).execute()
                        supabase.table("bug_reports").delete().eq("project_id", p_id).execute()
                        supabase.table("risk_matrix").delete().eq("project_id", p_id).execute()
                        supabase.table("project_documents").delete().eq("project_id", p_id).execute()
                        supabase.table("projects").delete().eq("id", p_id).execute()
                        st.success("Projeto e dados vinculados removidos com sucesso!")
                        st.rerun()