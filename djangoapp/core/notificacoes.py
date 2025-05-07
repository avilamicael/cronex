import requests
from django.conf import settings

def enviar_mensagem_telegram(chat_id, mensagem):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': mensagem,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data)
    return response.status_code, response.json()
