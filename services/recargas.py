from json_db import add_transaction, load_db, save_db

def fazer_recarga(numero, operadora, valor):
    data = load_db()

    if valor <= 0:
        return False, "O valor deve ser maior que zero."

    if data["saldo"] < valor:
        return False, "Saldo insuficiente."

    data["saldo"] -= valor

    add_transaction(
        tipo="Recarga",
        descricao=f"Recarga {operadora} - {numero}",
        valor=-valor
    )

    save_db(data)
    return True, "Recarga realizada!"

