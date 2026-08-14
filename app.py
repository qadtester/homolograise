import streamlit as st
from modules import auth, projects, requirements, testing, metrics, admin_panel
from config.database import supabase
from config.ai_config import render_ai_provider_selector, is_master_user

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="QA & Requisitos Hub",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. CONTROLE DE AUTENTICAÇÃO
# ==============================================================================
if not auth.is_authenticated():
    auth.render_auth_page()
    st.stop()

user_info = auth.get_logged_user()

# ==============================================================================
# 3. BUSCA DE EQUIPES VINCULADAS AO USUÁRIO (Relação N para N)
# ==============================================================================
user_teams_res = (
    supabase.table("team_members")
    .select("team_id, role, teams(id, name, invite_code)")
    .eq("user_id", user_info["id"])
    .execute()
)

user_teams = []
if user_teams_res.data:
    for item in user_teams_res.data:
        if item.get("teams"):
            team_info = item["teams"]
            team_info["user_role"] = item["role"]
            user_teams.append(team_info)

# Se o usuário não está vinculado a nenhuma equipe (exceto se for Master puro), exibe o onboarding
if not user_teams and not is_master_user():
    auth.render_team_onboarding()
    st.stop()

# Gerenciamento da Equipe Ativa na Sessão
if user_teams:
    if "current_team_id" not in st.session_state or not st.session_state["current_team_id"]:
        st.session_state["current_team_id"] = user_teams[0]["id"]

    valid_team_ids = [t["id"] for t in user_teams]
    if st.session_state["current_team_id"] not in valid_team_ids:
        st.session_state["current_team_id"] = user_teams[0]["id"]

    active_team = next((t for t in user_teams if t["id"] == st.session_state["current_team_id"]), user_teams[0])
    user_info["team_id"] = active_team["id"]
    user_info["role"] = active_team.get("user_role", "editor")
else:
    active_team = {"name": "Painel Master Global", "invite_code": "MASTER"}

# ==============================================================================
# 4. SIDEBAR (PERFIL, SELETOR DE EQUIPE, PROJETO E NAVEGAÇÃO)
# ==============================================================================
with st.sidebar:
    st.title("🎯 QA Hub")
    
    st.write(f"👤 **Usuário:** {user_info.get('name', 'Usuário')}")
    st.caption(f"📧 {user_info.get('email', '')}")
    
    if is_master_user():
        st.caption("👑 **Papel:** `MASTER`")
    else:
        st.caption(f"🛡️ **Papel:** `{user_info.get('role', 'editor')}`")
    
    st.divider()

    # --- SELETOR DE EQUIPE / ORGANIZAÇÃO ---
    if user_teams:
        st.subheader("🏢 Organização Ativa")
        team_options = {t["name"]: t["id"] for t in user_teams}
        
        active_team_id = active_team.get("id") if active_team else None
        if active_team_id in team_options.values():
            default_index = list(team_options.values()).index(active_team_id)
        else:
            default_index = 0

        selected_team_name = st.selectbox(
            "Alternar Equipe:", 
            options=list(team_options.keys()), 
            index=default_index
        )
        
        if team_options[selected_team_name] != st.session_state.get("current_team_id"):
            st.session_state["current_team_id"] = team_options[selected_team_name]
            st.rerun()

        st.info(f"🔑 **Código da Equipe:** `{active_team.get('invite_code', 'N/A')}`")

        with st.expander("➕ Entrar em Outra Equipe"):
            with st.form("sidebar_join_team"):
                new_code = st.text_input("Código de Convite", placeholder="Ex: A1B2C3")
                if st.form_submit_button("Vincular Equipe"):
                    if new_code.strip():
                        t_lookup = supabase.table("teams").select("id, name").eq("invite_code", new_code.strip().upper()).execute()
                        if t_lookup.data:
                            found_t = t_lookup.data[0]
                            supabase.table("team_members").upsert({
                                "team_id": found_t["id"],
                                "user_id": user_info["id"],
                                "role": "editor"
                            }, on_conflict="team_id,user_id").execute()
                            
                            st.session_state["current_team_id"] = found_t["id"]
                            st.success(f"Vinculado à equipe '{found_t['name']}' com sucesso!")
                            st.rerun()
                        else:
                            st.error("Código de convite inválido.")
                    else:
                        st.error("Digite o código.")

    if st.button("🚪 Sair / Logout", use_container_width=True):
        auth.logout()

    st.divider()

    # Seletor de Provedor de IA
    render_ai_provider_selector()
    st.divider()

    # Navegação entre Módulos
    st.subheader("🧭 Navegação")
    page_options = [
        "📁 Gestão de Projetos",
        "📝 Requisitos",
        "🧪 Módulo de Testes",
        "📊 Métricas & Exportação",
    ]
    
    # Adiciona aba de gestão de membros se for admin da equipe ativa
    if user_info.get("role") == "admin" and not is_master_user():
        page_options.append("👥 Gestão de Equipe")

    # Adiciona a opção exclusiva do Painel Administrativo Master se for o usuário Master
    if is_master_user():
        page_options.append("👑 Painel Admin Master")

    page = st.radio("Ir para:", page_options)

# ==============================================================================
# 5. CARREGAMENTO DO PROJETO ATIVO
# ==============================================================================
active_project = None
if page not in ["👥 Gestão de Equipe", "👑 Painel Admin Master"]:
    active_project = projects.render_project_selector()
    
    if not active_project and page in ["📝 Requisitos", "🧪 Módulo de Testes", "📊 Métricas & Exportação"]:
        st.warning("⚠️ **Nenhum projeto selecionado!**")
        st.info("Por favor, selecione ou crie um projeto no menu lateral (ou no módulo **Gestão de Projetos**) para prosseguir.")
        st.stop()

# ==============================================================================
# 6. EXECUÇÃO DO MÓDULO SELECIONADO
# ==============================================================================
if page == "📁 Gestão de Projetos":
    projects.render_projects_page()

elif page == "📝 Requisitos":
    requirements.render_requirements_module()

elif page == "🧪 Módulo de Testes":
    testing.render_testing_module(active_project["id"])

elif page == "📊 Métricas & Exportação":
    project_id = active_project["id"]
    try:
        test_cases = supabase.table("test_cases").select("*").eq("project_id", project_id).execute().data or []
        bug_reports = supabase.table("bug_reports").select("*").eq("project_id", project_id).execute().data or []
        risk_matrix = supabase.table("risk_matrix").select("*").eq("project_id", project_id).execute().data or []
        user_stories = supabase.table("user_stories").select("*").eq("project_id", project_id).execute().data or []
    except Exception as e:
        st.error(f"Erro ao carregar métricas do Supabase: {e}")
        test_cases, bug_reports, risk_matrix, user_stories = [], [], [], []

    metrics.render_metrics_dashboard(test_cases, bug_reports, risk_matrix, user_stories)

elif page == "👥 Gestão de Equipe":
    st.title("👥 Gestão de Membros da Organização")
    st.write(f"Gerencie os usuários e permissões da organização ativa **{active_team.get('name')}**.")
    
    members_res = (
        supabase.table("team_members")
        .select("role, users(id, name, email, created_at)")
        .eq("team_id", active_team["id"])
        .execute()
    )
    
    members = []
    if members_res.data:
        for m in members_res.data:
            if m.get("users"):
                u_data = m["users"]
                u_data["role"] = m["role"]
                members.append(u_data)
    
    for member in members:
        cols = st.columns([3, 2, 2, 2])
        with cols[0]:
            st.write(f"**{member['name']}**")
            st.caption(member['email'])
        with cols[1]:
            is_self = (member["id"] == user_info["id"])
            available_roles = ["editor", "admin"]
            current_role_index = available_roles.index(member["role"]) if member["role"] in available_roles else 0
            
            new_role = st.selectbox(
                "Papel", 
                options=available_roles, 
                index=current_role_index, 
                key=f"role_{member['id']}",
                label_visibility="collapsed"
            )
            
            if new_role != member["role"]:
                if is_self:
                    st.warning("Você não pode alterar seu próprio cargo.")
                else:
                    supabase.table("team_members").update({"role": new_role}).eq("team_id", active_team["id"]).eq("user_id", member["id"]).execute()
                    st.success(f"Cargo de {member['name']} alterado para {new_role}!")
                    st.rerun()
                    
        with cols[2]:
            st.write(f"Entrou em: {member['created_at'][:10] if member.get('created_at') else ''}")
        with cols[3]:
            if not is_self:
                if st.button("🗑️ Remover", key=f"rm_mem_{member['id']}"):
                    supabase.table("team_members").delete().eq("team_id", active_team["id"]).eq("user_id", member["id"]).execute()
                    st.success(f"Usuário {member['name']} removido da equipe.")
                    st.rerun()
            else:
                st.caption("Você (Ativo)")

elif page == "👑 Painel Admin Master":
    admin_panel.render_master_admin_panel()