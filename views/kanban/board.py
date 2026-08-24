import streamlit as st
from utils.permissions import can_delete_items, can_edit
from kanban_service import (
    add_comment,
    delete_card_with_attachments,
    get_kanban_cards,
    get_kanban_columns,
    get_team_members,
    reassign_card,
    remove_attachment_from_card,
    update_card_details,
    update_card_status,
    upload_attachment_to_card,
)
from modals import render_create_card_modal, render_manage_columns_modal


def get_severity_badge(severity: str) -> str:
    mapping = {
        "Baixa": "🟢 Baixa",
        "Média": "🟡 Média",
        "Alta": "🟠 Alta",
        "Crítica": "🔴 Crítica",
    }
    return mapping.get(severity, "⚪ " + str(severity))


def render_kanban_board(project_id: str, *args, **kwargs):
    st.title("📌 Quadro Kanban")

    user_info = st.session_state.get("user", {})
    team_id = st.session_state.get("current_team_id")

    # 1. Obter membros da equipe
    team_members = get_team_members(team_id)
    member_options = {"Não atribuído": None}
    for m in team_members:
        member_options[m["name"]] = m["id"]

    # 2. Obter colunas
    columns_data = get_kanban_columns(project_id)

    # 3. Botões Principais
    c_act1, c_act2, _ = st.columns([2, 2, 6])
    with c_act1:
        if can_edit(user_info) and st.button("➕ Novo Card", use_container_width=True, type="primary"):
            st.session_state["open_new_card_modal"] = True

    with c_act2:
        if can_edit(user_info) and st.button("⚙️ Gerenciar Colunas", use_container_width=True):
            st.session_state["open_manage_cols_modal"] = True

    # Renderizar Modais
    render_create_card_modal(project_id, columns_data, member_options, user_info)
    render_manage_columns_modal(project_id, columns_data)

    st.divider()

    # 4. Filtros e Ordenação
    st.subheader("🔍 Filtros & Ordenação")
    fl1, fl2, fl3, fl4 = st.columns([3, 3, 3, 3])

    with fl1:
        filter_search = st.text_input("🔎 Buscar por Título", placeholder="Digite uma palavra-chave...")
    with fl2:
        filter_sev = st.multiselect("🟢 Severidade / Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
    with fl3:
        filter_assignee = st.multiselect("👤 Atribuído a", list(member_options.keys()))
    with fl4:
        sort_by = st.selectbox(
            "⇅ Ordenar cards por",
            [
                "Mais recentes",
                "Mais antigos",
                "Prioridade (Crítica ➡️ Baixa)",
                "Prioridade (Baixa ➡️ Crítica)",
            ],
        )

    # 5. Obter e Filtrar Cards
    cards = get_kanban_cards(project_id)

    filtered_cards = []
    for c in cards:
        if filter_sev and c.get("severity") not in filter_sev:
            continue
        c_assignee_name = (
            c.get("users", {}).get("name") if c.get("users") else "Não atribuído"
        )
        if filter_assignee and c_assignee_name not in filter_assignee:
            continue
        if filter_search and filter_search.lower() not in c.get("title", "").lower():
            continue
        filtered_cards.append(c)

    sev_weights = {"Crítica": 4, "Alta": 3, "Média": 2, "Baixa": 1}
    if sort_by == "Mais recentes":
        filtered_cards.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort_by == "Mais antigos":
        filtered_cards.sort(key=lambda x: x.get("created_at", ""))
    elif sort_by == "Prioridade (Crítica ➡️ Baixa)":
        filtered_cards.sort(
            key=lambda x: sev_weights.get(x.get("severity", "Baixa"), 0), reverse=True
        )
    elif sort_by == "Prioridade (Baixa ➡️ Crítica)":
        filtered_cards.sort(
            key=lambda x: sev_weights.get(x.get("severity", "Baixa"), 0)
        )

    st.divider()

    # 6. Renderização das Colunas e Cards
    ui_cols = st.columns(len(columns_data)) if columns_data else []

    for idx, col_info in enumerate(columns_data):
        col_name = col_info["name"]
        col_cards = [card for card in filtered_cards if card.get("status") == col_name]

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
                    st.caption(f"**Atribuído a:** {assigned_name}")
                    st.write(card.get("description") or "*Sem descrição*")
                    st.divider()

                    tab_actions, tab_history, tab_edit, tab_comments = st.tabs(
                        ["⚡ Mover/Atribuir", "📜 Histórico", "✏️ Editar", "💬 Comentários"]
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
                                update_card_status(card["id"], new_col)
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
                                index=list(member_options.keys()).index(cur_assignee_key),
                                key=f"assign_{card['id']}",
                            )

                            if member_options[new_assignee_key] != card.get("assignee_id"):
                                new_uid = member_options[new_assignee_key]
                                user_name = user_info.get("name", "Usuário")
                                reassign_card(card, new_uid, new_assignee_key, user_name)
                                st.rerun()

                    with tab_history:
                        history = card.get("assignment_history") or []
                        if history:
                            st.markdown("**📜 Histórico de Responsáveis:**")
                            for h in reversed(history):
                                st.write(f"• **{h.get('assignee_name')}** em `{h.get('date')}`")
                                st.caption(f"Atribuído por: {h.get('assigned_by', 'Desconhecido')}")
                        else:
                            st.caption("Nenhum histórico de atribuição.")

                    with tab_edit:
                        if can_edit(user_info):
                            with st.form(key=f"form_edit_card_{card['id']}"):
                                e_title = st.text_input("Título", value=card.get("title", ""))
                                e_desc = st.text_area("Descrição", value=card.get("description", ""))
                                e_sev = st.selectbox(
                                    "Severidade",
                                    ["Baixa", "Média", "Alta", "Crítica"],
                                    index=["Baixa", "Média", "Alta", "Crítica"].index(
                                        card.get("severity", "Baixa")
                                    ),
                                )

                                if st.form_submit_button("Salvar Edição"):
                                    update_card_details(card["id"], e_title, e_desc, e_sev)
                                    st.success("Card atualizado!")
                                    st.rerun()

                    with tab_comments:
                        comments = card.get("comments") or []
                        if comments:
                            for com in comments:
                                st.markdown(f"**{com.get('author', 'Usuário')}**: {com.get('text')}")
                                st.caption(f"_{com.get('date', '')}_")
                                st.divider()
                        else:
                            st.caption("Nenhum comentário.")

                        new_comment_text = st.text_area(
                            "Adicionar comentário:", key=f"comm_input_{card['id']}"
                        )
                        if st.button("Enviar Comentário", key=f"btn_comm_{card['id']}"):
                            if new_comment_text.strip():
                                author_name = user_info.get("name", "Usuário")
                                add_comment(card, author_name, new_comment_text)
                                st.success("Comentário salvo!")
                                st.rerun()

                    st.divider()

                    # Gestão de Anexos
                    st.markdown("**📎 Anexos:**")
                    st.caption("Limite máximo: 10 MB por arquivo")

                    attachments = card.get("attachments") or []
                    if attachments:
                        for idx_att, att in enumerate(attachments):
                            if isinstance(att, dict) and att.get("url"):
                                col_att1, col_att2 = st.columns([5, 1])
                                with col_att1:
                                    st.markdown(f"📄 [{att.get('name', 'Arquivo')}]({att.get('url')})")
                                with col_att2:
                                    if can_edit(user_info) and st.button("❌", key=f"del_att_{card['id']}_{idx_att}"):
                                        remove_attachment_from_card(card, idx_att)
                                        st.success("Anexo removido!")
                                        st.rerun()
                    else:
                        st.caption("Nenhum anexo.")

                    if can_edit(user_info):
                        with st.form(key=f"form_att_{card['id']}", clear_on_submit=True):
                            up_file = st.file_uploader(
                                "Selecionar arquivo (máx. 10 MB)", key=f"file_{card['id']}"
                            )
                            sub_att = st.form_submit_button("📤 Salvar Anexo")

                        if sub_att:
                            if up_file is not None:
                                try:
                                    upload_attachment_to_card(card, up_file)
                                    st.success("Anexo salvo com sucesso!")
                                    st.rerun()
                                except ValueError as ve:
                                    st.error(str(ve))
                                except Exception as e:
                                    st.error(f"Erro ao salvar no Storage: {e}")
                            else:
                                st.warning("Selecione um arquivo antes de enviar.")

                    st.divider()

                    # Exclusão Restrita do Card
                    if can_delete_items(user_info):
                        if st.button("🗑️ Excluir Card", key=f"del_card_{card['id']}", type="secondary"):
                            delete_card_with_attachments(card)
                            st.success("Card e seus anexos foram excluídos!")
                            st.rerun()
