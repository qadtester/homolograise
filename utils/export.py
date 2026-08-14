import io
import pandas as pd


def export_to_csv(data: list[dict]) -> str:
    """Converte uma lista de dicionários em uma string formato CSV."""
    if not data:
        return ""
    df = pd.DataFrame(data)
    return df.to_csv(index=False)


def export_to_markdown(data: list[dict], title: str = "Relatório") -> str:
    """Converte uma lista de dicionários em uma string formato Markdown com tabela."""
    if not data:
        return f"# {title}\n\n*Nenhum dado disponível.*"

    df = pd.DataFrame(data)

    # Formata como tabela markdown
    md_content = f"# {title}\n\n"
    md_content += df.to_markdown(index=False)
    md_content += "\n\n---\n*Gerado automaticamente pelo QA & Requisitos Hub*"

    return md_content