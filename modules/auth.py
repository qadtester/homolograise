import streamlit as st
import hashlib
import uuid
import random
import string
from config.database import supabase


def hash_password(password: str) -> str:
    """Gera um hash SHA-256 para a senha."""
    return hashlib.sha256(password.encode()).hexdigest()


def logout():
    """Limpa os dados do usuário da sessão e reinicia a aplicação."""
    st.session_state["user"] = None
    st.session_state["logged_in"] = False
    st.session_state["current_team_id"] = None
    st.rerun()


def render_auth_page():
    """Exibe a interface gráfica de autenticação (Login e Cadastro)."""
    st.title("🔐 QA & Requisitos Hub")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None

    if st.session_state["logged_in"]:
        return

    tab_login, tab_register = st.tabs(["🔑 Entrar", "📝 Criar Conta"])

    # --- ABA DE LOGIN ---
    with tab_login:
        st.subheader("Acesse sua Conta")
        with st.form("login_form"):
            email = st.text_input("E-mail :red[*]")
            password = st.text_input("Senha :red[*]", type="password")
            submit_login = st.form_submit_button("Entrar", type="primary")

            if submit_login:
                if email and password:
                    try:
                        users_res = (
                            supabase.table("users")
                            .select("*")
                            .eq("email", email.strip())
                            .execute()
                        )
                        if users_res.data and len(users_res.data) > 0:
                            user = users_res.data[0]
                            if user["password_hash"] == hash_password(password):
                                st.session_state["user"] = user
                                st.session_state["logged_in"] = True
                                
                                # Busca todas as equipes às quais o usuário pertence
                                teams_query = (
                                    supabase.table("team_members")
                                    .select("team_id")
                                    .eq("user_id", user["id"])
                                    .execute()
                                )
                                
                                if teams_query.data:
                                    st.session_state["current_team_id"] = teams_query.data[0]["team_id"]
                                elif user.get("team_id"):
                                    st.session_state["current_team_id"] = user["team_id"]
                                else:
                                    st.session_state["current_team_id"] = None

                                st.success("Login realizado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                        else:
                            st.error("E-mail não encontrado.")
                    except Exception as e:
                        st.error(f"Erro ao realizar login: {e}")
                else:
                    st.error("Preencha todos os campos obrigatórios.")

    # --- ABA DE CADASTRO ---
    with tab_register:
        st.subheader("Crie sua Conta e sua Equipe Principal")
        with st.form("register_form"):
            name = st.text_input("Nome Completo :red[*]")
            email = st.text_input("E-mail de Cadastro :red[*]")
            password = st.text_input("Senha :red[*]", type="password")
            team_name = st.text_input("Nome da sua Equipe/Empresa Principal :red[*]", placeholder="Ex: QA Solutions")
            
            submit_register = st.form_submit_button("Criar Conta", type="primary")

            if submit_register:
                if name and email and password and team_name:
                    try:
                        check_email = supabase.table("users").select("id").eq("email", email.strip()).execute()
                        if check_email.data:
                            st.error("Este e-mail já está cadastrado.")
                        else:
                            # 1. Cria a Equipe
                            invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                            team_payload = {
                                "name": team_name.strip(),
                                "invite_code": invite_code
                            }
                            team_res = supabase.table("teams").insert(team_payload).execute()
                            
                            if team_res.data:
                                new_team = team_res.data[0]
                                
                                # 2. Cria o Usuário
                                user_payload = {
                                    "name": name.strip(),
                                    "email": email.strip(),
                                    "password_hash": hash_password(password),
                                    "team_id": new_team["id"],
                                    "role": "admin"
                                }
                                user_res = supabase.table("users").insert(user_payload).execute()
                                
                                if user_res.data:
                                    new_user = user_res.data[0]
                                    
                                    # 3. Vincula o Usuário à Equipe no N:N
                                    supabase.table("team_members").insert({
                                        "team_id": new_team["id"],
                                        "user_id": new_user["id"],
                                        "role": "admin"
                                    }).execute()
                                    
                                    # 4. Atualiza o Dono da Equipe
                                    supabase.table("teams").update({"owner_id": new_user["id"]}).eq("id", new_team["id"]).execute()

                                    st.session_state["user"] = new_user
                                    st.session_state["logged_in"] = True
                                    st.session_state["current_team_id"] = new_team["id"]
                                    
                                    st.success(f"Conta criada com sucesso! Sua equipe '{team_name}' foi configurada.")
                                    st.rerun()
                                else:
                                    st.error("Erro ao criar registro do usuário.")
                            else:
                                st.error("Erro ao criar registro da equipe.")
                    except Exception as e:
                        st.error(f"Erro no cadastro: {e}")
                else:
                    st.error("Preencha todos os campos obrigatórios.")


def render_team_onboarding():
    """Tela exibida caso o usuário não esteja vinculado a nenhuma equipe."""
    st.title("👥 Gestão de Equipes e Organizações")
    user = st.session_state.get("user", {})
    
    st.write(f"Olá, **{user.get('name', 'Usuário')}**. Você precisa estar em uma equipe para gerenciar projetos.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("✨ Criar Nova Equipe")
        with st.form("create_extra_team_form"):
            new_t_name = st.text_input("Nome da Nova Equipe :red[*]")
            if st.form_submit_button("Criar Equipe"):
                if new_t_name.strip():
                    try:
                        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        t_res = supabase.table("teams").insert({
                            "name": new_t_name.strip(), 
                            "invite_code": invite_code, 
                            "owner_id": user["id"]
                        }).execute()
                        
                        if t_res.data:
                            created_team = t_res.data[0]
                            
                            supabase.table("team_members").insert({
                                "team_id": created_team["id"],
                                "user_id": user["id"],
                                "role": "admin"
                            }).execute()
                            
                            st.session_state["current_team_id"] = created_team["id"]
                            st.success(f"Equipe '{new_t_name}' criada com sucesso!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar equipe: {e}")
                else:
                    st.error("Informe o nome da equipe.")

    with c2:
        st.subheader("🔗 Entrar em Equipe via Código")
        with st.form("join_extra_team_form"):
            code_input = st.text_input("Código de Convite (ex: A1B2C3) :red[*]")
            if st.form_submit_button("Entrar na Equipe"):
                if code_input.strip():
                    try:
                        team_res = supabase.table("teams").select("*").eq("invite_code", code_input.strip().upper()).execute()
                        if team_res.data:
                            target_team = team_res.data[0]
                            
                            # Checa se o vínculo já existe antes de inserir para não quebrar no banco
                            existing_member = supabase.table("team_members") \
                                .select("*") \
                                .eq("team_id", target_team["id"]) \
                                .eq("user_id", user["id"]) \
                                .execute()
                            
                            if not existing_member.data:
                                supabase.table("team_members").insert({
                                    "team_id": target_team["id"],
                                    "user_id": user["id"],
                                    "role": "editor"
                                }).execute()
                            
                            st.session_state["current_team_id"] = target_team["id"]
                            st.success(f"Você agora faz parte da equipe '{target_team['name']}'!")
                            st.rerun()
                        else:
                            st.error("Código de convite inválido.")
                    except Exception as e:
                        st.error(f"Erro ao vincular à equipe: {e}")
                else:
                    st.error("Digite o código.")


def render_team_selector_sidebar():
    """Componente utilitário para colocar na Sidebar e permitir trocar de equipe."""
    user = st.session_state.get("user")
    if not user:
        return

    try:
        # Busca todas as equipes que o usuário faz parte
        memberships = supabase.table("team_members").select("team_id").eq("user_id", user["id"]).execute()
        if memberships.data:
            team_ids = [m["team_id"] for m in memberships.data]
            teams_res = supabase.table("teams").select("id, name").in_("id", team_ids).execute()
            
            if teams_res.data:
                team_options = {t["name"]: t["id"] for t in teams_res.data}
                
                # Procura o índice da equipe atual
                current_id = st.session_state.get("current_team_id")
                current_name = next((name for name, t_id in team_options.items() if t_id == current_id), list(team_options.keys())[0])
                
                selected_team_name = st.sidebar.selectbox(
                    "🏢 Equipe Ativa",
                    options=list(team_options.keys()),
                    index=list(team_options.keys()).index(current_name)
                )
                
                new_selected_id = team_options[selected_team_name]
                if new_selected_id != st.session_state.get("current_team_id"):
                    st.session_state["current_team_id"] = new_selected_id
                    st.rerun()
    except Exception:
        pass


def is_authenticated() -> bool:
    return st.session_state.get("logged_in", False) and st.session_state.get("user") is not None


def get_logged_user() -> dict:
    return st.session_state.get("user", {})
