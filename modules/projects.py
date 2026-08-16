import streamlit as st
import io
from pypdf import PdfReader
from docx import Document
from config.database import supabase
from utils.permissions import can_create, can_edit, can_delete_project

def extract_text_from_file(uploaded_file) -> str:
    """Extrai e limpa o texto de arquivos PDF, DOCX, TXT e CSV de forma segura para evitar erros no Supabase."""
    file_name_lower = uploaded_file.name.lower()
    text_content = ""

    try:
        if file_name_lower.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
                    
        elif file_name_lower.endswith((".doc", ".docx")):
            doc = Document(io.BytesIO(uploaded_file.read()))
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content += paragraph.text + "\n"
                    
        elif file_name_lower.endswith((".txt", ".csv")):
            raw_bytes = uploaded_file.read()
            text_content = raw_bytes.decode("utf-8", errors="ignore")
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo {uploaded_file.name}: {e}")
        
    # ESSENCIAL: Remove caracteres nulos (\x00 / \u0000) para evitar o erro 22P05 do PostgreSQL
    return text_content.replace("\x00", "").strip()[:50000]

def get_user_projects(team_id: str):
    res = supabase.table("projects").select("*").eq("team_id", team_id).execute()
    return res.data or []

def render_project_selector():
    user_info = st.session_state.get("user")
    if not user_info or "team_id" not in user_info:
        return None

    projects = get_user_projects(user_info["team_id"])
    if not projects:
        st.info("Nenhum projeto encontrado.")
        return None

    project_options = {p["name"]: p for p in projects}
    selected_name = st.selectbox("Selecione o Projeto:", options=list(project_options.keys()))
    
    active_project = project_options[selected_name]
    st.session_state["current_project_id"] = active_project["id"]
    return active_project

def render_projects_page():
    st.title("📁 Gestão de Projetos")
    user_info = st.session_state.get("user")
    if not user_info or "team_id" not in user_info:
        st.error("Usuário sem time vinculado.")
        return

    team_id = user_info["team_id"]
    
    # Define as abas com base nas permissões de criação
    if can_create(user_info):
        tab_list, tab_create = st.tabs(["📌 Meus Projetos", "➕ Criar Novo Projeto"])
    else:
        st.tabs(["📌 Meus Projetos"])
        tab_create = None

    # --- ABA: MEUS PROJETOS ---
    projects = get_user_projects(team_id)
    if not projects:
        st.info("Nenhum projeto cadastrado ainda.")
    else:
        for proj in projects:
            with st.expander(f"📁 {proj['name']}"):
                st.write(f"**Descrição:** {proj.get('description', 'Sem descrição')}")
                st.caption(f"ID: `{proj['id']}`")
                
                # LISTA DE DOCUMENTOS JÁ CADASTRADOS NO PROJETO
                docs = supabase.table("project_documents").select("*").eq("project_id", proj['id']).execute().data or []
                if docs:
                    st.markdown("---")
                    st.markdown("📂 **Documentos/Contextos vinculados a este projeto:**")
                    for d in docs:
                        st.caption(f"📄 **{d['file_name']}** (Enviado em: {d['created_at'][:10]})")

                # ADICIONAR DOCUMENTOS/CONTEXTO ADICIONAL (Inclusão restrita por can_create)
                if can_create(user_info):
                    with st.expander("➕ Adicionar Novo Documento ou Texto"):
                        with st.form(key=f"form_add_context_{proj['id']}"):
                            st.write("Envie novos arquivos ou cole textos adicionais para enriquecer a base da IA.")
                            new_file = st.file_uploader("Novo documento (PDF, DOC, DOCX, TXT, CSV):", type=["pdf", "doc", "docx", "txt", "csv"], key=f"file_{proj['id']}")
                            new_text = st.text_area("Ou adicione observações/regras extras em texto:", placeholder="Cole novas especificações aqui...", key=f"text_{proj['id']}")
                            
                            submitted_doc = st.form_submit_button("📥 Salvar Documento no Projeto")

                        if submitted_doc:
                            file_name = "Texto Manual"
                            file_content = ""

                            if new_file is not None:
                                file_name = new_file.name
                                file_content = extract_text_from_file(new_file)

                            if new_text.strip():
                                if file_content:
                                    file_content += f"\n\n{new_text[:20000]}"
                                else:
                                    file_content = new_text[:50000]
                                    file_name = f"Nota de Texto - {proj['name']}"

                            if file_content.strip():
                                try:
                                    supabase.table("project_documents").insert({
                                        "project_id": proj['id'],
                                        "file_name": file_name,
                                        "file_content": file_content
                                    }).execute()
                                    st.success("Documento salvo com sucesso na base do projeto!")
                                    st.rerun()
                                except Exception as db_err:
                                    st.error(f"Erro ao salvar no banco de dados: {db_err}")
                            else:
                                st.warning("Insira um texto ou envie um arquivo válido contendo texto legível.")

                st.markdown("---")
                col_edit, col_del = st.columns(2)
                
                # EDITAR PROJETO (Validação via permissions.py)
                with col_edit:
                    if can_edit(user_info):
                        with st.popover("✏️ Editar Projeto"):
                            new_name = st.text_input("Novo Nome", value=proj['name'], key=f"edit_p_name_{proj['id']}")
                            new_desc = st.text_area("Nova Descrição", value=proj.get('description', ''), key=f"edit_p_desc_{proj['id']}")
                            if st.button("Salvar Alterações", key=f"btn_save_p_{proj['id']}"):
                                supabase.table("projects").update({"name": new_name, "description": new_desc}).eq("id", proj['id']).execute()
                                st.success("Projeto atualizado com sucesso!")
                                st.rerun()
                    else:
                        st.caption("🔒 Edição restrita.")

                # EXCLUIR PROJETO (Apenas Owner/Master via permissions.py)
                with col_del:
                    if can_delete_project(user_info):
                        with st.popover("🗑️ Excluir Projeto"):
                            st.warning("⚠️ **Atenção:** Esta ação excluirá permanentemente este projeto e TODOS os dados associados!")
                            confirm_text = st.text_input("Digite 'EXCLUIR' para confirmar:", key=f"conf_del_p_{proj['id']}")
                            if st.button("Confirmar Exclusão", type="primary", key=f"btn_del_p_{proj['id']}"):
                                if confirm_text == "EXCLUIR":
                                    supabase.table("project_documents").delete().eq("project_id", proj['id']).execute()
                                    supabase.table("projects").delete().eq("id", proj['id']).execute()
                                    
                                    if st.session_state.get("current_project_id") == proj['id']:
                                        st.session_state["current_project_id"] = None
                                    st.success("Projeto e dados excluídos com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Palavra de confirmação incorreta.")
                    else:
                        st.caption("🔒 Exclusão restrita a administradores.")

    # --- ABA: CRIAR NOVO PROJETO ---
    if tab_create and can_create(user_info):
        with tab_create:
            with st.form("create_project_form", clear_on_submit=True):
                p_name = st.text_input("Nome do Projeto :red[*]")
                p_desc = st.text_area("Descrição do Projeto:")
                
                st.markdown("---")
                st.markdown("### 🤖 Documentação Inicial (Opcional)")
                uploaded_file = st.file_uploader("Carregar documento de escopo/requisitos (PDF, DOC, DOCX, TXT, CSV):", type=["pdf", "doc", "docx", "txt", "csv"])
                p_raw_text = st.text_area("Ou cole o texto bruto de requisitos/contexto:", placeholder="Cole aqui os detalhes técnicos...")

                submit_create = st.form_submit_button("🚀 Criar Projeto")

            if submit_create:
                if p_name and p_name.strip():
                    res = supabase.table("projects").insert({
                        "team_id": team_id, 
                        "name": p_name.strip(), 
                        "description": p_desc
                    }).execute()
                    
                    if res.data:
                        new_proj_id = res.data[0]['id']
                        file_name = "Documento Inicial"
                        file_content = ""

                        if uploaded_file is not None:
                            file_name = uploaded_file.name
                            file_content = extract_text_from_file(uploaded_file)

                        if p_raw_text.strip():
                            if file_content:
                                file_content += f"\n\n{p_raw_text[:20000]}"
                            else:
                                file_content = p_raw_text[:50000]
                                file_name = "Contexto Inicial"

                        if file_content.strip():
                            try:
                                supabase.table("project_documents").insert({
                                    "project_id": new_proj_id,
                                    "file_name": file_name,
                                    "file_content": file_content
                                }).execute()
                            except Exception as doc_insert_err:
                                st.warning(f"Projeto criado, mas houve falha ao anexar o documento: {doc_insert_err}")

                        st.session_state["current_project_id"] = new_proj_id
                        st.success(f"Projeto '{p_name}' criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao inserir o projeto no banco de dados.")
                else:
                    st.error("⚠️ O campo 'Nome do Projeto' é de preenchimento obrigatório.")
