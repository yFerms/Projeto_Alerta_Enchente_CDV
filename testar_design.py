from datetime import datetime
import dados_ruas
import gerar_imagem

# ======================================================
# CONFIGURAÇÃO DO CENÁRIO DE TESTE
# ======================================================
# Simulação de Cheia Grave
NIVEL_SIMULADO = 820  
TENDENCIA_SIMULADA = "SUBINDO"
VELOCIDADE_SIMULADA = "+15 cm/h"
EM_RECESSAO = False 

# Dicionário Histórico Completo (2020-2025)
# Simula o que o monitor busca na ANA
HISTORICO_SIMULADO = {
    2020: 650,
    2021: 410,
    2022: 780,
    2023: 350,
    2024: 500,
    2025: 420
}

def rodar_teste():
    print(f"--- INICIANDO SIMULAÇÃO VISUAL ---")
    print(f"Nível do Rio: {NIVEL_SIMULADO} cm")
    
    # 1. Preparar o Dicionário de Dados do Rio
    dados_rio = {
        'nivel_cm': NIVEL_SIMULADO,
        'data_leitura': datetime.now()
    }

    # 2. Calcular o Risco das Ruas
    print("Calculando riscos por rua...")
    risco_ruas = dados_ruas.calcular_risco_por_rua(NIVEL_SIMULADO)
    print(f"Total de setores monitorados: {len(risco_ruas)}")

    # 3. Gerar as Imagens
    print("Gerando imagens na pasta output/...")
    
    # CHAMADA ATUALIZADA: Passando o dicionário de histórico
    caminhos = gerar_imagem.gerar_todas_imagens(
        dados_rio, 
        risco_ruas, 
        TENDENCIA_SIMULADA, 
        HISTORICO_SIMULADO,  # <--- Passamos o Dicionário aqui
        VELOCIDADE_SIMULADA,
        EM_RECESSAO
    )

    print("\n✅ SUCESSO! Imagens geradas:")
    for path in caminhos:
        print(f" -> {path}")

if __name__ == "__main__":
    rodar_teste()