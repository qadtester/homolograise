import streamlit as st

def render_card_modal(kanban_service, project_id, members, releases, card=None):
    title_label = "Editar Card" if card else "Novo Card"

    with st.form("kanban_card_form"):
        st.subheader(title_label)

        title = st.text_input("Título *", value=card.get("title", "") if card else "")
        description = st.text_area("Descrição", value=card.get("description", "") if card else "")

        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox(
                "Status",
                ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"],
                index=["A Fazer", "Em Progresso", "Em Revisão", "Concluído"].index(card.get("status", "A Fazer")) if card else 0,
            )
            severity = st.selectbox(
                "Severidade / Prioridade",
                ["Baixa", "Média", "Alta", "Crítica"],
                index=["Baixa", "Média", "Alta", "Crítica"].index(card.get("severity", "Baixa")) if card else 0,
            )

        with col2:
            rel_options = {r["id"]: r["name"] for r in releases}
            rel_options[None] = "Sem Release"
            selected_rel = st.selectbox(
                "Release Alvo",
                options=list(rel_options.keys()),
                format_func=lambda x: rel_options[x],
                index=list(rel_options.keys()).index(card.get("release_id")) if card and card.get("release_id") in rel_options else 0,
            )

            is_blocked = st.checkbox("Card Bloqueado?", value=card.get("is_blocked", False) if card else False)
            blocker_reason = (
                st.text_input("Motivo do Bloqueio", value=card.get("blocker_reason", "") if card else "")
                if is_blocked
                else None
            )

        submitted = st.form_submit_button("Salvar")
        if submitted:
            payload = {
                "project_id": project_id,
                "title": title,
                "description": description,
                "status": status,
                "severity": severity,
                "release_id": selected_rel,
                "is_blocked": is_blocked,
                "blocker_reason": blocker_reason,
            }
            if card:
                kanban_service.supabase.table("kanban_cards").update(payload).eq("id", card["id"]).execute()
            else:
                kanban_service.supabase.table("kanban_cards").insert(payload).execute()
            st.rerun()
