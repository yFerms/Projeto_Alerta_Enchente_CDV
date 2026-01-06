import time
from datetime import datetime, timedelta
from pathlib import Path
import json
import os

# Importa as funções do monitor
import monitor_definitivo as monitor
from gerar_imagem import gerar_todas_imagens
from dados_ruas import calcular_risco_por_rua
from android_bot import enviar_carrossel_android
from telegram_bot import enviar_telegram 

# NOVO: Importa o cérebro da IA
import cerebro_ia 

# ==============================================================================
# CONFIGURAÇÃO MANUAL
# ==============================================================================
FORCAR_LIMPEZA = True 

def executar_postagem_manual():
    print("--- 🚨 INICIANDO POSTAGEM MANUAL ---")
    
    # 1. BUSCAR DADOS
    print("⏳ Buscando dados na ANA...")
    
    # --- CORREÇÃO AQUI ---
    if monitor.MODO_TESTE:
        d_timoteo = [{'data': datetime.now(), 'nivel': 800.0}, {'data': datetime.now(), 'nivel': 790.0}, {'data': datetime.now(), 'nivel': 780.0}]
        d_nova_era = [{'data': datetime.now(), 'nivel': 200.0}, {'data': datetime.now(), 'nivel': 200.0}] # Dados Fakes
    else:
        d_timoteo = monitor.buscar_dados_xml(monitor.ESTACAO_TIMOTEO)
        d_nova_era = monitor.buscar_dados_xml(monitor.ESTACAO_NOVA_ERA) # <--- LINHA QUE FALTAVA
    # ---------------------
    
    if not d_timoteo:
        print("❌ Erro: Não foi possível obter dados da estação Timóteo.")
        return

    atual_t = d_timoteo[0]
    tendencia = monitor.analisar_tendencia(d_timoteo)
    
    print(f"✅ Dados obtidos: {atual_t['nivel']}cm | {tendencia}")

    # 2. BUSCAR HISTÓRICO (2020-2025)
    print("⏳ Buscando histórico comparativo...")
    historico_anos = {}
    for ano in [2020, 2021, 2022, 2023, 2024, 2025]:
        val = monitor.buscar_nivel_historico(ano)
        historico_anos[ano] = val
        print(f"   -> {ano}: {val}")

    # 3. CALCULAR DADOS COMPLEMENTARES
    velocidade_texto = monitor.calcular_velocidade_rio(atual_t['nivel'], atual_t['data'])
    em_recessao = monitor.verificar_modo_vazante(atual_t['nivel'])
    risco = calcular_risco_por_rua(atual_t['nivel'])

   # --- NOVO BLOCO IA ---
    txt_previsao_imagem = None
    try:
        # Curto Prazo
        if d_timoteo and len(d_timoteo) >= 4:
            val, _ = cerebro_ia.prever_proxima_hora(d_timoteo[:6])
            if val:
                txt_previsao_imagem = f"Prev. +1h: {val:.0f} cm"
                print(f"🔮 IA Curta: {txt_previsao_imagem}")
        
        # Médio Prazo (Apenas print no terminal para saber)
        if d_nova_era:
            val_long, expl = cerebro_ia.prever_com_nova_era(d_timoteo, d_nova_era)
            print(f"🔭 IA Nova Era: {expl} -> {val_long:.0f} cm")

    except Exception as e:
        print(f"⚠️ Erro IA: {e}")
    # ---------------------

    # 4. GERAR IMAGENS
    print("🖼️ Gerando imagens...")
    dados_rio = {'nivel_cm': atual_t['nivel'], 'data_leitura': atual_t['data']}
    
    caminhos = gerar_todas_imagens(
        dados_rio, 
        risco, 
        tendencia, 
        historico_anos,
        velocidade_texto,
        em_recessao,
        texto_previsao=txt_previsao_imagem,
        dados_grafico=d_timoteo  # <--- NOVA LINHA AQUI TAMBÉM
    )

    caminhos_abs = [str(Path(p).resolve()) for p in caminhos]
    print(f"✅ Imagens geradas: {len(caminhos)}")

    # 5. POSTAR NO INSTAGRAM
    print("🚀 Enviando para o Instagram (Android)...")
    try:
        precisa_limpar = False
        if FORCAR_LIMPEZA:
            precisa_limpar = monitor.gerenciar_contador_stories(eh_rotina=False)
            
        enviar_carrossel_android(caminhos_abs, deve_limpar=precisa_limpar)
        print("✅ Postagem no Instagram concluída!")
    except Exception as e:
        print(f"❌ Erro no Instagram: {e}")

    # 6. ENVIAR TELEGRAM
    print("📧 Enviando relatório no Telegram...")
    try:
        msg_tg = f"🚨 *POSTAGEM MANUAL REALIZADA*\n"
        msg_tg += f"Nível Atual: *{atual_t['nivel']} cm*\n"
        
        # Adiciona previsão no texto do Telegram também
        if txt_previsao_imagem:
            msg_tg += f"🔮 {txt_previsao_imagem}\n"
            
        msg_tg += f"Tendência: {tendencia} {velocidade_texto}\n"
        if em_recessao: msg_tg += "📉 *MODO VAZANTE ATIVO*\n"
        
        msg_tg += "\n📅 *HISTÓRICO:*\n"
        for ano in sorted(historico_anos.keys()):
            val = historico_anos[ano]
            msg_tg += f"• {ano}: {val} cm\n"
            
        enviar_telegram(msg_tg)
        print("✅ Telegram enviado.")
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")

    print("--- FIM DA EXECUÇÃO ---")

if __name__ == "__main__":
    executar_postagem_manual()