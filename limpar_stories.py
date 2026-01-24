import subprocess
import time

def apagar_ultimos_stories():
    """
    Abre o Instagram e dispara o sinal para o MacroDroid UMA VEZ.
    (A macro no celular já está configurada para apagar 2 stories sozinha)
    """
    print("🚀 Iniciando limpeza de stories...")

    # 1. Acorda o celular
    subprocess.run(["adb", "shell", "input", "keyevent", "WAKEUP"])
    
    # 2. Abre o Instagram
    print("📱 Abrindo Instagram...")
    subprocess.run(["adb", "shell", "monkey", "-p", "com.instagram.android", "-c", "android.intent.category.LAUNCHER", "1"])
    time.sleep(5) # Espera carregar

    # 3. Dispara o MacroDroid (Tiro Único)
    print("🗑️ Enviando comando APAGARSTORY para o MacroDroid...")
    subprocess.run(["adb", "shell", "am", "broadcast", "-a", "APAGARSTORY"])
    
    # Dá um tempo para a macro trabalhar antes do Python voltar a fazer coisas
    print("⏳ Aguardando a macro terminar o serviço...")
    time.sleep(15) 

    print("✅ Sinal de limpeza enviado.")

# Teste direto
if __name__ == "__main__":
    apagar_ultimos_stories()