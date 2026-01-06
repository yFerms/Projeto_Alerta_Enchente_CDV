import requests
import time
from datetime import datetime

# URL principal do serviço (WSDL)
URL_ANA = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx"

def tocar_bip():
    """Faz um barulho no sistema (Windows/Linux/Mac)"""
    print("\a") # Caractere de Bell (faz o terminal apitar)
    try:
        import winsound
        winsound.Beep(1000, 500) # Frequencia 1000Hz, 500ms
        winsound.Beep(1500, 500)
    except:
        pass

print("--- INICIANDO VIGIA DA ANA ---")
print(f"Alvo: {URL_ANA}")
print("Vou te avisar quando voltar (Status 200)...\n")

while True:
    agora = datetime.now().strftime("%H:%M:%S")
    
    try:
        # Tenta conectar com timeout curto (5s)
        response = requests.get(URL_ANA, timeout=10)
        status = response.status_code
        
        if status == 200:
            print(f"[{agora}] ✅ ONLINE! O SERVIDOR VOLTOU! (Status 200)")
            print("Pode rodar o monitor agora.")
            
            # Alerta sonoro frenético para você ouvir de longe
            for _ in range(5):
                tocar_bip()
                time.sleep(0.5)
            break # Encerra o script
            
        elif status >= 500:
            print(f"[{agora}] ❌ OFFLINE (Erro Interno do Servidor: {status})")
            
        elif status == 404:
            print(f"[{agora}] ❓ ESTRANHO (Não encontrado: {status})")
            
        else:
            print(f"[{agora}] ⚠️ Status Inesperado: {status}")

    except requests.exceptions.ConnectionError:
        print(f"[{agora}] 🔌 Falha de Conexão (Internet ou DNS)")
    except requests.exceptions.Timeout:
        print(f"[{agora}] 🐢 Timeout (Servidor muito lento)")
    except Exception as e:
        print(f"[{agora}] 💀 Erro Geral: {e}")

    # Espera 30 segundos antes de tentar de novo
    time.sleep(30)