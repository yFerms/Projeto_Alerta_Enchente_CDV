import os
import time
import subprocess

# ==============================================================================
# CONFIGURAÇÕES ADB
# ==============================================================================
def executar_adb(comando_lista):
    """Função auxiliar para rodar comandos ADB"""
    cmd_adb = "adb"
    if os.path.exists("adb.exe"):
        cmd_adb = ".\\adb.exe"
    # Adicionamos timeout para evitar travamentos eternos
    subprocess.run([cmd_adb] + comando_lista, check=False)

def acordar_celular():
    print("🔌 Acordando o celular...")
    executar_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    time.sleep(1)
    # Desliza para desbloquear (ajuste as coordenadas se necessário)
    executar_adb(["shell", "input", "swipe", "500", "2000", "500", "1000", "200"])
    time.sleep(1)
    # Garante brilho baixo para economizar bateria
    executar_adb(["shell", "settings", "put", "system", "screen_brightness", "1"])

def dormir_celular():
    print("💤 Colocando celular para dormir...")
    executar_adb(["shell", "input", "keyevent", "KEYCODE_HOME"])
    time.sleep(1)
    executar_adb(["shell", "input", "keyevent", "KEYCODE_SLEEP"])

# ==============================================================================
# FUNÇÕES DE LIMPEZA
# ==============================================================================
def limpar_stories_antigos():
    """
    MODO TURBO: Aciona a macro uma vez para apagar o lote antigo (2 stories).
    """
    print("🧹 Iniciando ROTINA DE FAXINA (Modo Janela Deslizante)...")
    
    # 1. Reinicia Instagram (Garante que o app não está travado)
    print("   🔄 Reiniciando Instagram...")
    executar_adb(["shell", "am", "force-stop", "com.instagram.android"])
    time.sleep(2)
    executar_adb(["shell", "monkey", "-p", "com.instagram.android", "-c", "android.intent.category.LAUNCHER", "1"])
    
    print("   ⏳ Aguardando Instagram carregar (8s)...")
    time.sleep(8)
    
    # 2. Dispara Macro (O MacroDroid deve estar configurado para executar a exclusão 2 VEZES)
    print("   📢 Disparando MacroDroid: APAGARSTORY")
    executar_adb(["shell", "am", "broadcast", "-a", "APAGARSTORY", "-p", "com.arlosoft.macrodroid"])
    
    # 3. Tempo para a macro trabalhar
    # Cálculo estimado: 10s para apagar o primeiro + 10s para o segundo + 10s de margem
    tempo_macro = 30 
    print(f"   ☕ Aguardando {tempo_macro}s para a faxina de 2 stories...")
    time.sleep(tempo_macro)
    
    print("✨ Limpeza concluída.")

# ==============================================================================
# FUNÇÕES DE POSTAGEM (CORRIGIDAS)
# ==============================================================================
def enviar_uma_imagem(caminho_imagem):
    nome_arquivo = "alerta_story.png"
    destino_celular = f"/sdcard/Pictures/{nome_arquivo}"
    
    print(f"📤 Preparando envio: {os.path.basename(caminho_imagem)}")

    # 1. DELETAR ARQUIVO ANTIGO (A Correção Mágica 🎩)
    # Isso obriga o Android a perceber que o próximo arquivo é "Novo" e colocá-lo no topo da galeria
    executar_adb(["shell", "rm", "-f", destino_celular])
    
    # 2. ENVIAR A NOVA IMAGEM
    executar_adb(["push", caminho_imagem, destino_celular])
    
    # 3. FORÇAR ESCANEAMENTO DE MÍDIA
    # Avisa a galeria que chegou arquivo novo
    executar_adb(["shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{destino_celular}"])
    
    # 4. REINICIAR INSTAGRAM
    # Fechar e abrir garante que o Instagram atualize a cache da galeria interna dele
    executar_adb(["shell", "am", "force-stop", "com.instagram.android"])
    time.sleep(1.5)
    executar_adb(["shell", "monkey", "-p", "com.instagram.android", "-c", "android.intent.category.LAUNCHER", "1"])
    
    # 5. AGUARDAR CARREGAMENTO (Aumentei para 10s para celulares lentos)
    print("   ⏳ Aguardando Instagram abrir (10s)...")
    time.sleep(10)
    
    # 6. DISPARAR MACRO
    print("   📢 Disparando Macro POSTAR_STORY...")
    executar_adb(["shell", "am", "broadcast", "-a", "POSTAR_STORY", "-p", "com.arlosoft.macrodroid"])

def enviar_carrossel_android(lista_caminhos, deve_limpar=False):
    print("\n📱 --- INICIANDO POSTAGEM ANDROID ---")
    acordar_celular()
    
    # FASE 1: Limpeza (Se necessário)
    if deve_limpar:
        try:
            limpar_stories_antigos() 
        except Exception as e:
            print(f"⚠️ Erro não-fatal na limpeza: {e}")

    # FASE 2: Postagem Loop
    # O tempo de postagem precisa ser suficiente para o MacroDroid fazer:
    # Clicar (+) -> Story -> Galeria -> Selecionar -> Postar -> Esperar Upload
    tempo_por_story = 35 
    
    for i, imagem in enumerate(lista_caminhos):
        print(f"\n📸 Postando {i+1}/{len(lista_caminhos)}...")
        try:
            enviar_uma_imagem(imagem)
            
            # Espera a macro terminar de clicar e o upload acontecer
            print(f"   ⏳ Dando {tempo_por_story}s para o MacroDroid trabalhar...")
            time.sleep(tempo_por_story)
            
        except Exception as e:
            print(f"❌ Erro ao postar imagem {i+1}: {e}")
            
    print("🏁 Ciclo Android finalizado.")
    dormir_celular()