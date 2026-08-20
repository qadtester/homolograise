import streamlit as st
from config.ai_config import is_master_user
from config.database import supabase


def render_master_admin_panel():
    # Validação estrita do Usuário Master via MASTER_EMAIL
    if not is_master_user():
        st.error(
            "⛔ Acesso negado. Esta área é restrita exclusivamente ao Usuário Master."
        )
        return

    st.title("👑 Painel Administrativo Master")
    st.markdown("Gerenciamento global de usuários e projetos da plataforma.")

    tab_users, tab_projects = st.tabs(
        ["👥 Gerenciar Usuários", "📁 Gerenciar Projetos"]
    )

    # -------------------------------------------------------------
    # ABA 1: GERENCIAMENTO DE USUÁRIOS, EDIÇÃO E EXCLUSÃO EM CASCATA
    # -------------------------------------------------------------
    with tab_users:
        st.subheader("Lista de Usuários Cadastrados")

        users_res = supabase.table("users").select("*").execute()
        users = users_res.data or []

        if not users:
            st.info("Nenhum usuário cadastrado.")
        else:
            for u in users:
                with st.expander(
                    f"👤 {u['name']} ({u['email']}) - Criado em: {u.get('created_at', '')[:10]}"
                ):
                    st.write(f"**ID:** `{u['id']}`")
                    st.write(f"**Papel:** `{u.get('role', 'editor')}`")

                    # Identifica equipes em que ele é owner
                    teams_owned = (
                        supabase.table("teams")
                        .select("id, name")
                        .eq("owner_id", u["id"])
                        .execute()
                        .data
                        or []
                    )
                    team_ids_owned = [t["id"] for t in teams_owned]

                    exclusive_projects = []
                    if team_ids_owned:
                        proj_res = (
                            supabase.table("projects")
                            .select("id, name")
                            .in_("team_id", team_ids_owned)
                            .execute()
                        )
                        exclusive_projects = proj_res.data or []

                    st.markdown(
                        f"**Projetos exclusivos da conta:** {len(exclusive_projects)}"
                    )
                    if exclusive_projects:
                        for ep in exclusive_projects:
                            st.caption(f"- 📁 {ep['name']} (`{ep['id']}`)")

                    st.divider()

                    # ---------------------------------------------------------
                    # SEÇÃO DE EDIÇÃO DE DADOS DO USUÁRIO
                    # ---------------------------------------------------------
                    st.markdown("### ✏️ Alterar Dados do Usuário")
                    with st.form(key=f"form_edit_user_{u['id']}"):
                        new_name = st.text_input(
                            "Nome Completo",
                            value=u.get("name", ""),
                            key=f"edit_name_{u['id']}",
                        )
                        new_email = st.text_input(
                            "Endereço de E-mail",
                            value=u.get("email", ""),
                            key=f"edit_email_{u['id']}",
                        )
                        new_password = st.text_input(
                            "Nova Senha (deixe em branco para não alterar)",
                            type="password",
                            placeholder="Digite a nova senha...",
                            key=f"edit_pass_{u['id']}",
                        )

                        btn_update = st.form_submit_button(
                            "💾 Salvar Alterações do Usuário"
                        )

                        if btn_update:
                            if not new_name.strip() or not new_email.strip():
                                st.error("Nome e E-mail não podem ficar vazios.")
                            else:
                                update_payload = {
                                    "name": new_name.strip(),
                                    "email": new_email.strip(),
                                }

                                # Atualiza a senha somente se o campo for preenchido
                                if new_password.strip():
                                    update_payload["password"] = (
                                        new_password.strip()
                                    )

                                try:
                                    supabase.table("users").update(
                                        update_payload
                                    ).eq("id", u["id"]).execute()
                                    st.success(
                                        f"Dados do usuário {new_name} atualizados com sucesso!"
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.error(
                                        f"Erro ao atualizar dados do usuário: {e}"
                                    )

                    st.divider()

                    # Botão de exclusão com confirmação em cascata
                    del_key = f"del_user_{u['id']}"
                    if st.button(
                        f"🗑️ Excluir Usuário e Dados Relacionados",
                        key=del_key,
                        type="primary",
                    ):
                        try:
                            # 1. Limpa o vínculo do usuário atual de qualquer equipe
                            supabase.table("users").update(
                                {"team_id": None}
                            ).eq("id", u["id"]).execute()

                            # 2. Se o usuário for dono de equipes, desvincula OUTROS usuários dessas equipes
                            if team_ids_owned:
                                supabase.table("users").update(
                                    {"team_id": None}
                                ).in_("team_id", team_ids_owned).execute()

                            # 3. Apaga dependências dos projetos exclusivos
                            for ep in exclusive_projects:
                                p_id = ep["id"]
                                supabase.table("personas").delete().eq(
                                    "project_id", p_id
                                ).execute()
                                supabase.table("user_stories").delete().eq(
                                    "project_id", p_id
                                ).execute()
                                supabase.table("test_cases").delete().eq(
                                    "project_id", p_id
                                ).execute()
                                supabase.table("bug_reports").delete().eq(
                                    "project_id", p_id
                                ).execute()
                                supabase.table("risk_matrix").delete().eq(
                                    "project_id", p_id
                                ).execute()
                                supabase.table(
                                    "project_documents"
                                ).delete().eq("project_id", p_id).execute()

                            # 4. Apaga os projetos das equipes do owner
                            if team_ids_owned:
                                supabase.table("projects").delete().in_(
                                    "team_id", team_ids_owned
                                ).execute()

                            # 5. Remove TODOS os membros vinculados às equipes desse owner
                            if team_ids_owned:
                                supabase.table("team_members").delete().in_(
                                    "team_id", team_ids_owned
                                ).execute()

                            # 6. Remove vínculos diretos do próprio usuário na tabela team_members
                            supabase.table("team_members").delete().eq(
                                "user_id", u["id"]
                            ).execute()

                            # 7. Apaga as equipes das quais ele era owner
                            if team_ids_owned:
                                supabase.table("teams").delete().in_(
                                    "id", team_ids_owned
                                ).execute()

                            # 8. Por fim, deleta o registro principal do usuário
                            supabase.table("users").delete().eq(
                                "id", u["id"]
                            ).execute()

                            st.success(
                                f"Usuário {u['name']} e todos os dados relacionados foram excluídos com sucesso!"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(
                                f"Erro ao executar exclusão em cascata: {e}"
                            )

    # -------------------------------------------------------------
    # ABA 2: GERENCIAMENTO DE PROJETOS GLOBAIS
    # -------------------------------------------------------------
    with tab_projects:
        st.subheader("Todos os Projetos no Banco de Dados")
        projects_res = (
            supabase.table("projects").select("*, teams(name)").execute()
        )
        all_projects = projects_res.data or []

        if not all_projects:
            st.info("Nenhum projeto encontrado no sistema.")
        else:
            for proj in all_projects:
                team_name = (
                    proj.get("teams", {}).get("name", "Desconhecido")
                    if proj.get("teams")
                    else "Desconhecido"
                )
                with st.expander(
                    f"📁 {proj['name']} (Equipe: {team_name})"
                ):
                    st.write(
                        f"**Descrição:** {proj.get('description', 'Sem descrição')}"
                    )
                    st.write(f"**ID do Projeto:** `{proj['id']}`")

                    if st.button(
                        f"🗑️ Excluir Projeto Individualmente",
                        key=f"del_proj_{proj['id']}",
                    ):
                        p_id = proj["id"]
                        supabase.table("personas").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("user_stories").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("test_cases").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("bug_reports").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("risk_matrix").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("project_documents").delete().eq(
                            "project_id", p_id
                        ).execute()
                        supabase.table("projects").delete().eq(
                            "id", p_id
                        ).execute()
                        st.success(
                            "Projeto e dados vinculados removidos com sucesso!"
                        )
                        st.rerun()
