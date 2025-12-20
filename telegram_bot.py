import requests
import os
from dotenv import load_dotenv

load_dotenv()

def enviar_telegram(mensagem):
    """Envia mensagens de log para o seu Telegram"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ Telegram não configurado no .env")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id, 
            "text": mensagem,
            "parse_mode": "Markdown"
        }
        # Timeout curto para não travar o robô se a internet oscilar
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")