import os
import time
from android_bot import enviar_carrossel_android

def criar_imagem_teste():
    """
    Cria uma imagem simples de cor sólida para teste.
    Se tiver a biblioteca PIL (Pillow), cria um JPG vermelho.
    Se não tiver, cria um arquivo dummy (pode não abrir na galeria, mas testa o envio).
    """
    nome_arquivo = "imagem_teste_vermelha.png"
    
    try:
        from PIL import Image
        print("🎨 Criando imagem de teste (Vermelha)...")
        img = Image.new('RGB', (1080, 1920), color=(200, 50, 50))
        img.save(nome_arquivo)
    except ImportError:
        print("⚠️ Biblioteca PIL não encontrada. Criando arquivo vazio apenas para testar o fluxo.")
        with open(nome_arquivo, "wb") as f:
            f.write(b'\x00' * 1024)
            
    return os.path.abspath(nome_arquivo)

if __name__ == "__main__":
    print("="*40)
    print("      TESTE MANUAL DE POSTAGEM")
    print("="*40)
    print("Certifique-se que:")
    print("1. O celular está conectado via USB.")
    print("2. O MacroDroid está ouvindo o gatilho 'POSTAR_STORY'.")
    print("-" * 40)

    # Pergunta se quer testar a limpeza (Apagar stories) também
    resp = input("Deseja testar a LIMPEZA antes de postar? (s/n): ").strip().lower()
    testar_limpeza = (resp == 's')

    # Gera a imagem
    caminho_img = criar_imagem_teste()
    
    # Lista com 1 imagem para postar
    lista_imagens = [caminho_img]

    print(f"\n🚀 Enviando para o android_bot.py...")
    print(f"📂 Imagem: {caminho_img}")
    
    try:
        # Chama a função exata que o monitor usa
        enviar_carrossel_android(lista_imagens, deve_limpar=testar_limpeza)
        print("\n✅ Teste finalizado! Verifique o celular.")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")