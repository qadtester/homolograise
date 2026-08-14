import streamlit as st
from config.ai_config import is_master_user, render_ai_provider_selector
from config.database import supabase
from modules import admin_panel, auth, metrics, projects, requirements, testing

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
    if (
        "current_team_id" not in st.session_state
        or not st.session_state["current_team_id"]
    ):
        st.session_state["current_team_id"] = user_teams[0]["id"]

    valid_team_ids = [t["id"] for t in user_teams]
    if st.session_state["current_team_id"] not in valid_team_ids:
        st.session_state["current_team_id"] = user_teams[0]["id"]

    active_team = next(
        (
            t
            for t in user_teams
            if t["id"] == st.session_state["current_team_id"]
        ),
        user_teams[0],
    )
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
            index=default_index,
        )

        if team_options[selected_team_name] != st.session_state.get(
            "current_team_id"
        ):
            st.session_state["current_team_id"] = team_options[
                selected_team_name
            ]
            st.rerun()

        st.info(
            f"🔑 **Código da Equipe:** `{active_team.get('invite_code', 'N/A')}`"
        )

        with st.expander("➕ Entrar em Outra Equipe"):
            with st.form("sidebar_join_team"):
                new_code = st.text_input(
                    "Código de Convite", placeholder="Ex: A1B2C3"
                )
                if st.form_submit_button("Vincular Equipe"):
                    if new_code.strip():
                        t_lookup = (
                            supabase.table("teams")
                            .select("id, name")
                            .eq("invite_code", new_code.strip().upper())
                            .execute()
                        )
                        if t_lookup.data:
                            found_t = t_lookup.data[0]

                            # CORREÇÃO AQUI: Verifica a existência antes de inserir para evitar erro no Postgres
                            check_exists = (
                                supabase.table("team_members")
                                .select("id")
                                .eq("team_id", found_t["id"])
                                .eq("user_id", user_info["id"])
                                .execute()
                            )

                            if not check_exists.data:
                                supabase.table("team_members").insert({
                                    "team_id": found_t["id"],
                                    "user_id": user_info["id"],
                                    "role": "editor",
                                }).execute()

                            st.session_state["current_team_id"] = found_t["id"]
                            st.success(
                                f"Vinculado à equipe '{found_t['name']}' com"
                                " sucesso!"
                            )
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

    if not active_project and page in [
        "📝 Requisitos",
        "🧪 Módulo de Testes",
        "📊 Métricas & Exportação",
    ]:
        st.warning("⚠️ **Nenhum projeto selecionado!**")
        st.info(
            "Por favor, selecione ou crie um projeto no menu lateral (ou no"
            " módulo **Gestão de Projetos**) para prosseguir."
        )
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
        test_cases = (
            supabase.table("test_cases")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
        bug_reports = (
            supabase.table("bug_reports")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
        risk_matrix = (
            supabase.table("risk_matrix")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
        user_stories = (
            supabase.table("user_stories")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception as e:
        st.error(f"Erro ao carregar métricas do Supabase: {e}")
        test_cases, bug_reports, risk_matrix, user_stories = [], [], [], []

    metrics.render_metrics_dashboard(
        test_cases, bug_reports, risk_matrix, user_stories
    )

elif page == "👥 Gestão de Equipe":
    st.title("👥 Gestão de Membros da Equipe")
    st.write(f"Gerencie permissões e membros da equipe **{active_team.get('name')}**.")

    # 1. Busca os membros da equipe atual
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
                u_data["role"] = m.get("role", "editor")
                members.append(u_data)

    st.divider()

    # Dicionário amigável de funções
    ROLE_LABELS = {
        "admin": "Líder (Criar, Editar, Excluir, Gerenciar Time)",
        "editor": "Editor (Criar e Editar)",
        "viewer": "Leitor (Apenas Visualizar)"
    }
    ROLE_KEYS = list(ROLE_LABELS.keys())

    # 2. Lista todos os membros em tabela/cards
    for member in members:
        cols = st.columns([3, 3, 2, 2])
        
        with cols[0]:
            st.write(f"**{member['name']}**")
            st.caption(f"📧 {member['email']}")
        
        with cols[1]:
            is_self = (member["id"] == user_info["id"])
            current_role = member["role"] if member["role"] in ROLE_KEYS else "editor"
            current_role_index = ROLE_KEYS.index(current_role)

            if is_self:
                st.info(f"**Sua Função:** {ROLE_LABELS[current_role].split('(')[0]}")
            else:
                # Dropdown para alterar permissão do membro
                new_role_key = st.selectbox(
                    "Permissão",
                    options=ROLE_KEYS,
                    format_func=lambda x: ROLE_LABELS[x],
                    index=current_role_index,
                    key=f"role_sel_{member['id']}",
                    label_visibility="collapsed"
                )

                if new_role_key != member["role"]:
                    supabase.table("team_members") \
                        .update({"role": new_role_key}) \
                        .eq("team_id", active_team["id"]) \
                        .eq("user_id", member["id"]) \
                        .execute()
                    st.success(f"Permissão de {member['name']} atualizada para {ROLE_LABELS[new_role_key].split('(')[0]}!")
                    st.rerun()

        with cols[2]:
            st.caption(f"Vinculado em:\n{member['created_at'][:10] if member.get('created_at') else 'N/A'}")

        with cols[3]:
            if not is_self:
                # Botão para REMOVER O ACESSO do usuário à equipe
                if st.button("🗑️ Revogar Acesso", key=f"rm_mem_{member['id']}", type="secondary"):
                    supabase.table("team_members") \
                        .delete() \
                        .eq("team_id", active_team["id"]) \
                        .eq("user_id", member["id"]) \
                        .execute()
                    st.success(f"Acesso de {member['name']} removido com sucesso!")
                    st.rerun()
            else:
                st.caption("*(Sua conta)*")
        
        st.divider()

elif page == "👑 Painel Admin Master":
    admin_panel.render_master_admin_panel()
