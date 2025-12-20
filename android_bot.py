import os
import time
import subprocess

def executar_adb(comando_lista):
    """Função auxiliar para rodar comandos ADB"""
    cmd_adb = "adb"
    if os.path.exists("adb.exe"):
        cmd_adb = ".\\adb.exe"
    subprocess.run([cmd_adb] + comando_lista, check=False)

def acordar_celular():
    print("🔌 Acordando o celular...")
    executar_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    time.sleep(1)
    executar_adb(["shell", "input", "swipe", "500", "2000", "500", "1000", "200"])
    time.sleep(1)
    executar_adb(["shell", "settings", "put", "system", "screen_brightness", "1"])

def dormir_celular():
    print("💤 Colocando celular para dormir...")
    executar_adb(["shell", "input", "keyevent", "KEYCODE_HOME"])
    time.sleep(1)
    executar_adb(["shell", "input", "keyevent", "KEYCODE_SLEEP"])

def limpar_stories_antigos():
    """
    NOVA LÓGICA: 'TURBO FAXINA'
    1. Abre o Instagram.
    2. Envia UM ÚNICO comando 'APAGARSTORY'.
    3. O MacroDroid se vira para apagar os 3 mais antigos de uma vez.
    """
    print("🧹 Iniciando ROTINA DE FAXINA (Modo Turbo)...")
    
    # 1. Reinicia o Instagram (Para garantir que abra no Feed)
    print("   🔄 Reiniciando Instagram...")
    executar_adb(["shell", "am", "force-stop", "com.instagram.android"])
    time.sleep(2)
    executar_adb(["shell", "monkey", "-p", "com.instagram.android", "-c", "android.intent.category.LAUNCHER", "1"])
    
    # Tempo para carregar o feed
    print("   ⏳ Aguardando Instagram carregar (5s)...")
    time.sleep(5)
    
    # 2. Dispara a Macro APAGARSTORY (Uma única vez)
    print("   📢 Disparando MacroDroid: APAGARSTORY")
    executar_adb(["shell", "am", "broadcast", "-a", "APAGARSTORY", "-p", "com.arlosoft.macrodroid"])
    
    # 3. Tempo de Espera Estendido
    # Como o MacroDroid vai apagar 3 stories em sequência, precisamos dar tempo.
    # Estimativa: (Entrar no perfil) + 3x (Mais -> Excluir -> Confirmar).
    tempo_macro = 45 
    print(f"   ☕ Aguardando {tempo_macro}s para o MacroDroid fazer a faxina completa...")
    time.sleep(tempo_macro)
        
    print("✨ Ordem de limpeza finalizada.")

def enviar_uma_imagem(caminho_imagem):
    print(f"📤 Processando: {os.path.basename(caminho_imagem)}...")
    nome_arquivo = "alerta_story.png"
    destino_celular = f"/sdcard/Pictures/{nome_arquivo}"
    
    executar_adb(["push", caminho_imagem, destino_celular])
    executar_adb(["shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{destino_celular}"])
    
    executar_adb(["shell", "am", "force-stop", "com.instagram.android"])
    time.sleep(1)
    executar_adb(["shell", "monkey", "-p", "com.instagram.android", "-c", "android.intent.category.LAUNCHER", "1"])
    
    print("   ⏳ Aguardando Instagram (8s)...")
    time.sleep(8)
    
    print("   📢 Disparando Macro POSTAR_STORY...")
    executar_adb(["shell", "am", "broadcast", "-a", "POSTAR_STORY", "-p", "com.arlosoft.macrodroid"])

def enviar_carrossel_android(lista_caminhos, deve_limpar=False):
    print("\n--- INICIANDO CICLO (POSTAGEM + LIMPEZA) ---")
    acordar_celular()
    
    # 1. LIMPEZA (Agora é chamada sem argumentos de quantidade)
    if deve_limpar:
        try:
            limpar_stories_antigos() 
        except Exception as e:
            print(f"⚠️ Erro na limpeza: {e}")

    # 2. POSTAGEM
    tempo_estimado_postagem = 25
    
    for i, imagem in enumerate(lista_caminhos):
        print(f"\n--- Postando imagem {i+1}/{len(lista_caminhos)} ---")
        try:
            enviar_uma_imagem(imagem)
            print(f"   ⏳ Esperando {tempo_estimado_postagem}s...")
            time.sleep(tempo_estimado_postagem)
        except Exception as e:
            print(f"❌ Erro: {e}")
            
    dormir_celular()