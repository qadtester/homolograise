import streamlit as st
from kanban_service import (
    create_kanban_card,
    create_kanban_column,
    delete_kanban_column,
    swap_column_positions,
)


def render_create_card_modal(project_id: str, columns_data: list, member_options: dict, user_info: dict):
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
                        "Atribuir a", list(member_options.keys()), index=0
                    )

                submitted = st.form_submit_button("Salvar Tarefa")

                if submitted:
                    if not f_title.strip():
                        st.error("O título é obrigatório.")
                    else:
                        assigned_id = member_options[f_assignee]
                        creator_name = user_info.get("name", "Sistema")

                        create_kanban_card(
                            project_id=project_id,
                            title=f_title,
                            desc=f_desc,
                            severity=f_sev,
                            status=f_col,
                            assignee_id=assigned_id,
                            assignee_name=f_assignee,
                            creator_name=creator_name,
                        )

                        st.session_state["open_new_card_modal"] = False
                        st.success("Card criado com sucesso!")
                        st.rerun()

            if st.button("Cancelar", key="cancel_card_create"):
                st.session_state["open_new_card_modal"] = False
                st.rerun()


def render_manage_columns_modal(project_id: str, columns_data: list):
    if st.session_state.get("open_manage_cols_modal", False):
        with st.expander("🛠️ Organizar Colunas", expanded=True):
            t_add, t_ord, t_del = st.tabs(
                ["Adicionar Coluna", "Reordenar Colunas", "Excluir Coluna"]
            )

            with t_add:
                col_name_input = st.text_input("Nome da nova coluna:")
                if st.button("Salvar Nova Coluna"):
                    if col_name_input.strip():
                        create_kanban_column(project_id, col_name_input, columns_data)
                        st.rerun()

            with t_ord:
                st.write("Ajuste a ordem das colunas no quadro:")
                for i, col_item in enumerate(columns_data):
                    c_name, c_btn_up, c_btn_down = st.columns([6, 1, 1])
                    c_name.markdown(f"**{i+1}. {col_item['name']}**")

                    if i > 0 and c_btn_up.button("⬆️", key=f"up_{col_item['id']}"):
                        prev = columns_data[i - 1]
                        swap_column_positions(
                            col_item["id"], col_item["position"], prev["id"], prev["position"]
                        )
                        st.rerun()

                    if i < len(columns_data) - 1 and c_btn_down.button("⬇️", key=f"down_{col_item['id']}"):
                        nxt = columns_data[i + 1]
                        swap_column_positions(
                            col_item["id"], col_item["position"], nxt["id"], nxt["position"]
                        )
                        st.rerun()

            with t_del:
                del_target = st.selectbox(
                    "Escolha a coluna para remover:",
                    [c["name"] for c in columns_data],
                )
                if st.button("Remover Coluna", type="primary"):
                    target_obj = next(c for c in columns_data if c["name"] == del_target)
                    delete_kanban_column(target_obj["id"])
                    st.rerun()

            if st.button("Fechar Gerenciador de Colunas"):
                st.session_state["open_manage_cols_modal"] = False
                st.rerun()
