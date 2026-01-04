from datetime import datetime
import dados_ruas
import gerar_imagem

# ======================================================
# CONFIGURAÇÃO DO CENÁRIO DE TESTE
# ======================================================
# Vamos simular uma cheia grave para testar paginação e cores
NIVEL_SIMULADO = 870  
TENDENCIA_SIMULADA = "SUBINDO"
VELOCIDADE_SIMULADA = "+15 cm/h"
EM_RECESSAO = False # Mude para True se quiser testar a cor Verde Água

# Dados históricos fictícios para preencher a capa
HIST_2020 = 650
HIST_2022 = 780

def rodar_teste():
    print(f"--- INICIANDO SIMULAÇÃO VISUAL ---")
    print(f"Nível do Rio: {NIVEL_SIMULADO} cm")
    
    # 1. Preparar o Dicionário de Dados do Rio
    dados_rio = {
        'nivel_cm': NIVEL_SIMULADO,
        'data_leitura': datetime.now()
    }

    # 2. Calcular o Risco das Ruas (Usa o seu arquivo dados_ruas.py)
    print("Calculando riscos por rua...")
    risco_ruas = dados_ruas.calcular_risco_por_rua(NIVEL_SIMULADO)
    
    # Mostra quantos itens tem na lista (para conferir se vai gerar 2 páginas)
    print(f"Total de setores monitorados: {len(risco_ruas)}")

    # 3. Gerar as Imagens (Usa o seu arquivo gerar_imagem.py)
    print("Gerando imagens na pasta output/...")
    caminhos = gerar_imagem.gerar_todas_imagens(
        dados_rio, 
        risco_ruas, 
        TENDENCIA_SIMULADA, 
        HIST_2020, 
        HIST_2022, 
        VELOCIDADE_SIMULADA,
        EM_RECESSAO
    )

    print("\n✅ SUCESSO! Imagens geradas:")
    for path in caminhos:
        print(f" -> {path}")

if __name__ == "__main__":
    rodar_teste()