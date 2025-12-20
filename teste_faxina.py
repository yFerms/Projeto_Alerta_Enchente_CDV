from android_bot import limpar_stories_antigos
import time
import os

# Configuração
QTD_TESTE = 4  # Vamos tentar apagar 1 story para ser rápido

print("--- 🧹 TESTE DE FAXINA (MODO DEBUG) ---")
print(f"🎯 Objetivo: Apagar os {QTD_TESTE} story(ies) mais antigo(s).")
print("📱 Estado ideal do celular: Desbloqueado e na tela inicial.")

# Confirmação visual
print("⏳ Começando em 3 segundos...")
time.sleep(3)

try:
    print("🚀 Enviando comando para o Android...")
    # Chama a função que já existe no seu projeto
    limpar_stories_antigos(QTD_TESTE)
    
    print("\n✅ Comando enviado! Olhe para o celular.")
    print("   O Instagram deve abrir, ir no Story e o MacroDroid deve agir.")
except Exception as e:
    print(f"\n❌ Erro crítico: {e}")