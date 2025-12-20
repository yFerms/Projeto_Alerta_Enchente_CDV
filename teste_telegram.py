import requests

# Seus Dados
TOKEN = "8289310481:AAFnfvy6TRMLmUrmp7r-jmyZf7ysMSMdPxA"
CHAT_ID = "6975206692"

def testar():
    print("--- 📡 TESTE DE CONEXÃO TELEGRAM ---")
    print(f"Token: {TOKEN[:5]}...")
    print(f"ID: {CHAT_ID}")
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        # Tenta enviar a mensagem
        resposta = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": "🔔 Teste: Seu robô está conectado!"
        })
        
        # Mostra o resultado técnico
        print(f"\nStatus Code: {resposta.status_code}")
        print(f"Resposta do Telegram: {resposta.text}")
        
        if resposta.status_code == 200:
            print("\n✅ SUCESSO! Verifique seu celular.")
        else:
            print("\n❌ ERRO! Algo está errado com o Token ou ID.")
            
    except Exception as e:
        print(f"\n❌ ERRO DE INTERNET/CÓDIGO: {e}")

if __name__ == "__main__":
    testar()