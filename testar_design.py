from datetime import datetime, timedelta
import dados_ruas
import gerar_imagem
import random

# ======================================================
# CONFIGURAÇÃO DO CENÁRIO DE TESTE
# ======================================================
# Simulação de Cheia Grave
NIVEL_ATUAL = 820  
TENDENCIA_SIMULADA = "SUBINDO"
VELOCIDADE_SIMULADA = "+15 cm/h"
EM_RECESSAO = False 

# Simulação da IA
TEXTO_PREVISAO_SIMULADO = "Prev. +1h: 835 cm"

# Dicionário Histórico Completo (2020-2025)
HISTORICO_SIMULADO = {
    2020: 650,
    2021: 410,
    2022: 926, # Aquele pico máximo histórico
    2023: 350,
    2024: 500,
    2025: 420
}

def gerar_dados_grafico_fake(nivel_final):
    """
    Gera uma lista de leituras falsas das últimas 24h
    para testar o desenho do gráfico.
    """
    lista = []
    agora = datetime.now()
    
    # Começa 24h atrás com um nível mais baixo e vai subindo
    nivel_inicial = nivel_final - 150 # Começou 1.5m mais baixo
    
    for i in range(24):
        # Simula uma subida progressiva com um pouco de "tremec-tremec" (random)
        tempo = agora - timedelta(hours=(23-i))
        progresso = i / 23 # 0 a 1
        
        nivel = nivel_inicial + (progresso * 150) + random.uniform(-2, 2)
        
        lista.append({
            'data': tempo,
            'nivel': nivel
        })
        
    # Garante que o último dado bate com o atual
    lista.append({'data': agora, 'nivel': nivel_final})
    return lista

def rodar_teste():
    print(f"--- INICIANDO SIMULAÇÃO VISUAL COMPLETA ---")
    print(f"Nível Atual: {NIVEL_ATUAL} cm")
    
    # 1. Preparar o Dicionário de Dados do Rio
    dados_rio = {
        'nivel_cm': NIVEL_ATUAL,
        'data_leitura': datetime.now()
    }

    # 2. Gerar Dados para o Gráfico (Simulação de 24h)
    print("Gerando curva de gráfico simulada...")
    dados_para_grafico = gerar_dados_grafico_fake(NIVEL_ATUAL)

    # 3. Calcular o Risco das Ruas
    print("Calculando riscos por rua...")
    risco_ruas = dados_ruas.calcular_risco_por_rua(NIVEL_ATUAL)
    
    # 4. Gerar as Imagens
    print("Gerando imagens na pasta output/...")
    
    # CHAMADA ATUALIZADA COM TODOS OS PARÂMETROS NOVOS
    caminhos = gerar_imagem.gerar_todas_imagens(
        dados_rio, 
        risco_ruas, 
        TENDENCIA_SIMULADA, 
        HISTORICO_SIMULADO, 
        VELOCIDADE_SIMULADA,
        EM_RECESSAO,
        texto_previsao=TEXTO_PREVISAO_SIMULADO, # <--- Testa o texto amarelo
        dados_grafico=dados_para_grafico        # <--- Testa o gráfico
    )

    print("\n✅ SUCESSO! Imagens geradas:")
    for path in caminhos:
        print(f" -> {path}")

if __name__ == "__main__":
    rodar_teste()