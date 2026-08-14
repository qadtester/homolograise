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
                            
                            # Define a equipe padrão do usuário (a primeira vinculada na tabela team_members ou team_id)
                            teams_query = supabase.table("team_members").select("team_id, role").eq("user_id", user["id"]).execute()
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
                    # Verifica se e-mail já existe
                    check_email = supabase.table("users").select("id").eq("email", email.strip()).execute()
                    if check_email.data:
                        st.error("Este e-mail já está cadastrado.")
                    else:
                        try:
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
                                    "team_id": new_team["id"], # Mantém retrocompatibilidade
                                    "role": "admin"
                                }
                                user_res = supabase.table("users").insert(user_payload).execute()
                                
                                if user_res.data:
                                    new_user = user_res.data[0]
                                    
                                    # 3. Vincula na tabela N para N como admin da própria equipe
                                    supabase.table("team_members").insert({
                                        "team_id": new_team["id"],
                                        "user_id": new_user["id"],
                                        "role": "admin"
                                    }).execute()
                                    
                                    # Atualiza o owner_id da equipe
                                    supabase.table("teams").update({"owner_id": new_user["id"]}).eq("id", new_team["id"]).execute()

                                    st.session_state["user"] = new_user
                                    st.session_state["logged_in"] = True
                                    st.session_state["current_team_id"] = new_team["id"]
                                    
                                    st.success(f"Conta criada com sucesso! Sua equipe '{team_name}' foi configurada.")
                                    st.rerun()
                                else:
                                    st.error("Erro ao criar usuário.")
                            else:
                                st.error("Erro ao criar equipe.")
                        except Exception as e:
                            st.error(f"Erro no cadastro: {e}")
                else:
                    st.error("Preencha todos os campos obrigatórios.")


def render_team_onboarding():
    """Tela exibida caso o usuário não esteja vinculado a nenhuma equipe."""
    st.title("👥 Gestão de Equipes e Organizações")
    user = st.session_state.get("user")
    
    st.write(f"Olá, **{user.get('name')}**. Você precisa estar em uma equipe para gerenciar projetos.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("✨ Criar Nova Equipe")
        with st.form("create_extra_team_form"):
            new_t_name = st.text_input("Nome da Nova Equipe :red[*]")
            if st.form_submit_button("Criar Equipe"):
                if new_t_name.strip():
                    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    t_res = supabase.table("teams").insert({"name": new_t_name.strip(), "invite_code": invite_code, "owner_id": user["id"]}).execute()
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
                else:
                    st.error("Informe o nome da equipe.")

    with c2:
        st.subheader("🔗 Entrar em Equipe via Código")
        with st.form("join_extra_team_form"):
            code_input = st.text_input("Código de Convite (ex: A1B2C3) :red[*]")
            if st.form_submit_button("Entrar na Equipe"):
                if code_input.strip():
                    team_res = supabase.table("teams").select("*").eq("invite_code", code_input.strip().upper()).execute()
                    if team_res.data:
                        target_team = team_res.data[0]
                        # Insere na tabela team_members (se já não pertencer)
                        supabase.table("team_members").upsert({
                            "team_id": target_team["id"],
                            "user_id": user["id"],
                            "role": "editor"
                        }, on_conflict="team_id,user_id").execute()
                        
                        st.session_state["current_team_id"] = target_team["id"]
                        st.success(f"Você agora faz parte da equipe '{target_team['name']}'!")
                        st.rerun()
                    else:
                        st.error("Código de convite inválido.")
                else:
                    st.error("Digite o código.")


def is_authenticated() -> bool:
    return st.session_state.get("logged_in", False) and st.session_state.get("user") is not None


def get_logged_user() -> dict:
    return st.session_state.get("user", {})