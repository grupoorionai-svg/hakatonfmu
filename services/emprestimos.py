from json_db import add_transaction, load_db, save_db

def contratar_emprestimo(valor, juros=0.10):
    data = load_db()

    if valor <= 0:
        return False, "Valor inválido."

    total = round(valor * (1 + juros), 2)

    # Saldo aumenta
    data["saldo"] += valor

    # Registrar empréstimo
    add_transaction(
        tipo="Empréstimo",
        descricao=f"Empréstimo contratado - Total a pagar: R$ {total}",
        valor=valor
    )

    # Salvar banco
    save_db(data)

    # Retornar valor total a pagar (entrada simulada)
    return True, total

