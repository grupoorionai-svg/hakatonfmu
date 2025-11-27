from json_db import add_transaction, load_db, save_db

def enviar_pix(chave, valor):
    data = load_db()

    if valor <= 0:
        return False, "O valor deve ser maior que zero."

    if data["saldo"] < valor:
        return False, "Saldo insuficiente."

    # Atualiza saldo
    data["saldo"] -= valor

    # Adiciona transação
    add_transaction(
        tipo="PIX",
        descricao=f"Enviado para {chave}",
        valor=-valor
    )

    save_db(data)
    return True, "PIX enviado com sucesso!"

