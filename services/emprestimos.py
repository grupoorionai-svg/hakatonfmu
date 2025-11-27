from json_db import add_transaction, load_db, save_db

def contratar_emprestimo(valor, juros=0.10):
    data = load_db()

    if valor <= 0:
        return False, "Valor inválido."

    # Total a pagar no futuro
    total = round(valor * (1 + juros), 2)

    # Entrada do dinheiro (saldo aumenta imediatamente)
    data["saldo"] += valor

    # Registrar transação de entrada
    add_transaction(
        tipo="Empréstimo",
        descricao="Crédito recebido via contratação de empréstimo",
        valor=valor,                 # entrada positiva
        categoria="empréstimo"       # categoria nova
    )

    # Salvar banco
    save_db(data)

    # Retornar o valor total a pagar
    return True, total

