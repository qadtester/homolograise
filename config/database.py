import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from supabase import Client, create_client

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# Validação simples
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem ser configurados no arquivo .env")

# Inicialização do cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_client() -> Client:
    """Retorna a instância do cliente Supabase."""
    return supabase


def insert_data(table_name: str, data: Dict[str, Any]) -> Any:
    """Insere um novo registro na tabela especificada."""
    try:
        response = supabase.table(table_name).insert(data).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao inserir dados na tabela {table_name}: {e}")
        return None


def select_data(
    table_name: str, 
    columns: str = "*", 
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Busca registros na tabela com suporte opcional a filtros simples de igualdade."""
    try:
        query = supabase.table(table_name).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        response = query.execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar dados na tabela {table_name}: {e}")
        return []


def update_data(table_name: str, row_id: Any, data: Dict[str, Any], id_column: str = "id") -> Any:
    """Atualiza um registro existente com base na coluna de ID."""
    try:
        response = supabase.table(table_name).update(data).eq(id_column, row_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao atualizar registro na tabela {table_name}: {e}")
        return None


def delete_data(table_name: str, row_id: Any, id_column: str = "id") -> Any:
    """Remove um registro da tabela com base na coluna de ID."""
    try:
        response = supabase.table(table_name).delete().eq(id_column, row_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao deletar registro na tabela {table_name}: {e}")
        return None