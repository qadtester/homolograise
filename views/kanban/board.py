import streamlit as st
from services.kanban_service import KanbanService
from views.kanban.modals import render_card_modal

def render_kanban_board(supabase_client, project_id: str, members: list):
    service = KanbanService(supabase_client)
    releases = service.get_releases(project_id)

    st.header("📋 Quadro Kanban & Releases")

    # --- FILTROS E AÇÕES ---
    col_rel, col_btn = st.columns([3, 1])
    with col_rel:
        rel_filter_opts = {"ALL": "Todas as Releases"}
        rel_filter_opts.update({r["id"]: f"🚀 {r['name']} ({r['status']})" for r in releases})
        selected_rel_filter = st.selectbox(
            "Filtrar por Release:",
            options=list(rel_filter_opts.keys()),
            format_func=lambda x: rel_filter_opts[x],
        )

    with col_btn:
        st.write("")
        if st.button("➕ Novo Card", use_container_width=True):
            st.session_state["show_card_modal"] = True

    # Buscar dados
    rel_id_param = None if selected_rel_filter == "ALL" else selected_rel_filter
    cards = service.get_cards(project_id, rel_id_param)

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Cards", len(cards))
    m2.metric("Em Progresso", len([c for c in cards if c["status"] == "Em Progresso"]))
    m3.metric("Bugs Vinculados", len([c for c in cards if c.get("bug_id")]))
    m4.metric("Bloqueados", len([c for c in cards if c.get("is_blocked")]), delta_color="inverse")

    st.markdown("---")

    # Colunas padrão
    columns = ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"]
    cols = st.columns(len(columns))

    for idx, col_name in enumerate(columns):
        with cols[idx]:
            st.markdown(f"### {col_name}")
            col_cards = [c for c in cards if c["status"] == col_name]

            for card in col_cards:
                with st.container(border=True):
                    if card.get("is_blocked"):
                        st.error(f"⛔ **BLOQUEADO:** {card.get('blocker_reason', 'Sem motivo')}")

                    if card.get("bug_id"):
                        st.caption("🐞 **VINCULADO A BUG_REPORT**")

                    st.subheader(card["title"])
                    st.write(card["description"] or "*Sem descrição*")

                    sev = card.get("severity", "Baixa")
                    sev_icon = "🔴" if sev in ["Alta", "Crítica"] else ("🟡" if sev == "Média" else "🟢")
                    st.caption(f"Severidade: {sev_icon} {sev}")

                    next_status = st.selectbox(
                        "Mover para:",
                        columns,
                        index=columns.index(card["status"]) if card["status"] in columns else 0,
                        key=f"move_{card['id']}",
                    )
                    if next_status != card["status"]:
                        service.update_card_status(card["id"], next_status)
                        st.rerun()

    if st.session_state.get("show_card_modal"):
        render_card_modal(service, project_id, members, releases)
