import pandas as pd


def export_to_csv(data: list[dict]) -> str:
    """Converte uma lista de dicionários em uma string formato CSV (compatível com Excel)."""
    if not data:
        return ""

    df = pd.DataFrame(data)

    # 1. sep=";" -> Impede que os dados fiquem espremidos em uma única coluna no Excel
    # 2. encoding="utf-8-sig" -> Preserva acentuação e caracteres especiais
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig")


def export_to_markdown(data: list[dict], title: str = "Relatório") -> str:
    """Converte uma lista de dicionários em uma string formato Markdown com tabela.

    Nota: requer que a biblioteca 'tabulate' esteja instalada no ambiente.
    """
    if not data:
        return f"# {title}\n\n*Nenhum dado disponível.*"

    df = pd.DataFrame(data)

    md_content = f"# {title}\n\n"
    # Requer o pacote `tabulate` no ambiente
    md_content += df.to_markdown(index=False)
    md_content += "\n\n---\n*Gerado automaticamente pelo QA & Requisitos Hub*"

    return md_content
