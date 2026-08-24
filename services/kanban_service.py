import uuid

class KanbanService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def get_releases(self, project_id: str):
        res = (
            self.supabase.table("releases")
            .select("id, name, status, release_date")
            .eq("project_id", project_id)
            .execute()
        )
        return res.data or []

    def get_cards(self, project_id: str, release_id: str = None):
        query = (
            self.supabase.table("kanban_cards")
            .select(
                "id, title, description, status, severity, is_blocked, blocker_reason, tags, bug_id, release_id, assignee_id, attachments, created_at"
            )
            .eq("project_id", project_id)
        )

        if release_id:
            query = query.eq("release_id", release_id)

        res = query.execute()
        return res.data or []

    def update_card_status(self, card_id: str, new_status: str):
        return (
            self.supabase.table("kanban_cards")
            .update({"status": new_status})
            .eq("id", card_id)
            .execute()
        )

    def upload_attachment(self, card_id: str, uploaded_file):
        ext = uploaded_file.name.split(".")[-1]
        safe_name = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name.replace(' ', '_')}"
        path = f"cards/{card_id}/{safe_name}"

        self.supabase.storage.from_("attachments").upload(
            path, uploaded_file.getvalue(), {"upsert": "true"}
        )
        public_url = self.supabase.storage.from_("attachments").get_public_url(path)
        return public_url
