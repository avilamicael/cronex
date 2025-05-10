# core/notificacoes.py
import requests
from django.conf import settings

def enviar_mensagem_telegram(chat_id, mensagem_completa):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"

    # Dividir em linhas
    linhas = mensagem_completa.split('\n')
    header = linhas[0]  # primeira linha com título
    linhas = linhas[1:]

    blocos = []
    bloco_atual = header + '\n'
    for linha in linhas:
        if len(bloco_atual + linha + '\n') > 4000:
            blocos.append(bloco_atual)
            bloco_atual = header + '\n' + linha + '\n'
        else:
            bloco_atual += linha + '\n'

    if bloco_atual:
        blocos.append(bloco_atual)

    # Enviar todas as partes
    respostas = []
    for parte in blocos:
        data = {
            'chat_id': chat_id,
            'text': parte,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data)
        respostas.append((response.status_code, response.json()))
    return respostas
