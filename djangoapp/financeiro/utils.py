from ofxparse import OfxParser
from datetime import datetime

def processar_ofx(arquivo):
    ofx = OfxParser.parse(arquivo)
    contas = []
    for transacao in ofx.account.statement.transactions:
        contas.append({
            'data': transacao.date,
            'descricao': transacao.memo,
            'valor': transacao.amount,
        })
    return contas
