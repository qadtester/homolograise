import hashlib
import streamlit as st
from config.database import supabase


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ------------------------------------------------------------------------------
# 1. TELA DE NOTIFICAÇÕES
# ------------------------------------------------------------------------------
def render_notifications_page():
    user = st.session_state.get("user")

    if not user:
        st.error("Usuário não autenticado.")
        return

    st.title("🔔 Central de Notificações")

    notifs_res = (
        supabase.table("notifications")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    notifications = notifs_res.data or []

    unread_count = sum(1 for n in notifications if not n["read"])

    if not notifications:
        st.info("Você não possui notificações.")
        return

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
        if st.button("🧹 Excluir todas as lidas", key="btn_del_read"):
            supabase.table("notifications").delete().eq(
                "user_id", user["id"]
            ).eq("read", True).execute()
            st.success("Notificações lidas excluídas!")
            st.rerun()

    st.divider()

    for n in notifications:
        unread_badge = "🔴 [Nova] " if not n["read"] else "🟢 [Lida] "
        created_date = (
            n.get("created_at", "")[:10] if n.get("created_at") else ""
        )

        with st.expander(f"{unread_badge}{n['title']} - {created_date}"):
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
                    st.rerun()


# ------------------------------------------------------------------------------
# 2. TELA DE PERFIL / SENHA
# ------------------------------------------------------------------------------
def render_user_profile_page():
    user = st.session_state.get("user")

    if not user:
        st.error("Usuário não autenticado.")
        return

    st.title("🔒 Meu Perfil / Alterar Senha")

    with st.form("change_password_form"):
        current_pwd = st.text_input("Senha Atual", type="password")
        new_pwd = st.text_input("Nova Senha", type="password")
        confirm_pwd = st.text_input("Confirme a Nova Senha", type="password")

        if st.form_submit_button("Atualizar Senha", type="primary"):
            if hash_password(current_pwd) != user.get("password_hash"):
                st.error("A senha atual informada está incorreta.")
            elif new_pwd != confirm_pwd:
                st.error("A nova senha e a confirmação não coincidem.")
            elif len(new_pwd) < 6:
                st.warning("A nova senha deve ter no mínimo 6 caracteres.")
            else:
                new_hash = hash_password(new_pwd)
                supabase.table("users").update(
                    {"password_hash": new_hash}
                ).eq("id", user["id"]).execute()
                st.session_state["user"]["password_hash"] = new_hash
                st.success("Senha alterada com sucesso!")
