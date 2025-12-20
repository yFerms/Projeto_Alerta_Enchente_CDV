# instagram_bot.py
from instagrapi import Client
from pathlib import Path
import os
import time

# --- CONFIGURAÇÕES ---
ARQUIVO_SESSAO = "session_insta.json"
MAX_STORIES_PERMITIDOS = 9 

def login_instagram(usuario, senha, sessionid=None, csrftoken=None):
    cl = Client()
    
    # 1. Tenta Login Cirúrgico (SessionID + CSRF)
    if sessionid and csrftoken:
        print("   🔑 Tentando login manual com Cookies...")
        try:
            # Injeta os cookies diretamente no navegador do robô
            cl.cookie_jar.set("sessionid", sessionid, domain=".instagram.com")
            cl.cookie_jar.set("csrftoken", csrftoken, domain=".instagram.com")
            
            # Força sincronização
            cl.get_timeline_feed() 
            
            print("   ✅ Login via Cookies Manual realizado com sucesso!")
            cl.dump_settings(ARQUIVO_SESSAO)
            return cl
        except Exception as e:
            print(f"   ⚠️ Falha com Cookies Manuais: {e}")
            print("   🔄 Tentando outros métodos...")

    # 2. Login Tradicional (Só use se mudar o IP!)
    print("   🔑 Tentando login com senha...")
    try:
        cl.login(usuario, senha)
        cl.dump_settings(ARQUIVO_SESSAO)
        print("   ✅ Login com senha OK!")
        return cl
    except Exception as e:
        print(f"   ❌ Erro fatal no login: {e}")
        return None

def limpar_stories_antigos(cl):
    print("   🧹 Verificando limpeza de stories antigos...")
    try:
        meu_id = cl.user_id
        stories = cl.user_stories(meu_id)
        qtd_atual = len(stories)
        
        if qtd_atual > MAX_STORIES_PERMITIDOS:
            excedente = qtd_atual - MAX_STORIES_PERMITIDOS
            print(f"   🗑️ Apagando {excedente} stories excedentes...")
            
            # Ordena por data (taken_at)
            stories_ordenados = sorted(stories, key=lambda x: x.taken_at)
            para_apagar = stories_ordenados[:excedente]
            
            for story in para_apagar:
                cl.media_delete(story.pk)
                print(f"      ❌ Story antigo apagado.")
                time.sleep(3) 
                
    except Exception as e:
        print(f"   ⚠️ Erro limpeza (ignorado): {e}")

def postar_carrossel_stories(usuario, senha, caminhos_imagens, sessionid=None, csrftoken=None):
    print("\n--- 📸 POSTAGEM INSTAGRAM ---")
    
    # Passamos todos os dados para o login
    cl = login_instagram(usuario, senha, sessionid, csrftoken)
    if not cl: return
    
    # Postagem
    for caminho in caminhos_imagens:
        try:
            print(f"   ⬆️ Uploading: {Path(caminho).name}...")
            cl.photo_upload_to_story(caminho)
            time.sleep(8) # Pausa dramática para não parecer robô
        except Exception as e:
            print(f"   ❌ Erro upload: {e}")
            if "login_required" in str(e) or "403" in str(e):
                print("   🚨 ALERTA: Seu IP ainda pode estar bloqueado ou os cookies expiraram.")
    
    print("   ✅ Fim do ciclo de postagem.")
    limpar_stories_antigos(cl)