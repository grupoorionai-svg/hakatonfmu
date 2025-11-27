import re
from json_db import add_transaction

# ---------------------------------------------------------
# Categorização automática completa (versão PRO)
# ---------------------------------------------------------

def categorizar_transacao(desc):
    desc = desc.lower()

    # Luz / Energia elétrica
    if any(x in desc for x in ["energia", "eletric", "light", "cemig", "copel", "enel"]):
        return "luz"

    # Água / Saneamento
    if any(x in desc for x in ["agua", "água", "sabesp", "sanepar", "casan"]):
        return "água"

    # Educação
    if any(x in desc for x in ["escola", "colégio", "colegio", "faculdade", "fmu", "curso"]):
        return "educação"

    # Internet / Telefonia
    if any(x in desc for x in ["internet", "vivo", "claro", "tim", "oi", "fibra", "net"]):
        return "internet"

    # Saúde
    if any(x in desc for x in ["unimed", "saúde", "saude", "laboratório", "clinica", "hospital"]):
        return "saúde"

    # Lazer / Entretenimento
    if any(x in desc for x in ["cinema", "ingresso", "show", "bar", "lazer", "netflix", "spotify", "prime", "hbo"]):
        return "lazer"

    # Alimentação
    if any(x in desc for x in ["ifood", "lanche", "lanch", "restaurante", "padaria", "pizza", "hamburg"]):
        return "alimentação"

    # Supermercado
    if any(x in desc for x in ["mercado", "super", "carrefour", "extra", "dia%"]):
        return "supermercado"

    # Transporte
    if any(x in desc for x in ["uber", "99", "taxi", "estacionamento", "metro", "ônibus", "onibus"]):
        return "transporte"

    # PIX
    if "pix" in desc:
        return "pix"

    # Pagamentos / contas gerais
    if any(x in desc for x in ["boleto", "pagamento", "conta"]):
        return "pagamentos"

    # Categoria fallback
    return "outros"


# ---------------------------------------------------------
# Extrator de transações do PDF
# ---------------------------------------------------------

def extrair_transacoes_do_texto(texto):
    """
    Extrai transações do PDF detectando:
    - 01/11 Mercadinho Central R$ 45,90
    - 02/10 Uber Viagem R$ 18,00
    - Mercadinho Central R$ 45,90
    """

    texto = texto.replace("R$", "R$ ")

    padroes = [
        # data + descrição + valor
        r"(\d{1,2}/\d{1,2})\s+(.+?)\s+R\$\s*([\d.,]+)",

        # descrição + valor (sem data)
        r"(.+?)\s+R\$\s*([\d.,]+)"
    ]

    resultados = []

    for regex in padroes:
        matches = re.findall(regex, texto)

        for m in matches:
            if len(m) == 3:
                data, descricao, valor = m
            else:
                data = ""
                descricao, valor = m

            # Ajusta valor
            valor = float(valor.replace(".", "").replace(",", "."))
            valor = -abs(valor)  # sempre despesa

            resultados.append({
                "data": data,
                "descricao": descricao.strip(),
                "valor": valor
            })

    return resultados


# ---------------------------------------------------------
# Salvar transações extraídas no banco
# ---------------------------------------------------------

def salvar_transacoes_extraidas(lista_transacoes):
    for t in lista_transacoes:
        categoria = categorizar_transacao(t["descricao"])

        add_transaction(
            tipo="PDF",
            descricao=f"{t['data']} - {t['descricao']}".strip(" -"),
            valor=t["valor"],
            categoria=categoria
        )

