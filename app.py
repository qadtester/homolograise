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
    .select("team_id, role, teams(id, name, invite_code, owner_id)")
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

# Se o usuário não está vinculado a nenhuma equipe (exceto Master), exibe onboarding
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
    user_info["role"] = active_team.get("user_role", "leitor")
else:
    active_team = {
        "name": "Painel Master Global",
        "invite_code": "MASTER",
        "owner_id": None,
    }

# IDENTIFICA SE O USUÁRIO LOGADO É O DONO/CRIADOR DA EQUIPE ATIVA
is_team_owner = active_team.get("owner_id") == user_info["id"]
user_info["is_team_owner"] = is_team_owner
user_info["is_master"] = is_master_user()

# ==============================================================================
# 4. SIDEBAR (PERFIL, SELETOR DE EQUIPE, PROJETO E NAVEGAÇÃO)
# ==============================================================================
with st.sidebar:
    st.title("🎯 QA Hub")

    st.write(f"👤 **Usuário:** {user_info.get('name', 'Usuário')}")
    st.caption(f"📧 {user_info.get('email', '')}")

    if is_master_user():
        st.caption("👑 **Papel Global:** `MASTER`")
    elif is_team_owner:
        st.caption("👑 **Papel na Equipe:** `Dono / Administrador`")
    else:
        st.caption(f"🛡️ **Papel na Equipe:** `{user_info.get('role', 'leitor').title()}`")

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

                            # Verifica se já está vinculado para evitar duplicidade no banco
                            check_exists = (
                                supabase.table("team_members")
                                .select("id")
                                .eq("team_id", found_t["id"])
                                .eq("user_id", user_info["id"])
                                .execute()
                            )

                            if not check_exists.data:
                                # Todo novo usuário vinculado entra por padrão como 'leitor'
                                supabase.table("team_members").insert({
                                    "team_id": found_t["id"],
                                    "user_id": user_info["id"],
                                    "role": "leitor",
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

    # REGRA RESTRITA: APENAS o Criador/Dono da equipe ou Usuário Master vê o menu de Gestão de Equipe
    if is_team_owner or is_master_user():
        page_options.append("👥 Gestão de Equipe")

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
    # TRAVA EXTRA DE SEGURANÇA NA ROTA
    if not is_team_owner and not is_master_user():
        st.error(
            "🚫 **Acesso Negado:** Apenas o Administrador/Dono da equipe pode"
            " gerenciar membros e permissões."
        )
        st.stop()

    st.title("👥 Gestão de Membros da Minha Equipe")
    st.write(
        "Gerencie permissões e acessos dos usuários vinculados à sua equipe"
        f" **{active_team.get('name')}**."
    )

    # 1. Busca os membros vinculados à equipe do Dono
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
                u_data["role"] = m.get("role", "leitor")
                members.append(u_data)

    st.divider()

    # Mapeamento dos papéis permitidos para atribuição pelo Dono
    ROLE_LABELS = {
        "gestor": "Gestor (Criar, Editar e Excluir)",
        "editor": "Editor (Criar e Editar)",
        "leitor": "Leitor (Apenas Visualizar)",
    }
    ROLE_KEYS = list(ROLE_LABELS.keys())

    # 2. Listagem de membros exclusiva para gestão do Dono
    for member in members:
        is_owner_user = member["id"] == active_team.get("owner_id")

        cols = st.columns([3, 4, 2, 2])

        with cols[0]:
            st.write(f"**{member['name']}**")
            st.caption(f"📧 {member['email']}")

        with cols[1]:
            if is_owner_user:
                st.success("👑 **Dono / Administrador**")
            else:
                # Normaliza papéis antigos/legados
                current_role = member["role"]
                if current_role not in ROLE_KEYS:
                    current_role = "leitor"

                current_role_index = ROLE_KEYS.index(current_role)

                # O Dono define o papel do usuário vinculado aqui
                new_role = st.selectbox(
                    "Papel na Equipe",
                    options=ROLE_KEYS,
                    format_func=lambda x: ROLE_LABELS[x],
                    index=current_role_index,
                    key=f"role_sel_{member['id']}",
                    label_visibility="collapsed",
                )

                if new_role != member["role"]:
                    supabase.table("team_members").update(
                        {"role": new_role}
                    ).eq("team_id", active_team["id"]).eq(
                        "user_id", member["id"]
                    ).execute()
                    st.success(
                        f"Papel de {member['name']} atualizado para"
                        f" {ROLE_LABELS[new_role].split('(')[0]}!"
                    )
                    st.rerun()

        with cols[2]:
            st.caption(
                "Entrou em:\n"
                f"{member['created_at'][:10] if member.get('created_at') else 'N/A'}"
            )

        with cols[3]:
            if not is_owner_user:
                # O Dono pode excluir o acesso do usuário da equipe
                if st.button(
                    "🗑️ Removê-lo",
                    key=f"rm_mem_{member['id']}",
                    type="secondary",
                ):
                    supabase.table("team_members").delete().eq(
                        "team_id", active_team["id"]
                    ).eq("user_id", member["id"]).execute()
                    st.success(f"{member['name']} foi removido da equipe.")
                    st.rerun()
            else:
                st.caption("*(Você)*")

        st.divider()

elif page == "👑 Painel Admin Master":
    admin_panel.render_master_admin_panel()
