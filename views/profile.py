import hashlib
import streamlit as st
from config.database import supabase


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def render_user_profile_page():
    user = st.session_state.get("user")

    if not user:
        st.error("Usuário não autenticado.")
        return

    # 1. Consulta inicial para contar quantas notificações NÃO LIDAS existem
    unread_res = (
        supabase.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user["id"])
        .eq("read", False)
        .execute()
    )
    unread_count = unread_res.count or 0

    # Sinalizador visual dinâmico com o sininho e o badge numérico
    badge_label = f" ({unread_count})" if unread_count > 0 else ""
    bell_icon = "🔔🔴" if unread_count > 0 else "🔔"

    st.title("👤 Meu Perfil e Configurações")

    tab_profile, tab_notifs = st.tabs(
        ["🔒 Trocar Senha", f"{bell_icon} Central de Notificações{badge_label}"]
    )

    # --- ABA 1: TROCA DE SENHA ---
    with tab_profile:
        st.subheader("Alterar Senha de Acesso")
        with st.form("change_password_form"):
            current_pwd = st.text_input("Senha Atual", type="password")
            new_pwd = st.text_input("Nova Senha", type="password")
            confirm_pwd = st.text_input(
                "Confirme a Nova Senha", type="password"
            )

            if st.form_submit_button("Atualizar Senha", type="primary"):
                if hash_password(current_pwd) != user.get("password_hash"):
                    st.error("A senha atual informada está incorreta.")
                elif new_pwd != confirm_pwd:
                    st.error("A nova senha e a confirmação não coincidem.")
                elif len(new_pwd) < 6:
                    st.warning(
                        "A nova senha deve ter no mínimo 6 caracteres."
                    )
                else:
                    new_hash = hash_password(new_pwd)
                    supabase.table("users").update(
                        {"password_hash": new_hash}
                    ).eq("id", user["id"]).execute()
                    st.session_state["user"]["password_hash"] = new_hash
                    st.success("Senha alterada com sucesso!")

    # --- ABA 2: CENTRAL DE NOTIFICAÇÕES COM AÇÕES EM MASSA E EXCLUSÃO ---
    with tab_notifs:
        st.subheader("Minhas Notificações")

        notifs_res = (
            supabase.table("notifications")
            .select("*")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        notifications = notifs_res.data or []

        if not notifications:
            st.info("Você não possui notificações.")
        else:
            # Botões de ações globais em lote
            col_actions1, col_actions2 = st.columns(2)
            with col_actions1:
                if unread_count > 0 and st.button(
                    "✔ Marcar todas como lidas", key="btn_read_all"
                ):
                    supabase.table("notifications").update({"read": True}).eq(
                        "user_id", user["id"]
                    ).execute()
                    st.rerun()

            with col_actions2:
                if st.button(
                    "🧹 Excluir todas as lidas", key="btn_del_read"
                ):
                    supabase.table("notifications").delete().eq(
                        "user_id", user["id"]
                    ).eq("read", True).execute()
                    st.success("Notificações lidas excluídas!")
                    st.rerun()

            st.divider()

            # Lista individual de notificações
            for n in notifications:
                unread_badge = "🔴 [Nova] " if not n["read"] else "🟢 [Lida] "
                created_date = (
                    n.get("created_at", "")[:10]
                    if n.get("created_at")
                    else ""
                )

                with st.expander(
                    f"{unread_badge}{n['title']} - {created_date}"
                ):
                    st.write(n["message"])

                    st.divider()
                    c_read, c_delete = st.columns([1, 1])

                    with c_read:
                        if not n["read"]:
                            if st.button(
                                "✔ Marcar como Lida", key=f"read_notif_{n['id']}"
                            ):
                                supabase.table("notifications").update(
                                    {"read": True}
                                ).eq("id", n["id"]).execute()
                                st.rerun()

                    with c_delete:
                        if st.button(
                            "🗑️ Excluir Notificação",
                            key=f"del_notif_{n['id']}",
                            type="primary",
                        ):
                            supabase.table("notifications").delete().eq(
                                "id", n["id"]
                            ).execute()
                            st.success("Notificação excluída!")
                            st.rerun()import hashlib
import streamlit as st
from config.database import supabase


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def render_user_profile_page():
    st.title("👤 Meu Perfil e Configurações")
    user = st.session_state.get("user")

    if not user:
        st.error("Usuário não autenticado.")
        return

    tab_profile, tab_notifs = st.tabs(
        ["🔒 Trocar Senha", "🔔 Central de Notificações"]
    )

    # --- ABA 1: TROCA DE SENHA ---
    with tab_profile:
        st.subheader("Alterar Senha de Acesso")
        with st.form("change_password_form"):
            current_pwd = st.text_input("Senha Atual", type="password")
            new_pwd = st.text_input("Nova Senha", type="password")
            confirm_pwd = st.text_input(
                "Confirme a Nova Senha", type="password"
            )

            if st.form_submit_button("Atualizar Senha", type="primary"):
                if hash_password(current_pwd) != user.get("password_hash"):
                    st.error("A senha atual informada está incorreta.")
                elif new_pwd != confirm_pwd:
                    st.error("A nova senha e a confirmação não coincidem.")
                elif len(new_pwd) < 6:
                    st.warning(
                        "A nova senha deve ter no mínimo 6 caracteres."
                    )
                else:
                    new_hash = hash_password(new_pwd)
                    supabase.table("users").update(
                        {"password_hash": new_hash}
                    ).eq("id", user["id"]).execute()
                    st.session_state["user"]["password_hash"] = new_hash
                    st.success("Senha alterada com sucesso!")

    # --- ABA 2: NOTIFICAÇÕES DO USUÁRIO ---
    with tab_notifs:
        st.subheader("Minhas Notificações")

        # Correção aqui: trocado ascending=False por desc=True
        notifs_res = (
            supabase.table("notifications")
            .select("*")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        notifications = notifs_res.data or []

        if not notifications:
            st.info("Você não possui novas notificações.")
        else:
            for n in notifications:
                unread_badge = "🔴 " if not n["read"] else ""
                with st.expander(
                    f"{unread_badge}{n['title']} - {n['created_at'][:10]}"
                ):
                    st.write(n["message"])
                    if not n["read"]:
                        if st.button("Marcar como Lida", key=f"notif_{n['id']}"):
                            supabase.table("notifications").update(
                                {"read": True}
                            ).eq("id", n["id"]).execute()
                            st.rerun()
