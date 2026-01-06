import json
import os

# Nome do arquivo que o sistema usa
ARQUIVO_HISTORICO = "historico_velocidade.json"

def criar_cenario(lista_niveis):
    """Cria um arquivo JSON falso com os níveis passados"""
    dados = []
    # Cria entradas fictícias. A data não importa para essa lógica específica, 
    # apenas a ordem dos níveis.
    for n in lista_niveis:
        dados.append({"data": "2026-01-01 10:00:00", "nivel": n})
    
    with open(ARQUIVO_HISTORICO, "w") as f:
        json.dump(dados, f)

def verificar_modo_vazante_simulado(nivel_atual):
    """Mesma lógica do seu monitor_definitivo.py"""
    if nivel_atual < 400: return False # Rio baixo não conta

    try:
        with open(ARQUIVO_HISTORICO, "r") as f:
            historico = json.load(f)
        
        # Pega os 3 últimos. Como no monitor real o atual já foi salvo antes,
        # aqui vamos simular que o histórico JÁ CONTÉM o atual.
        ultimos = historico[-3:] 
        niveis = [item['nivel'] for item in ultimos]
        
        print(f"   📊 Analisando sequência: {niveis}")
        
        if len(niveis) < 3: return False
        
        # Lógica: A > B > C (Decrescente estrito)
        if niveis[0] > niveis[1] > niveis[2]:
            return True
        return False
    except Exception as e:
        print(e)
        return False

# ==============================================================================
# BATERIA DE TESTES
# ==============================================================================
print("--- INICIANDO TESTE DE LÓGICA VAZANTE ---\n")

# CENÁRIO 1: Rio Subindo (Não deve ativar)
print("1. TESTE: Rio Subindo")
criar_cenario([600, 610, 620]) 
resultado = verificar_modo_vazante_simulado(620)
print(f"   Resultado: {'✅ MODO VAZANTE' if resultado else '🔴 MODO ALERTA'}")
print("-" * 30)

# CENÁRIO 2: Rio Baixando Perfeito (Deve ativar)
print("2. TESTE: Rio Baixando (Escadinha perfeita)")
criar_cenario([750, 740, 730]) 
resultado = verificar_modo_vazante_simulado(730)
print(f"   Resultado: {'✅ MODO VAZANTE' if resultado else '🔴 MODO ALERTA'}")
print("-" * 30)

# CENÁRIO 3: Rio Baixou mas Estabilizou (Não deve ativar)
# Isso é importante: se parou de descer, o alerta volta a ser laranja/vermelho
print("3. TESTE: Estabilizou (740 -> 730 -> 730)")
criar_cenario([740, 730, 730]) 
resultado = verificar_modo_vazante_simulado(730)
print(f"   Resultado: {'✅ MODO VAZANTE' if resultado else '🔴 MODO ALERTA'}")
print("-" * 30)

# CENÁRIO 4: Oscilação (Baixou, Subiu, Baixou) - O famoso "Serrote"
print("4. TESTE: Oscilação (740 -> 745 -> 730)")
criar_cenario([740, 745, 730]) 
resultado = verificar_modo_vazante_simulado(730)
print(f"   Resultado: {'✅ MODO VAZANTE' if resultado else '🔴 MODO ALERTA'}")
print("-" * 30)

# CENÁRIO 5: Nível Crítico (> 900) - Mesmo baixando, deve ignorar no visual
# Nota: A função retorna True aqui (a lógica detecta descida), 
# mas o seu gerar_imagem.py tem um IF extra que bloqueia a cor verde se for > 900.
print("5. TESTE: Descida em Nível Catastrófico (950 -> 940 -> 930)")
criar_cenario([950, 940, 930])
resultado = verificar_modo_vazante_simulado(930)
print(f"   Lógica detectou descida? {resultado}")
print("   (Obs: No gerar_imagem, isso será ignorado por segurança se nivel > 900)")

# Limpeza
if os.path.exists(ARQUIVO_HISTORICO): os.remove(ARQUIVO_HISTORICO)