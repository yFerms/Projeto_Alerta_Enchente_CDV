import time
from android_bot import limpar_stories_antigos, acordar_celular

print("="*40)
print("      TESTE DE FAXINA TURBO (3 EM 1)")
print("="*40)
print("Configuração Esperada:")
print("1. O Python abre o Instagram.")
print("2. O Python manda UM comando 'APAGARSTORY'.")
print("3. O MacroDroid deve apagar 3 stories sozinho.")
print("-" * 40)

input("Pressione ENTER para começar...")

try:
    acordar_celular()
    # Chama a função nova (sem argumentos de quantidade)
    limpar_stories_antigos()
    print("\n✅ Teste finalizado! Verifique se 3 stories sumiram.")
except Exception as e:
    print(f"\n❌ Erro: {e}")
