import streamlit as st
from config.ai_config import generate_istqb_content
from config.database import supabase
from utils.export import export_to_csv, export_to_html, export_to_markdown
from utils.permissions import can_create, can_delete_items, can_edit

# Mapeamento de prioridade para a ordenação por Severidade/Criticidade
SEVERITY_ORDER = {"Crítica": 1, "Alta": 2, "Média": 3, "Baixa": 4}


def create_kanban_card_from_bug(
    project_id: str,
    bug_id: str,
    title: str,
    description: str,
    severity: str,
):
    try:
        cols_res = (
            supabase.table("kanban_columns")
            .select("name")
            .eq("project_id", project_id)
            .order("position")
            .limit(1)
            .execute()
        )
        initial_col = (
            cols_res.data[0]["name"] if cols_res.data else "A Fazer"
        )

        card_payload = {
            "project_id": project_id,
            "bug_id": bug_id,
            "title": f"🐛 {title}",
            "description": description,
            "severity": severity,
            "status": initial_col,
            "comments": [],
            "attachments": [],
        }
        supabase.table("kanban_cards").insert(card_payload).execute()
    except Exception as e:
        st.warning(f"Bug criado, mas erro ao gerar card no Kanban: {e}")


def render_bug_reports_tab(project_id: str):
    st.subheader("🐛 Registro e Gestão de Bugs")
    user_info = st.session_state.get("user", {})

    bug_cycle_input = st.text_input(
        "🏷️ Ciclo de Teste do Bug / Release (para novos registros)",
        value="",
        placeholder="Ex: Release 1.0...",
        key="bug_active_cycle_input",
    )
    active_bug_cycle = bug_cycle_input.strip()

    if can_create(user_info):
        with st.expander("🚨 Registrar Novo Bug", expanded=False):
            bug_mode = st.radio(
                "Modo de Registro:",
                ["Sem IA (Manual)", "Com IA (Automático)"],
                horizontal=True,
                key="bug_mode_radio",
            )

            if bug_mode == "Com IA (Automático)":
                if not active_bug_cycle:
                    st.warning("⚠️ Preencha o Ciclo de Teste do Bug acima.")
                else:
                    raw_bug = st.text_area(
                        "Descreva o problema encontrado:", key="bug_ai_prompt"
                    )
                    if st.button(
                        "✨ Gerar e Salvar Bug Report via IA",
                        type="primary",
                        key="btn_gen_bug_ai",
                    ):
                        if raw_bug.strip():
                            with st.spinner("Gerando Bug Report..."):
                                data = generate_istqb_content(
                                    "bug_report",
                                    f"{project_id} | Falha: {raw_bug}",
                                )
                                if data and isinstance(data, dict):
                                    payload = {
                                        "project_id": project_id,
                                        "title": data.get(
                                            "title", "Bug Relatado por IA"
                                        ),
                                        "description": data.get(
                                            "description", raw_bug
                                        ),
                                        "severity": data.get(
                                            "severity", "Média"
                                        ),
                                        "steps": data.get(
                                            "steps_to_reproduce", ""
                                        ),
                                        "expected_behavior": data.get(
                                            "expected_behavior", ""
                                        ),
                                        "actual_behavior": data.get(
                                            "actual_behavior", ""
                                        ),
                                        "status": "Aberto",
                                        "test_cycle": active_bug_cycle,
                                    }
                                    res = (
                                        supabase.table("bug_reports")
                                        .insert(payload)
                                        .execute()
                                    )
                                    if res.data:
                                        create_kanban_card_from_bug(
                                            project_id,
                                            res.data[0]["id"],
                                            payload["title"],
                                            payload["description"],
                                            payload["severity"],
                                        )
                                    st.success(
                                        "Bug registrado e enviado ao Kanban!"
                                    )
                                    st.rerun()
            else:
                with st.form("bug_report_form", clear_on_submit=True):
                    title = st.text_input("Título do Bug *")
                    severity = st.selectbox(
                        "Severidade *", ["Baixa", "Média", "Alta", "Crítica"]
                    )
                    description = st.text_area("Descrição do Problema")
                    steps = st.text_area("Passos para Reproduzir *")
                    expected_behavior = st.text_area("Comportamento Esperado *")
                    actual_behavior = st.text_area("Comportamento Atual *")

                    if st.form_submit_button("🚨 Registrar Bug"):
                        if not active_bug_cycle:
                            st.error("Preencha o Ciclo de Teste do Bug.")
                        elif (
                            title.strip()
                            and steps.strip()
                            and expected_behavior.strip()
                            and actual_behavior.strip()
                        ):
                            payload = {
                                "project_id": project_id,
                                "title": title.strip(),
                                "description": description.strip(),
                                "severity": severity,
                                "steps": steps.strip(),
                                "expected_behavior": expected_behavior.strip(),
                                "actual_behavior": actual_behavior.strip(),
                                "status": "Aberto",
                                "test_cycle": active_bug_cycle,
                            }
                            res = (
                                supabase.table("bug_reports")
                                .insert(payload)
                                .execute()
                            )
                            if res.data:
                                create_kanban_card_from_bug(
                                    project_id,
                                    res.data[0]["id"],
                                    payload["title"],
                                    payload["description"],
                                    severity,
                                )
                            st.success("Bug registrado com sucesso!")
                            st.rerun()

    st.divider()

    col_bf1, col_bf2, col_bf3 = st.columns(3)
    with col_bf1:
        existing_bug_cycles_res = (
            supabase.table("bug_reports")
            .select("test_cycle")
            .eq("project_id", project_id)
            .execute()
        )
        bug_cycles_list = sorted(
            list(
                set(
                    [
                        row.get("test_cycle")
                        for row in (existing_bug_cycles_res.data or [])
                        if row.get("test_cycle")
                    ]
                )
            )
        )
        bug_cycle_filter = st.selectbox(
            "Filtrar por Ciclo:",
            ["Todos"] + bug_cycles_list,
            key="bug_cycle_filter_select",
        )

    with col_bf2:
        bug_status_filter = st.selectbox(
            "Filtrar por Status QA:",
            [
                "Todos",
                "Aberto",
                "Em correção",
                "Pronto para Teste",
                "Passou",
                "Fechado",
            ],
            key="bug_status_filter_select",
        )

    with col_bf3:
        bug_severity_filter = st.selectbox(
            "Filtrar por Severidade:",
            ["Todos", "Baixa", "Média", "Alta", "Crítica"],
            key="bug_severity_filter_select",
        )

    b_query = (
        supabase.table("bug_reports").select("*").eq("project_id", project_id)
    )
    if bug_cycle_filter != "Todos":
        b_query = b_query.eq("test_cycle", bug_cycle_filter)
    if bug_status_filter != "Todos":
        b_query = b_query.eq("status", bug_status_filter)
    if bug_severity_filter != "Todos":
        b_query = b_query.eq("severity", bug_severity_filter)
    bugs = b_query.execute().data or []

    if not bugs:
        st.info("Nenhum bug registrado.")
    else:
        # APLICAÇÃO DA REGRA DE ORDENAÇÃO:
        # 1. Ordem por Severidade/Criticidade: Crítica -> Alta -> Média -> Baixa
        # 2. Ordem Alfabética (A-Z) do Título dentro de cada Severidade
        bugs.sort(
            key=lambda x: (
                SEVERITY_ORDER.get(x.get("severity"), 99),
                x.get("title", "").strip().lower(),
            )
        )

        grouped_bugs = {}
        for bug in bugs:
            grouped_bugs.setdefault(
                bug.get("test_cycle") or "Sem Ciclo", []
            ).append(bug)

        for b_cycle_name, b_list in grouped_bugs.items():
            with st.expander(
                f"📦 **Ciclo / Release: {b_cycle_name}** ({len(b_list)} bugs)",
                expanded=False,
            ):
                for bug in b_list:
                    sev = bug.get("severity", "Média")
                    bug_status = bug.get("status", "Aberto")

                    # Mapeamento de cores igual ao Kanban:
                    # Crítica = 🔴 | Alta = 🟠 | Média = 🟡 | Baixa/Outros = 🟢
                    sev_color = (
                        "🔴"
                        if sev == "Crítica"
                        else (
                            "🟠"
                            if sev == "Alta"
                            else ("🟡" if sev == "Média" else "🟢")
                        )
                    )

                    with st.expander(
                        f"{sev_color} [{sev}] {bug.get('title')} - Status QA: `{bug_status}`"
                    ):
                        st.markdown(
                            f"**Descrição:**\n\n{bug.get('description') or 'N/A'}"
                        )
                        st.markdown(
                            f"**Passos:**\n\n{bug.get('steps') or 'N/A'}"
                        )
                        st.markdown(
                            f"**Comportamento Esperado:** {bug.get('expected_behavior') or 'N/A'}"
                        )
                        st.markdown(
                            f"**Comportamento Atual:** {bug.get('actual_behavior') or 'N/A'}"
                        )

                        st.divider()
                        c_status, c_edit, c_clone, c_del = st.columns(
                            [2, 1, 1, 1]
                        )

                        with c_status:
                            if can_edit(user_info):
                                status_options = [
                                    "Aberto",
                                    "Em correção",
                                    "Pronto para Teste",
                                    "Passou",
                                    "Fechado",
                                ]
                                current_idx = (
                                    status_options.index(bug_status)
                                    if bug_status in status_options
                                    else 0
                                )
                                new_b_status = st.selectbox(
                                    "Atualizar Status QA:",
                                    status_options,
                                    index=current_idx,
                                    key=f"st_bug_{bug['id']}",
                                )
                                if new_b_status != bug_status and st.button(
                                    "💾 Salvar Status",
                                    key=f"btn_save_st_{bug['id']}",
                                ):
                                    supabase.table("bug_reports").update(
                                        {"status": new_b_status}
                                    ).eq("id", bug["id"]).execute()
                                    st.success("Status QA atualizado!")
                                    st.rerun()

                        with c_edit:
                            if can_edit(user_info):
                                with st.popover(
                                    "✏️ Editar",
                                    key=f"pop_edit_bug_{bug['id']}",
                                ):
                                    e_title = st.text_input(
                                        "Título",
                                        value=bug["title"],
                                        key=f"e_b_t_{bug['id']}",
                                    )
                                    e_desc = st.text_area(
                                        "Descrição",
                                        value=bug.get("description", ""),
                                        key=f"e_b_d_{bug['id']}",
                                    )
                                    if st.button(
                                        "Salvar Edições",
                                        key=f"btn_bug_edit_{bug['id']}",
                                    ):
                                        supabase.table("bug_reports").update(
                                            {
                                                "title": e_title,
                                                "description": e_desc,
                                            }
                                        ).eq("id", bug["id"]).execute()
                                        st.rerun()

                        with c_clone:
                            if can_edit(user_info) and st.button(
                                "📋 Duplicar", key=f"btn_bug_clone_{bug['id']}"
                            ):
                                bug_clone_payload = {
                                    **bug,
                                    "title": f"{bug['title']} (Cópia)",
                                    "status": "Aberto",
                                }
                                bug_clone_payload.pop("id", None)
                                res = (
                                    supabase.table("bug_reports")
                                    .insert(bug_clone_payload)
                                    .execute()
                                )
                                if res.data:
                                    create_kanban_card_from_bug(
                                        project_id,
                                        res.data[0]["id"],
                                        bug_clone_payload["title"],
                                        bug_clone_payload.get(
                                            "description", ""
                                        ),
                                        sev,
                                    )
                                st.rerun()

                        with c_del:
                            if can_delete_items(user_info) and st.button(
                                "🗑️ Excluir",
                                key=f"btn_bug_del_{bug['id']}",
                                type="primary",
                            ):
                                supabase.table("bug_reports").delete().eq(
                                    "id", bug["id"]
                                ).execute()
                                st.rerun()
