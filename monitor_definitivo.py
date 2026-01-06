import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import os
import csv
import json
from pathlib import Path
from dotenv import load_dotenv
import random
import cerebro_ia
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- MÓDULOS LOCAIS ---
from gerar_imagem import gerar_todas_imagens
from dados_ruas import calcular_risco_por_rua
from android_bot import enviar_carrossel_android
from email_bot import enviar_email_alerta
from telegram_bot import enviar_telegram 

load_dotenv()

# ==============================================================================
# PAINEL DE CONTROLE
# ==============================================================================
MODO_TESTE = False

LIMITE_ALERTA = 600
LIMITE_GRAVE = 760

VELOCIDADE_ALERTA = 10
VELOCIDADE_PANICO = 30

DELTA_BARRAGEM_CRITICO = 40
DELTA_NOVA_ERA_ALERTA = 50

ARQUIVO_CONTADOR = "stories_ativos.json"
ARQUIVO_HISTORICO_RECENTE = "historico_velocidade.json"

ESTACAO_TIMOTEO = "56696000"
ESTACAO_BARRAGEM = "56688080"
ESTACAO_NOVA_ERA = "56661000"

ULTIMA_DATA_ANA = None
ULTIMA_POSTAGEM = None

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def registrar_log(mensagem, enviar_tg=True):
    """Escreve no terminal, no arquivo de log e MANDA NO TELEGRAM (Mensagens Curtas)"""
    timestamp = datetime.now().strftime("%H:%M") 
    texto_completo = f"[{timestamp}] {mensagem}"
    print(texto_completo)
    
    with open("sistema.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n")
    
    if enviar_tg:
        try:
            emoji = "ℹ️"
            if "CRÍTICA" in mensagem or "GRAVE" in mensagem or "FLASH" in mensagem: emoji = "🚨"
            elif "ALERTA" in mensagem or "SUBINDO" in mensagem: emoji = "⚠️"
            elif "POSTAGEM" in mensagem: emoji = "🚀"
            elif "Sucesso" in mensagem: emoji = "✅"
            elif "Erro" in mensagem: emoji = "❌"
            elif "VAZANTE" in mensagem: emoji = "📉"
            # Nota: O Telegram detalhado é enviado separado, aqui são só logs de sistema
            enviar_telegram(f"{emoji} {mensagem}")
        except:
            pass

def salvar_csv(data_hora, nivel, tendencia, estacao):
    arquivo = "historico_rio.csv"
    existe = os.path.exists(arquivo)
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe: writer.writerow(["DataHora", "Estacao", "Nivel", "Tendencia"])
        writer.writerow([data_hora, estacao, nivel, tendencia])

def gerenciar_contador_stories(eh_rotina=False):
    if os.path.exists(ARQUIVO_CONTADOR):
        with open(ARQUIVO_CONTADOR, "r") as f:
            try: dados = json.load(f)
            except: dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    else:
        dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    
    qtd_atual = dados["qtd"]
    deve_limpar = False
    
    LOTE_IMAGENS = 2
    LIMITE_STORIES = 6
    
    if eh_rotina:
        registrar_log("Modo ROTINA: Resetando contador.", enviar_tg=False)
        nova_qtd = LOTE_IMAGENS
        deve_limpar = False
    else:
        if qtd_atual >= LIMITE_STORIES:
            registrar_log(f"Limite ({qtd_atual}) atingido. Solicitando exclusão.", enviar_tg=False)
            deve_limpar = True
            nova_qtd = LIMITE_STORIES
        else:
            nova_qtd = qtd_atual + LOTE_IMAGENS
            registrar_log(f"Contador stories: {qtd_atual} -> {nova_qtd}", enviar_tg=False)
            deve_limpar = False
        
    dados["qtd"] = nova_qtd
    dados["ultima_limpeza"] = str(datetime.now())
    
    with open(ARQUIVO_CONTADOR, "w") as f:
        json.dump(dados, f)
        
    return deve_limpar

# ==============================================================================
# MEMÓRIA HISTÓRICA
# ==============================================================================
def buscar_nivel_historico(ano_alvo):
    try:
        agora = datetime.now()
        data_historica = agora.replace(year=ano_alvo)
        inicio = data_historica - timedelta(days=1)
        fim = data_historica + timedelta(days=1)
        
        url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
        params = {
            "codEstacao": ESTACAO_TIMOTEO,
            "dataInicio": inicio.strftime("%d/%m/%Y"),
            "dataFim": fim.strftime("%d/%m/%Y"),
        }
        
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            melhor_diferenca = float('inf')
            nivel_encontrado = None
            
            for dado in root.iter("DadosHidrometereologicos"):
                nivel = dado.find("Nivel")
                data_hora = dado.find("DataHora")
                
                if nivel is not None and data_hora is not None:
                    try:
                        dt_leitura = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        dt_ajustada = dt_leitura.replace(year=agora.year, month=agora.month, day=agora.day)
                        diff = abs((agora - dt_ajustada).total_seconds())
                        
                        if diff < melhor_diferenca:
                            melhor_diferenca = diff
                            nivel_encontrado = float(nivel.text)
                    except: continue
            
            if nivel_encontrado is not None:
                return nivel_encontrado
                
        return "N/D"
    except:
        return "Erro"

# ==============================================================================
# LÓGICA DO ROBÔ
# ==============================================================================
def buscar_dados_xml(codigo_estacao):
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)
    params = {"codEstacao": codigo_estacao, "dataInicio": ontem.strftime("%d/%m/%Y"), "dataFim": hoje.strftime("%d/%m/%Y")}
    
    # --- CONFIGURAÇÃO DE PERSISTÊNCIA (RETRY) ---
    # Tenta 3 vezes total.
    # backoff_factor=2 significa: espera 2s, depois 4s, depois 8s...
    # status_forcelist: Tenta de novo se der erro 500, 502, 503, 504 (Erros de servidor)
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    # --------------------------------------------

    try:
        # Aumentei o timeout para 30s por segurança
        response = session.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            leituras = []
            for dado in root.iter("DadosHidrometereologicos"):
                nivel = dado.find("Nivel")
                data_hora = dado.find("DataHora")
                if nivel is not None and data_hora is not None:
                    try:
                        dt = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        leituras.append({"data": dt, "nivel": float(nivel.text)})
                    except: continue
            leituras.sort(key=lambda x: x['data'], reverse=True)
            
            if not leituras:
                registrar_log(f"⚠️ Aviso: Estação {codigo_estacao} conectou, mas XML veio sem dados.", enviar_tg=False)
            
            return leituras
        else:
            registrar_log(f"❌ Erro HTTP {response.status_code} na estação {codigo_estacao}", enviar_tg=False)
            return []
    except Exception as e:
        registrar_log(f"❌ Falha Definitiva ANA: {e}", enviar_tg=False)
        return []

def analisar_velocidade(leituras, janela_horas=1):
    if len(leituras) < 2: return 0
    agora = leituras[0]
    for l in leituras:
        diff = (agora['data'] - l['data']).total_seconds() / 3600
        if (janela_horas * 0.8) <= diff <= (janela_horas * 1.2):
            return agora['nivel'] - l['nivel']
    return 0

def analisar_tendencia(leituras):
    if len(leituras) < 2: return "Estável"
    diff = leituras[0]['nivel'] - leituras[1]['nivel']
    if diff > 0: return f"SUBINDO (+{diff:.0f}cm)"
    elif diff < 0: return f"BAIXANDO ({diff:.0f}cm)"
    return "ESTÁVEL"

def definir_estrategia_postagem(dados_timoteo, dados_barragem, dados_nova_era):
    if not dados_timoteo: return False, 720, "Erro Timóteo"
    
    nivel_timoteo = dados_timoteo[0]['nivel']
    vel_timoteo = analisar_velocidade(dados_timoteo, 1)
    
    delta_barragem = 0
    if dados_barragem and len(dados_barragem) >= 2:
        delta_barragem = dados_barragem[0]['nivel'] - dados_barragem[1]['nivel']
        
    delta_nova_era = 0
    if dados_nova_era: delta_nova_era = analisar_velocidade(dados_nova_era, 1)
        
    if delta_barragem >= DELTA_BARRAGEM_CRITICO: return True, 15, f"BARRAGEM CRÍTICA (+{delta_barragem}cm)"
    if vel_timoteo >= VELOCIDADE_PANICO: return True, 15, f"FLASH FLOOD (+{vel_timoteo}cm/h)"
    if nivel_timoteo >= LIMITE_GRAVE: return True, 15, "NÍVEL GRAVE"
    if delta_nova_era >= DELTA_NOVA_ERA_ALERTA: return True, 30, f"ONDA NOVA ERA (+{delta_nova_era}cm/h)"
    if nivel_timoteo >= LIMITE_ALERTA: return True, 30, "NÍVEL DE ALERTA"
    if vel_timoteo >= VELOCIDADE_ALERTA: return True, 30, f"RIO SUBINDO (+{vel_timoteo}cm/h)"
    
    agora = datetime.now()
    if (agora.hour == 7 or agora.hour == 19) and agora.minute <= 25: return True, 720, "ROTINA"
    return False, 720, "Estável"

def calcular_velocidade_rio(nivel_atual, data_atual):
    historico = []
    if os.path.exists(ARQUIVO_HISTORICO_RECENTE):
        try:
            with open(ARQUIVO_HISTORICO_RECENTE, "r") as f: historico = json.load(f)
        except: pass

    historico.append({"data": data_atual.strftime("%Y-%m-%d %H:%M:%S"), "nivel": nivel_atual})
    agora = data_atual
    historico_limpo = []
    leitura_referencia = None
    
    for item in historico:
        item_data = datetime.strptime(item["data"], "%Y-%m-%d %H:%M:%S")
        diferenca_horas = (agora - item_data).total_seconds() / 3600
        if diferenca_horas <= 3:
            historico_limpo.append(item)
        if 0.8 <= diferenca_horas <= 1.5:
            leitura_referencia = item

    with open(ARQUIVO_HISTORICO_RECENTE, "w") as f:
        json.dump(historico_limpo, f)

    if leitura_referencia:
        nivel_antigo = leitura_referencia["nivel"]
        delta_nivel = nivel_atual - nivel_antigo
        if delta_nivel > 0: return f"+{delta_nivel:.0f} cm/h"
        elif delta_nivel < 0: return f"{delta_nivel:.0f} cm/h"
        else: return "Estável"
    else:
        if len(historico_limpo) >= 2:
            ultimo = historico_limpo[-2] 
            delta = nivel_atual - ultimo["nivel"]
            return f"Var. Recente: {delta:+.0f} cm"
        return "Calculando..."

def verificar_modo_vazante(nivel_atual):
    if nivel_atual < 400: return False
    try:
        with open(ARQUIVO_HISTORICO_RECENTE, "r") as f: historico = json.load(f)
        if len(historico) < 3: return False
        ultimos = historico[-3:] 
        niveis = [item['nivel'] for item in ultimos]
        if niveis[0] > niveis[1] > niveis[2]: return True
        return False
    except: return False

# ==============================================================================
# JOB PRINCIPAL
# ==============================================================================

def job():
    global ULTIMA_DATA_ANA, ULTIMA_POSTAGEM
    registrar_log("--- Iniciando Varredura ---", enviar_tg=False)
    
    # 1. INICIALIZAÇÃO SEGURA DE VARIÁVEIS (Para evitar erros de "not defined")
    nivel_futuro = None          # Variável unificada para a previsão
    previsao_ia_texto = None     # Texto curto para a imagem
    msg_ia_longa = ""            # Texto longo para o Telegram
    
    if MODO_TESTE:
        d_timoteo = [{'data': datetime.now(), 'nivel': 800.0}, {'data': datetime.now() - timedelta(hours=1), 'nivel': 790.0}, {'data': datetime.now() - timedelta(hours=2), 'nivel': 780.0}, {'data': datetime.now() - timedelta(hours=3), 'nivel': 770.0}]
        d_barragem = [{'data': datetime.now(), 'nivel': 200.0}, {'data': datetime.now(), 'nivel': 200.0}]
        d_nova_era = [{'data': datetime.now(), 'nivel': 150.0}, {'data': datetime.now(), 'nivel': 150.0}]
        ULTIMA_DATA_ANA = None 
    else:
        d_timoteo = buscar_dados_xml(ESTACAO_TIMOTEO)
        d_barragem = buscar_dados_xml(ESTACAO_BARRAGEM)
        d_nova_era = buscar_dados_xml(ESTACAO_NOVA_ERA)
    
    if not d_timoteo: 
        registrar_log("❌ Varredura cancelada: Sem dados de Timóteo.")
        return

    atual_t = d_timoteo[0]
    tendencia = analisar_tendencia(d_timoteo)
    
    if MODO_TESTE or (ULTIMA_DATA_ANA != atual_t['data']):
        salvar_csv(atual_t['data'], atual_t['nivel'], tendencia, "Timoteo")
        ULTIMA_DATA_ANA = atual_t['data']

    deve_postar, intervalo_min, motivo = definir_estrategia_postagem(d_timoteo, d_barragem, d_nova_era)
    
    # -------------------------------------------------------------
    # 2. BUSCA HISTÓRICA & PREPARAÇÃO DE DADOS
    # -------------------------------------------------------------
    registrar_log("⏳ Buscando histórico (2020-2025)...", enviar_tg=False)
    historico_anos = {}
    log_txt = "📅 Histórico: "
    for ano in [2020, 2021, 2022, 2023, 2024, 2025]:
        val = buscar_nivel_historico(ano)
        historico_anos[ano] = val
        log_txt += f"[{ano}: {val}] "
    registrar_log(log_txt, enviar_tg=False)
    
    velocidade_texto = calcular_velocidade_rio(atual_t['nivel'], atual_t['data'])
    em_recessao = verificar_modo_vazante(atual_t['nivel'])
    risco = calcular_risco_por_rua(atual_t['nivel'])
    
    if em_recessao: registrar_log("MODO VAZANTE DETECTADO! 📉", enviar_tg=False)

    # -------------------------------------------------------------
    # 3. CÉREBRO IA (CALCULA PREVISÕES)
    # -------------------------------------------------------------
    # IA Curto Prazo (Timóteo)
    try:
        if d_timoteo and len(d_timoteo) >= 4:
            prev_curta, vel_ia = cerebro_ia.prever_proxima_hora(d_timoteo[:6])
            if prev_curta:
                registrar_log(f"🧠 IA Curta (Inércia): Vai para {prev_curta:.0f}cm em 1h", enviar_tg=False)
                nivel_futuro = prev_curta # Atualiza a variável segura
                previsao_ia_texto = f"Prev. +1h: {prev_curta:.0f} cm"
                msg_ia_longa += f"🔮 Previsão Imediata (+1h): *{prev_curta:.0f} cm* ({vel_ia})\n"
    except Exception as e:
        registrar_log(f"Erro IA Curta: {e}", enviar_tg=False)

    # IA Médio Prazo (Nova Era)
    try:
        if d_nova_era and len(d_nova_era) >= 2:
            prev_longa, explicacao = cerebro_ia.prever_com_nova_era(d_timoteo, d_nova_era)
            
            if prev_longa:
                 diferenca = prev_longa - atual_t['nivel']
                 if abs(diferenca) > 10:
                     registrar_log(f"🔭 IA Longa (Nova Era): {explicacao} -> {prev_longa:.0f}cm", enviar_tg=False)
                     msg_ia_longa += f"🌊 Onda de Cheia (Nova Era): Esperado *{prev_longa:.0f} cm* em ~5h\n"
                 else:
                     # ADICIONE ISTO AQUI PARA VER NO TERMINAL
                     registrar_log(f"🔭 IA Longa: {explicacao} (Sem impacto grave)", enviar_tg=False)
            else:
                 # ADICIONE ISTO PARA VER SE FOI FILTRADO POR SER PEQUENO
                 registrar_log(f"🔭 IA Longa: {explicacao}", enviar_tg=False)

    except Exception as e:
        registrar_log(f"Erro IA Longa: {e}", enviar_tg=False)

    # -------------------------------------------------------------
    # 4. ENVIA RELATÓRIO TELEGRAM (SEMPRE)
    # -------------------------------------------------------------
    try:
        msg_tg = f"🚨 *MONITORAMENTO DO RIO* (Ciclo 15min)\n"
        msg_tg += f"Nível Atual: *{atual_t['nivel']} cm*\n"
        
        if msg_ia_longa:
            msg_tg += f"\n{msg_ia_longa}\n"
            
        msg_tg += f"Tendência: {tendencia} {velocidade_texto}\n"
        msg_tg += f"Status: {motivo}\n"
        if em_recessao: msg_tg += "📉 *MODO VAZANTE ATIVO*\n"
        
        msg_tg += "\n📅 *HISTÓRICO (Mesma data):*\n"
        for ano in sorted(historico_anos.keys()):
            val = historico_anos[ano]
            msg_tg += f"• {ano}: {val} cm\n"
        
        msg_tg += "\n⚠️ *SITUAÇÃO DAS RUAS:*\n"
        ruas_afetadas = [r for r in risco if r['porcentagem'] > 0]
        if not ruas_afetadas: ruas_afetadas = risco[:3] 

        for rua in ruas_afetadas:
            status_emoji = "🟢"
            if rua['porcentagem'] > 50: status_emoji = "🟡"
            if rua['porcentagem'] > 80: status_emoji = "🟠"
            if rua['porcentagem'] >= 100: status_emoji = "🔴"
            msg_tg += f"{status_emoji} {rua['nome']} ({rua['apelido']}): {rua['porcentagem']:.0f}%\n"

        enviar_telegram(msg_tg)
        registrar_log("✅ Relatório enviado ao Telegram.", enviar_tg=False)
    except Exception as e:
        registrar_log(f"Erro ao enviar Telegram detalhado: {e}")

    # -------------------------------------------------------------
    # 5. VERIFICA POSTAGEM INSTAGRAM/EMAIL
    # -------------------------------------------------------------
    if deve_postar and not MODO_TESTE:
        if "ROTINA" in motivo:
             if ULTIMA_POSTAGEM and (datetime.now() - ULTIMA_POSTAGEM).total_seconds() < 3600: deve_postar = False
        elif ULTIMA_POSTAGEM:
            tempo_passado = (datetime.now() - ULTIMA_POSTAGEM).total_seconds() / 60
            if tempo_passado < intervalo_min:
                registrar_log(f"Aguardando intervalo IG ({tempo_passado:.0f}/{intervalo_min} min).", enviar_tg=False)
                deve_postar = False

    if deve_postar:
        registrar_log("🚀 POSTAGEM INSTAGRAM AUTORIZADA")
        eh_rotina = "ROTINA" in motivo
        try:
            precisa_limpar = gerenciar_contador_stories(eh_rotina=eh_rotina)
        except: 
            precisa_limpar = False
            
        dados_rio = {'nivel_cm': atual_t['nivel'], 'data_leitura': atual_t['data']}
    
        # Prepara o texto curto para a Imagem
        txt_previsao_imagem = None
        if nivel_futuro: 
            txt_previsao_imagem = f"Prev. +1h: {nivel_futuro:.0f} cm"

        # GERA IMAGENS
        try:
            caminhos = gerar_todas_imagens(
                dados_rio, 
                risco, 
                tendencia, 
                historico_anos,
                velocidade_texto,
                em_recessao,
                texto_previsao=txt_previsao_imagem,
                dados_grafico=d_timoteo # <--- NOVA LINHA: Passa a lista bruta para o gráfico
            )
            caminhos_abs = [str(Path(p).resolve()) for p in caminhos]
        except Exception as e:
            registrar_log(f"Erro ao gerar imagens: {e}")
            return

        # ENVIA EMAIL (DENTRO DO IF)
        if "ROTINA" not in motivo:
            try: enviar_email_alerta(caminhos_abs, atual_t['nivel'], f"{tendencia} - {motivo}")
            except: pass
        
        # ENVIA INSTAGRAM (DENTRO DO IF)
        try:
            enviar_carrossel_android(caminhos_abs, deve_limpar=precisa_limpar)
            ULTIMA_POSTAGEM = datetime.now()
            registrar_log("Ciclo Instagram concluído com sucesso!")
        except Exception as e:
            registrar_log(f"Erro Android: {e}")

if __name__ == "__main__":
    registrar_log("MONITOR INICIADO (TG 100% | IG FILTRADO)")
    try:
        while True:
            job()
            print("💤 Aguardando 15 min...")
            time.sleep(15 * 60) 
    except KeyboardInterrupt:
        registrar_log("Encerrado.")