from json_db import add_transaction, load_db, save_db

def pagar_boleto(codigo, valor):
    data = load_db()

    if valor <= 0:
        return False, "O valor deve ser maior que zero."

    if data["saldo"] < valor:
        return False, "Saldo insuficiente."

    data["saldo"] -= valor

    add_transaction(
        tipo="Pagamento",
        descricao=f"Boleto {codigo}",
        valor=-valor
    )

    save_db(data)
    return True, "Pagamento realizado!"

