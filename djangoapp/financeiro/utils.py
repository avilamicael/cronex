from ofxparse import OfxParser
from datetime import datetime

# utils.py
def processar_ofx(arquivo):
    from ofxparse import OfxParser
    ofx = OfxParser.parse(arquivo)
    contas = []

    for transacao in ofx.account.statement.transactions:
        valor = transacao.amount
        if valor < 0:
            valor = abs(valor)  # padroniza como valor positivo para conciliar

        contas.append({
            'data': transacao.date,
            'descricao': transacao.memo.strip(),
            'valor': valor,
        })
    return contas
