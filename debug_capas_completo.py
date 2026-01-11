import os
from datetime import datetime
from gerar_imagem import gerar_todas_imagens

# 1. Simulação de Ruas (Gera uma lista de 20 ruas com riscos variados)
def simular_ruas(nivel_simulado):
    ruas_teste = []
    for i in range(1, 21):
        cota_rua = 300 + (i * 20) # Ruas inundam entre 320cm e 720cm
        # Cálculo de percentagem simples para o teste
        pct = max(0, min(100, (nivel_simulado / cota_rua) * 100))
        
        ruas_teste.append({
            'nome': f"Rua Teste Exemplo {i}",
            'apelido': f"Cota: {cota_rua}cm",
            'porcentagem': pct
        })
    return ruas_teste

# 2. Dados Históricos e Gráfico
historico_teste = {2020: 183, 2021: 197, 2022: 813, 2023: 404}
grafico_teste = []
for i in range(15):
    grafico_teste.append({'data': datetime.now(), 'nivel': 140 + (i * 5)})

def executar_debug_total():
    # Cenários de teste
    cenarios = [
        {"nome": "VERDE", "valor": 142.0, "status": "NÍVEL NORMAL", "vel": "+1 cm/h"},
        {"nome": "AMARELA", "valor": 480.0, "status": "ATENÇÃO", "vel": "+12 cm/h"},
        {"nome": "VERMELHA", "valor": 750.0, "status": "ALERTA CRÍTICO", "vel": "+25 cm/h"}
    ]

    print("🛠️  Iniciando Debug de Imagens (Capa + Placares)...")

    for c in cenarios:
        print(f"\n--- Testando Cenário {c['nome']} ({c['valor']}cm) ---")
        
        ruas = simular_ruas(c['valor'])
        
        # O monitor envia a previsão já calculada como string
        previsao_str = f"Prev. +1h: {int(c['valor'] + 10)} cm"

        caminhos = gerar_todas_imagens(
            dados_rio={'nivel_cm': c['valor'], 'data_leitura': datetime.now()},
            dados_ruas=ruas,
            tendencia=c['status'],
            historico_dict=historico_teste,
            velocidade=c['vel'],
            em_recessao=False,
            texto_previsao=previsao_str,
            dados_grafico=grafico_teste
        )

        # Organiza os ficheiros na pasta output para fácil conferência
        for idx, path in enumerate(caminhos):
            tipo = "CAPA" if idx == 0 else f"RUA_PG{idx}"
            novo_nome = f"output/DEBUG_{c['nome']}_{tipo}.png"
            os.replace(path, novo_nome)
            print(f"  ✅ Gerado: {novo_nome}")

    print("\n✨ Debug finalizado! Abre a pasta 'output' para validar o design.")

if __name__ == "__main__":
    executar_debug_total()