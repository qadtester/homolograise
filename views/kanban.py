import datetime
import streamlit as st
from config.database import supabase
from utils.permissions import can_delete_items, can_edit


def notify_user(user_id: str, title: str, message: str):
    try:
        supabase.table("notifications").insert(
            {"user_id": user_id, "title": title, "message": message}
        ).execute()
    except Exception as e:
        st.error(f"Erro ao notificar usuário: {e}")


def get_severity_badge(severity: str) -> str:
    mapping = {
        "Baixa": "🟢 Baixa",
        "Média": "🟡 Média",
        "Alta": "🟠 Alta",
        "Crítica": "🔴 Crítica",
    }
    return mapping.get(severity, "⚪ " + str(severity))


def delete_attachment_from_storage(file_path: str):
    """Função utilitária para remover um arquivo do bucket no Supabase Storage."""
    try:
        supabase.storage.from_("evidences").remove([file_path])
    except Exception as e:
        st.error(f"Erro ao deletar arquivo do storage: {e}")


def render_kanban_board(project_id: str):
    st.title("📌 Quadro Kanban")

    user_info = st.session_state.get("user", {})
    team_id = st.session_state.get("current_team_id")

    # 1. BUSCA DE MEMBROS DA EQUIPE
    team_members = []
    if team_id:
        res = (
            supabase.table("team_members")
            .select("user_id, users!team_members_user_id_fkey(id, name, email)")
            .eq("team_id", team_id)
            .execute()
        )
        team_members = [
            row["users"] for row in (res.data or []) if row.get("users")
        ]

    member_options = {m["name"]: m["id"] for m in team_members}
    member_options["Não atribuído"] = None

    # 2. CARREGA AS COLUNAS
    cols_res = (
        supabase.table("kanban_columns")
        .select("*")
        .eq("project_id", project_id)
        .order("position")
        .execute()
    )
    columns_data = cols_res.data or []

    if not columns_data:
        defaults = ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"]
        for idx, name in enumerate(defaults):
            supabase.table("kanban_columns").insert(
                {"project_id": project_id, "name": name, "position": idx + 1}
            ).execute()
        st.rerun()

    # 3. BOTÕES DE AÇÃO
    c_act1, c_act2, _ = st.columns([2, 2, 6])

    with c_act1:
        if can_edit(user_info) and st.button(
            "➕ Novo Card", use_container_width=True, type="primary"
        ):
            st.session_state["open_new_card_modal"] = True

    with c_act2:
        if can_edit(user_info) and st.button(
            "⚙️ Gerenciar Colunas", use_container_width=True
        ):
            st.session_state["open_manage_cols_modal"] = True

    # --- MODAL: CRIAR CARD NO KANBAN ---
    if st.session_state.get("open_new_card_modal", False):
        with st.expander("📝 Criar Novo Card no Kanban", expanded=True):
            with st.form("form_create_kanban_card"):
                f_title = st.text_input("Título da Tarefa *")
                f_desc = st.text_area("Descrição / Detalhes")
                col_f1, col_f2, col_f3 = st.columns(3)

                with col_f1:
                    f_sev = st.selectbox(
                        "Prioridade/Severidade",
                        ["Baixa", "Média", "Alta", "Crítica"],
                    )
                with col_f2:
                    f_col = st.selectbox(
                        "Coluna Inicial", [c["name"] for c in columns_data]
                    )
                with col_f3:
                    f_assignee = st.selectbox(
                        "Atribuir a", list(member_options.keys())
                    )

                submitted = st.form_submit_button("Salvar Tarefa")

                if submitted:
                    if not f_title.strip():
                        st.error("O título é obrigatório.")
                    else:
                        payload = {
                            "project_id": project_id,
                            "title": f_title.strip(),
                            "description": f_desc.strip(),
                            "severity": f_sev,
                            "status": f_col,
                            "assignee_id": member_options[f_assignee],
                            "comments": [],
                            "attachments": [],
                        }
                        supabase.table("kanban_cards").insert(payload).execute()

                        if member_options[f_assignee]:
                            notify_user(
                                member_options[f_assignee],
                                "Nova Tarefa Atribuída 📋",
                                f"Você foi atribuído ao card: '{f_title}'",
                            )

                        st.session_state["open_new_card_modal"] = False
                        st.success("Card criado com sucesso!")
                        st.rerun()

            if st.button("Cancelar", key="cancel_card_create"):
                st.session_state["open_new_card_modal"] = False
                st.rerun()

    # --- MODAL: GERENCIAR COLUNAS ---
    if st.session_state.get("open_manage_cols_modal", False):
        with st.expander("🛠️ Organizar Colunas", expanded=True):
            t_add, t_ord, t_del = st.tabs(
                ["Adicionar Coluna", "Reordenar Colunas", "Excluir Coluna"]
            )

            with t_add:
                col_name_input = st.text_input("Nome da nova coluna:")
                if st.button("Salvar Nova Coluna"):
                    if col_name_input.strip():
                        max_p = max(
                            [c["position"] for c in columns_data], default=0
                        )
                        supabase.table("kanban_columns").insert(
                            {
                                "project_id": project_id,
                                "name": col_name_input.strip(),
                                "position": max_p + 1,
                            }
                        ).execute()
                        st.rerun()

            with t_ord:
                st.write("Ajuste a ordem das colunas no quadro:")
                for i, col_item in enumerate(columns_data):
                    c_name, c_btn_up, c_btn_down = st.columns([6, 1, 1])
                    c_name.markdown(f"**{i+1}. {col_item['name']}**")

                    if i > 0 and c_btn_up.button(
                        "⬆️", key=f"up_{col_item['id']}"
                    ):
                        prev = columns_data[i - 1]
                        supabase.table("kanban_columns").update(
                            {"position": prev["position"]}
                        ).eq("id", col_item["id"]).execute()
                        supabase.table("kanban_columns").update(
                            {"position": col_item["position"]}
                        ).eq("id", prev["id"]).execute()
                        st.rerun()

                    if i < len(columns_data) - 1 and c_btn_down.button(
                        "⬇️", key=f"down_{col_item['id']}"
                    ):
                        nxt = columns_data[i + 1]
                        supabase.table("kanban_columns").update(
                            {"position": nxt["position"]}
                        ).eq("id", col_item["id"]).execute()
                        supabase.table("kanban_columns").update(
                            {"position": col_item["position"]}
                        ).eq("id", nxt["id"]).execute()
                        st.rerun()

            with t_del:
                del_target = st.selectbox(
                    "Escolha a coluna para remover:",
                    [c["name"] for c in columns_data],
                )
                if st.button("Remover Coluna", type="primary"):
                    target_obj = next(
                        c for c in columns_data if c["name"] == del_target
                    )
                    supabase.table("kanban_columns").delete().eq(
                        "id", target_obj["id"]
                    ).execute()
                    st.rerun()

            if st.button("Fechar Gerenciador de Colunas"):
                st.session_state["open_manage_cols_modal"] = False
                st.rerun()

    st.divider()

    # 4. FILTROS
    with st.expander("🔍 Filtros Avançados", expanded=False):
        fl1, fl2, fl3 = st.columns(3)
        with fl1:
            filter_sev = st.multiselect(
                "Filtrar por Severidade/Prioridade",
                ["Baixa", "Média", "Alta", "Crítica"],
            )
        with fl2:
            filter_assignee = st.multiselect(
                "Filtrar por Atribuído", list(member_options.keys())
            )
        with fl3:
            filter_search = st.text_input("Buscar por Título / Palavra-chave")

    # 5. CARREGA CARDS DO KANBAN
    cards_res = (
        supabase.table("kanban_cards")
        .select("*, users!kanban_cards_assignee_id_fkey(name)")
        .eq("project_id", project_id)
        .execute()
    )
    cards = cards_res.data or []

    filtered_cards = []
    for c in cards:
        if filter_sev and c.get("severity") not in filter_sev:
            continue
        c_assignee_name = (
            c.get("users", {}).get("name")
            if c.get("users")
            else "Não atribuído"
        )
        if filter_assignee and c_assignee_name not in filter_assignee:
            continue
        if (
            filter_search
            and filter_search.lower() not in c.get("title", "").lower()
        ):
            continue
        filtered_cards.append(c)

    # 6. EXIBIÇÃO DAS COLUNAS E CARDS
    ui_cols = st.columns(len(columns_data)) if columns_data else []

    for idx, col_info in enumerate(columns_data):
        col_name = col_info["name"]
        col_cards = [
            card for card in filtered_cards if card.get("status") == col_name
        ]

        with ui_cols[idx]:
            st.markdown(f"#### **{col_name}** `({len(col_cards)})`")
            st.markdown("---")

            for card in col_cards:
                badge = get_severity_badge(card.get("severity", "Baixa"))
                assigned_name = (
                    card.get("users", {}).get("name")
                    if card.get("users")
                    else "Não atribuído"
                )

                with st.expander(f"{badge} {card['title']}"):
                    st.caption(f"**Atribuído:** {assigned_name}")
                    st.write(card.get("description") or "*Sem descrição*")
                    st.divider()

                    tab_actions, tab_edit, tab_comments = st.tabs(
                        ["⚡ Mover/Atribuir", "✏️ Editar", "💬 Comentários"]
                    )

                    with tab_actions:
                        if can_edit(user_info):
                            col_names = [c["name"] for c in columns_data]
                            new_col = st.selectbox(
                                "Mover para:",
                                col_names,
                                index=col_names.index(col_name),
                                key=f"mov_{card['id']}",
                            )
                            if new_col != col_name:
                                supabase.table("kanban_cards").update(
                                    {"status": new_col}
                                ).eq("id", card["id"]).execute()
                                st.rerun()

                            cur_assignee_key = next(
                                (
                                    k
                                    for k, v in member_options.items()
                                    if v == card.get("assignee_id")
                                ),
                                "Não atribuído",
                            )
                            new_assignee_key = st.selectbox(
                                "Reatribuir a:",
                                list(member_options.keys()),
                                index=list(member_options.keys()).index(
                                    cur_assignee_key
                                ),
                                key=f"assign_{card['id']}",
                            )
                            if (
                                member_options[new_assignee_key]
                                != card.get("assignee_id")
                            ):
                                new_uid = member_options[new_assignee_key]
                                supabase.table("kanban_cards").update(
                                    {"assignee_id": new_uid}
                                ).eq("id", card["id"]).execute()
                                if new_uid:
                                    notify_user(
                                        new_uid,
                                        "Reatribuição de Tarefa 📋",
                                        f"O card '{card['title']}' foi reatribuído a você.",
                                    )
                                st.rerun()

                    with tab_edit:
                        if can_edit(user_info):
                            with st.form(key=f"form_edit_card_{card['id']}"):
                                e_title = st.text_input(
                                    "Título", value=card.get("title", "")
                                )
                                e_desc = st.text_area(
                                    "Descrição",
                                    value=card.get("description", ""),
                                )
                                e_sev = st.selectbox(
                                    "Severidade",
                                    ["Baixa", "Média", "Alta", "Crítica"],
                                    index=[
                                        "Baixa",
                                        "Média",
                                        "Alta",
                                        "Crítica",
                                    ].index(card.get("severity", "Baixa")),
                                )

                                if st.form_submit_button("Salvar Edição"):
                                    supabase.table("kanban_cards").update(
                                        {
                                            "title": e_title.strip(),
                                            "description": e_desc.strip(),
                                            "severity": e_sev,
                                        }
                                    ).eq("id", card["id"]).execute()
                                    st.success("Card atualizado!")
                                    st.rerun()

                    with tab_comments:
                        comments = card.get("comments") or []
                        if comments:
                            for com in comments:
                                st.markdown(
                                    f"**{com.get('author', 'Usuário')}**: {com.get('text')}"
                                )
                                st.caption(f"_{com.get('date', '')}_")
                                st.divider()
                        else:
                            st.caption("Nenhum comentário.")

                        new_comment_text = st.text_area(
                            "Adicionar comentário:",
                            key=f"comm_input_{card['id']}",
                        )
                        if st.button(
                            "Enviar Comentário", key=f"btn_comm_{card['id']}"
                        ):
                            if new_comment_text.strip():
                                author_name = user_info.get("name", "Usuário")
                                now_str = datetime.datetime.now().strftime(
                                    "%d/%m/%Y %H:%M"
                                )
                                updated_comments = comments + [
                                    {
                                        "author": author_name,
                                        "text": new_comment_text.strip(),
                                        "date": now_str,
                                    }
                                ]
                                supabase.table("kanban_cards").update(
                                    {"comments": updated_comments}
                                ).eq("id", card["id"]).execute()
                                st.success("Comentário salvo!")
                                st.rerun()

                    st.divider()

                    # ANEXOS (COM SUPORTE A REMOÇÃO E LIMITE DE 10MB)
                    st.markdown("**📎 Anexos:**")
                    st.caption("Limite máximo: 10 MB por arquivo")

                    attachments = card.get("attachments") or []
                    if attachments:
                        for idx_att, att in enumerate(attachments):
                            if isinstance(att, dict) and att.get("url"):
                                col_att1, col_att2 = st.columns([5, 1])
                                with col_att1:
                                    st.markdown(
                                        f"📄 [{att.get('name', 'Arquivo')}]({att.get('url')})"
                                    )
                                with col_att2:
                                    if can_edit(user_info) and st.button(
                                        "❌", key=f"del_att_{card['id']}_{idx_att}"
                                    ):
                                        if att.get("path"):
                                            delete_attachment_from_storage(att["path"])

                                        updated_att = [
                                            a for i, a in enumerate(attachments) if i != idx_att
                                        ]
                                        supabase.table("kanban_cards").update(
                                            {"attachments": updated_att}
                                        ).eq("id", card["id"]).execute()
                                        st.success("Anexo removido!")
                                        st.rerun()
                    else:
                        st.caption("Nenhum anexo.")

                    if can_edit(user_info):
                        with st.form(
                            key=f"form_att_{card['id']}", clear_on_submit=True
                        ):
                            up_file = st.file_uploader(
                                "Selecionar arquivo (máx. 10 MB)", key=f"file_{card['id']}"
                            )
                            sub_att = st.form_submit_button("📤 Salvar Anexo")

                        if sub_att:
                            if up_file is not None:
                                file_bytes = up_file.read()
                                max_size_bytes = 10 * 1024 * 1024  # 10 MB

                                if len(file_bytes) > max_size_bytes:
                                    st.error("O arquivo excede o limite máximo permitido de 10 MB.")
                                else:
                                    safe_filename = up_file.name.replace(" ", "_")
                                    file_path = f"kanban_evidences/{card['id']}_{safe_filename}"

                                    try:
                                        supabase.storage.from_("evidences").upload(
                                            path=file_path,
                                            file=file_bytes,
                                            file_options={
                                                "content-type": up_file.type,
                                                "upsert": "true",
                                            },
                                        )
                                        file_url = (
                                            supabase.storage.from_("evidences").get_public_url(
                                                file_path
                                            )
                                        )

                                        updated_att = attachments + [
                                            {
                                                "name": up_file.name,
                                                "url": file_url,
                                                "path": file_path,
                                            }
                                        ]
                                        supabase.table("kanban_cards").update(
                                            {"attachments": updated_att}
                                        ).eq("id", card["id"]).execute()

                                        st.success("Anexo salvo com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar no Storage: {e}")
                            else:
                                st.warning("Selecione um arquivo antes de enviar.")

                    st.divider()

                    # EXCLUSÃO RESTRITA DO CARD (E DE SEUS ANEXOS NO STORAGE)
                    if can_delete_items(user_info):
                        if st.button(
                            "🗑️ Excluir Card",
                            key=f"del_card_{card['id']}",
                            type="secondary",
                        ):
                            for att in attachments:
                                if isinstance(att, dict) and att.get("path"):
                                    delete_attachment_from_storage(att["path"])

                            supabase.table("kanban_cards").delete().eq(
                                "id", card["id"]
                            ).execute()
                            st.success("Card e seus anexos foram excluídos!")
                            st.rerun()
