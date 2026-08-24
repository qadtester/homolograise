import datetime
import streamlit as st
from config.database import supabase


def notify_user(user_id: str, title: str, message: str):
    try:
        supabase.table("notifications").insert(
            {"user_id": user_id, "title": title, "message": message}
        ).execute()
    except Exception as e:
        st.error(f"Erro ao notificar usuário: {e}")


def get_team_members(team_id: str):
    if not team_id:
        return []
    res = (
        supabase.table("team_members")
        .select("user_id, users!team_members_user_id_fkey(id, name, email)")
        .eq("team_id", team_id)
        .execute()
    )
    return [row["users"] for row in (res.data or []) if row.get("users")]


def get_kanban_columns(project_id: str):
    cols_res = (
        supabase.table("kanban_columns")
        .select("*")
        .eq("project_id", project_id)
        .order("position")
        .execute()
    )
    data = cols_res.data or []
    if not data:
        defaults = ["A Fazer", "Em Progresso", "Em Revisão", "Concluído"]
        for idx, name in enumerate(defaults):
            supabase.table("kanban_columns").insert(
                {"project_id": project_id, "name": name, "position": idx + 1}
            ).execute()
        cols_res = (
            supabase.table("kanban_columns")
            .select("*")
            .eq("project_id", project_id)
            .order("position")
            .execute()
        )
        data = cols_res.data or []
    return data


def create_kanban_column(project_id: str, col_name: str, current_cols: list):
    max_p = max([c["position"] for c in current_cols], default=0)
    supabase.table("kanban_columns").insert(
        {
            "project_id": project_id,
            "name": col_name.strip(),
            "position": max_p + 1,
        }
    ).execute()


def swap_column_positions(col_a_id: str, pos_a: int, col_b_id: str, pos_b: int):
    supabase.table("kanban_columns").update({"position": pos_b}).eq(
        "id", col_a_id
    ).execute()
    supabase.table("kanban_columns").update({"position": pos_a}).eq(
        "id", col_b_id
    ).execute()


def delete_kanban_column(col_id: str):
    supabase.table("kanban_columns").delete().eq("id", col_id).execute()


def create_kanban_card(
    project_id: str,
    title: str,
    desc: str,
    severity: str,
    status: str,
    assignee_id: str,
    assignee_name: str,
    creator_name: str,
):
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    initial_history = []
    if assignee_id:
        initial_history.append(
            {
                "assignee_name": assignee_name,
                "date": now_str,
                "assigned_by": creator_name,
            }
        )

    payload = {
        "project_id": project_id,
        "title": title.strip(),
        "description": desc.strip(),
        "severity": severity,
        "status": status,
        "assignee_id": assignee_id,
        "comments": [],
        "attachments": [],
        "assignment_history": initial_history,
    }
    supabase.table("kanban_cards").insert(payload).execute()
    if assignee_id:
        notify_user(
            assignee_id,
            "Nova Tarefa Atribuída 📋",
            f"Você foi atribuído ao card: '{title}'",
        )


def get_kanban_cards(project_id: str):
    cards_res = (
        supabase.table("kanban_cards")
        .select("*, users!kanban_cards_assignee_id_fkey(name)")
        .eq("project_id", project_id)
        .execute()
    )
    return cards_res.data or []


def update_card_status(card_id: str, new_status: str):
    supabase.table("kanban_cards").update({"status": new_status}).eq(
        "id", card_id
    ).execute()


def reassign_card(
    card: dict, new_assignee_id: str, new_assignee_name: str, user_name: str
):
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    history = card.get("assignment_history") or []
    history.append(
        {
            "assignee_name": new_assignee_name,
            "date": now_str,
            "assigned_by": user_name,
        }
    )
    supabase.table("kanban_cards").update(
        {"assignee_id": new_assignee_id, "assignment_history": history}
    ).eq("id", card["id"]).execute()
    if new_assignee_id:
        notify_user(
            new_assignee_id,
            "Reatribuição de Tarefa 📋",
            f"O card '{card['title']}' foi atribuído a você.",
        )


def update_card_details(card_id: str, title: str, description: str, severity: str):
    supabase.table("kanban_cards").update(
        {
            "title": title.strip(),
            "description": description.strip(),
            "severity": severity,
        }
    ).eq("id", card_id).execute()


def add_comment(card: dict, author_name: str, text: str):
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    comments = card.get("comments") or []
    updated_comments = comments + [
        {"author": author_name, "text": text.strip(), "date": now_str}
    ]
    supabase.table("kanban_cards").update({"comments": updated_comments}).eq(
        "id", card["id"]
    ).execute()


def delete_attachment_from_storage(file_path: str):
    try:
        supabase.storage.from_("evidences").remove([file_path])
    except Exception as e:
        st.error(f"Erro ao deletar arquivo do storage: {e}")


def remove_attachment_from_card(card: dict, attachment_index: int):
    attachments = card.get("attachments") or []
    att = attachments[attachment_index]
    if isinstance(att, dict) and att.get("path"):
        delete_attachment_from_storage(att["path"])

    updated_att = [a for i, a in enumerate(attachments) if i != attachment_index]
    supabase.table("kanban_cards").update({"attachments": updated_att}).eq(
        "id", card["id"]
    ).execute()


def upload_attachment_to_card(card: dict, up_file):
    file_bytes = up_file.read()
    max_size_bytes = 10 * 1024 * 1024  # 10 MB

    if len(file_bytes) > max_size_bytes:
        raise ValueError("O arquivo excede o limite máximo permitido de 10 MB.")

    safe_filename = up_file.name.replace(" ", "_")
    file_path = f"kanban_evidences/{card['id']}_{safe_filename}"

    supabase.storage.from_("evidences").upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": up_file.type, "upsert": "true"},
    )
    file_url = supabase.storage.from_("evidences").get_public_url(file_path)

    attachments = card.get("attachments") or []
    updated_att = attachments + [
        {"name": up_file.name, "url": file_url, "path": file_path}
    ]
    supabase.table("kanban_cards").update({"attachments": updated_att}).eq(
        "id", card["id"]
    ).execute()


def delete_card_with_attachments(card: dict):
    attachments = card.get("attachments") or []
    for att in attachments:
        if isinstance(att, dict) and att.get("path"):
            delete_attachment_from_storage(att["path"])
    supabase.table("kanban_cards").delete().eq("id", card["id"]).execute()
