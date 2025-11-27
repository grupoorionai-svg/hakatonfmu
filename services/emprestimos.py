# emprestimos.py
from json_db import load_db, save_db
from datetime import datetime

def contratar_emprestimo(valor, juros=0.10):
    data = load_db()

    try:
        valor = float(valor)
    except Exception:
        return False, "Valor inválido."

    if valor <= 0:
        return False, "Valor inválido."

    total = round(valor * (1 + juros), 2)

    # Atualiza saldo (entrada)
    data["saldo"] = data.get("saldo", 0.0) + valor

    # Cria transação (entrada positiva)
    trans = {
        "tipo": "Empréstimo",
        "descricao": f"Empréstimo contratado - Total a pagar: R$ {total:.2f}",
        "valor": float(valor),         # positivo => será contado como entrada
        "categoria": "empréstimo",
        "data": datetime.utcnow().isoformat()
    }

    # Garante que lista de transações exista
    if "transacoes" not in data or not isinstance(data["transacoes"], list):
        data["transacoes"] = []

    # Adiciona transação e salva
    data["transacoes"].append(trans)
    save_db(data)

    return True, total
