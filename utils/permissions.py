# utils/permissions.py

ROLE_PERMISSIONS = {
    "gestor": {
        "can_create": True,
        "can_edit": True,
        "can_delete_items": True,  # Casos de teste, bugs, personas, historias, matriz
        "can_delete_project": False, # NÃO deleta projeto
    },
    "editor": {
        "can_create": True,
        "can_edit": True,
        "can_delete_items": False, # NÃO deleta nada
        "can_delete_project": False,
    },
    "leitor": {
        "can_create": False,
        "can_edit": False,
        "can_delete_items": False,
        "can_delete_project": False,
    }
}

def get_user_role(user_info):
    if user_info.get("is_master") or user_info.get("is_team_owner"):
        return "owner"
    return user_info.get("role", "leitor").lower()

def can_create(user_info):
    role = get_user_role(user_info)
    if role == "owner":
        return True
    return ROLE_PERMISSIONS.get(role, {}).get("can_create", False)

def can_edit(user_info):
    role = get_user_role(user_info)
    if role == "owner":
        return True
    return ROLE_PERMISSIONS.get(role, {}).get("can_edit", False)

def can_delete_items(user_info):
    role = get_user_role(user_info)
    if role == "owner":
        return True
    return ROLE_PERMISSIONS.get(role, {}).get("can_delete_items", False)

def can_delete_project(user_info):
    role = get_user_role(user_info)
    if role == "owner":
        return True
    return ROLE_PERMISSIONS.get(role, {}).get("can_delete_project", False)
