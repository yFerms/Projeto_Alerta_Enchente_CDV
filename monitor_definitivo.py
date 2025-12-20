import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import os
import csv
import json
from pathlib import Path
from dotenv import load_dotenv

# --- MÓDULOS LOCAIS ---
from gerar_imagem import gerar_todas_imagens
from dados_ruas import calcular_risco_por_rua
from android_bot import enviar_carrossel_android
from email_bot import enviar_email_alerta
# NOVO: Importando o Telegram
from telegram_bot import enviar_telegram 

load_dotenv()

# ==============================================================================
# PAINEL DE CONTROLE
# ==============================================================================
MODO_TESTE = False  # <--- MODO SIMULAÇÃO (800cm)

# Limites de Nível
LIMITE_ALERTA = 600
LIMITE_GRAVE = 760

# Limites de Velocidade
VELOCIDADE_ALERTA = 10
VELOCIDADE_PANICO = 30

# Limites Preditivos
DELTA_BARRAGEM_CRITICO = 40
DELTA_NOVA_ERA_ALERTA = 50

ARQUIVO_CONTADOR = "stories_ativos.json"

# Estações ANA
ESTACAO_TIMOTEO = "56696000"
ESTACAO_BARRAGEM = "56688080"
ESTACAO_NOVA_ERA = "56661000"

# Estado Global
ULTIMA_DATA_ANA = None
ULTIMA_POSTAGEM = None

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def registrar_log(mensagem):
    """Escreve no terminal, no arquivo de log e MANDA NO TELEGRAM"""
    timestamp = datetime.now().strftime("%H:%M") # Hora mais curta pro Telegram
    texto_completo = f"[{timestamp}] {mensagem}"
    
    # 1. Print no Terminal
    print(texto_completo)
    
    # 2. Salva no Arquivo
    with open("sistema.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n")
        
    # 3. Envia para o Telegram (Tenta enviar, se falhar, o robô continua)
    try:
        # Adiciona emoji dependendo da mensagem para ficar bonito no chat
        emoji = "ℹ️"
        if "CRÍTICA" in mensagem or "GRAVE" in mensagem or "FLASH" in mensagem: emoji = "🚨"
        elif "ALERTA" in mensagem or "SUBINDO" in mensagem: emoji = "⚠️"
        elif "POSTAGEM" in mensagem: emoji = "🚀"
        elif "Sucesso" in mensagem: emoji = "✅"
        elif "Erro" in mensagem: emoji = "❌"
        
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

def gerenciar_contador_stories():
    """
    Controla o limite de 9 stories.
    """
    if os.path.exists(ARQUIVO_CONTADOR):
        with open(ARQUIVO_CONTADOR, "r") as f:
            try: dados = json.load(f)
            except: dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    else:
        dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    
    qtd_atual = dados["qtd"]
    deve_limpar = False
    
    if qtd_atual >= 9:
        registrar_log(f"Limite stories ({qtd_atual}). Agendando Faxina.")
        deve_limpar = True
        nova_qtd = qtd_atual 
    else:
        registrar_log(f"Total stories será: {qtd_atual + 3}")
        deve_limpar = False
        nova_qtd = qtd_atual + 3
        
    dados["qtd"] = nova_qtd
    dados["ultima_limpeza"] = str(datetime.now())
    
    with open(ARQUIVO_CONTADOR, "w") as f:
        json.dump(dados, f)
        
    return deve_limpar

# ==============================================================================
# LÓGICA DO ROBÔ
# ==============================================================================
def buscar_dados_xml(codigo_estacao):
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)
    params = {"codEstacao": codigo_estacao, "dataInicio": ontem.strftime("%d/%m/%Y"), "dataFim": hoje.strftime("%d/%m/%Y")}
    try:
        response = requests.get(url, params=params, timeout=20)
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
            return leituras
        return []
    except Exception as e:
        registrar_log(f"Erro ANA: {e}")
        return []

def buscar_nivel_historico(ano_alvo):
    """
    Busca na API da ANA qual era o nível do rio na mesma data/hora, 
    mas no ano especificado.
    """
    try:
        # Define a data alvo (Hoje, mas no ano passado)
        agora = datetime.now()
        
        # Cria data de inicio e fim para a busca (janela de 2 dias no passado)
        data_historica = agora.replace(year=ano_alvo)
        inicio = data_historica - timedelta(days=1)
        fim = data_historica + timedelta(days=1)
        
        url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
        params = {
            "codEstacao": ESTACAO_TIMOTEO,
            "dataInicio": inicio.strftime("%d/%m/%Y"),
            "dataFim": fim.strftime("%d/%m/%Y"),
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            # Vamos procurar a leitura com horário mais próximo de 'agora'
            melhor_diferenca = float('inf')
            nivel_encontrado = None
            
            for dado in root.iter("DadosHidrometereologicos"):
                nivel = dado.find("Nivel")
                data_hora = dado.find("DataHora")
                
                if nivel is not None and data_hora is not None:
                    try:
                        dt_leitura = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        # Verifica a diferença de tempo (ignorando o ano)
                        # Queremos bater 14:00 com 14:00
                        dt_leitura_ajustada = dt_leitura.replace(year=agora.year, month=agora.month, day=agora.day)
                        diff = abs((agora - dt_leitura_ajustada).total_seconds())
                        
                        if diff < melhor_diferenca:
                            melhor_diferenca = diff
                            nivel_encontrado = float(nivel.text)
                    except: continue
            
            if nivel_encontrado is not None:
                return nivel_encontrado
                
        return "N/D" # Não disponível
    except:
        return "Erro"

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
        
    # ESTRATÉGIAS
    if delta_barragem >= DELTA_BARRAGEM_CRITICO: return True, 15, f"BARRAGEM CRÍTICA (+{delta_barragem}cm)"
    if vel_timoteo >= VELOCIDADE_PANICO: return True, 15, f"FLASH FLOOD (+{vel_timoteo}cm/h)"
    if nivel_timoteo >= LIMITE_GRAVE: return True, 15, "NÍVEL GRAVE"
    if delta_nova_era >= DELTA_NOVA_ERA_ALERTA: return True, 30, f"ONDA NOVA ERA (+{delta_nova_era}cm/h)"
    if nivel_timoteo >= LIMITE_ALERTA: return True, 30, "NÍVEL DE ALERTA"
    if vel_timoteo >= VELOCIDADE_ALERTA: return True, 30, f"RIO SUBINDO (+{vel_timoteo}cm/h)"
    
    agora = datetime.now()
    if (agora.hour == 7 or agora.hour == 19) and agora.minute <= 25: return True, 720, "ROTINA"
        
    return False, 720, "Estável"

# ==============================================================================
# JOB PRINCIPAL
# ==============================================================================
def job():
    global ULTIMA_DATA_ANA, ULTIMA_POSTAGEM
    registrar_log("--- Iniciando Varredura ---")
    
    # ---------------------------------------------------------
    # BLOCO SIMULAÇÃO 800cm
    # ---------------------------------------------------------
    if MODO_TESTE:
        registrar_log("SIMULAÇÃO ATIVA: Rio em 800cm")
        d_timoteo = [
            {'data': datetime.now(), 'nivel': 800.0}, 
            {'data': datetime.now() - timedelta(hours=1), 'nivel': 790.0}
        ]
        d_barragem = [{'data': datetime.now(), 'nivel': 200.0}, {'data': datetime.now(), 'nivel': 200.0}]
        d_nova_era = [{'data': datetime.now(), 'nivel': 150.0}, {'data': datetime.now(), 'nivel': 150.0}]
        ULTIMA_DATA_ANA = None 
    else:
        d_timoteo = buscar_dados_xml(ESTACAO_TIMOTEO)
        d_barragem = buscar_dados_xml(ESTACAO_BARRAGEM)
        d_nova_era = buscar_dados_xml(ESTACAO_NOVA_ERA)
    
    if not d_timoteo: return

    atual_t = d_timoteo[0]
    tendencia = analisar_tendencia(d_timoteo)
    
    if MODO_TESTE or (ULTIMA_DATA_ANA != atual_t['data']):
        salvar_csv(atual_t['data'], atual_t['nivel'], tendencia, "Timoteo")
        ULTIMA_DATA_ANA = atual_t['data']

    deve_postar, intervalo_min, motivo = definir_estrategia_postagem(d_timoteo, d_barragem, d_nova_era)
    registrar_log(f"Status: {motivo} | Nível: {atual_t['nivel']}cm")
    
    # --- NOVO BLOCO: COMPARATIVO HISTÓRICO ---
    # Só buscamos se não for modo teste (para não pesar a API à toa) ou se você quiser testar
    hist_2020 = buscar_nivel_historico(2020)
    hist_2022 = buscar_nivel_historico(2022)
    
    msg_extra = f"\n📅 *Comparativo Hoje:*\n• 2022: {hist_2022}cm\n• 2020: {hist_2020}cm"
    
    # Adicionamos ao log (agora vai pro Telegram também)
    msg_completa = f"Status: {motivo} | Nível Atual: {atual_t['nivel']}cm{msg_extra}"
    registrar_log(msg_completa)
    
    # Validação de Tempo 
    if deve_postar and not MODO_TESTE:
        if "ROTINA" in motivo:
             if ULTIMA_POSTAGEM and (datetime.now() - ULTIMA_POSTAGEM).total_seconds() < 3600: deve_postar = False
        elif ULTIMA_POSTAGEM:
            tempo_passado = (datetime.now() - ULTIMA_POSTAGEM).total_seconds() / 60
            if tempo_passado < intervalo_min:
                registrar_log(f"Aguardando intervalo ({tempo_passado:.0f}/{intervalo_min} min).")
                deve_postar = False

    if deve_postar:
        registrar_log("POSTAGEM AUTORIZADA")
        try:
            precisa_limpar = gerenciar_contador_stories()
        except: needs_cleaning = False
            
        dados_rio = {'nivel_cm': atual_t['nivel'], 'data_leitura': atual_t['data']}
        risco = calcular_risco_por_rua(atual_t['nivel'])
        ruas_fmt = [{'nome': i['apelido'], 'percentual': i['porcentagem']} for i in risco]
        caminhos = gerar_todas_imagens(dados_rio, ruas_fmt, tendencia)
        caminhos_abs = [str(Path(p).resolve()) for p in caminhos]
        
        if "ROTINA" not in motivo:
            try: enviar_email_alerta(caminhos_abs, atual_t['nivel'], f"{tendencia} - {motivo}")
            except: pass
            
        try:
            enviar_carrossel_android(caminhos_abs, deve_limpar=precisa_limpar)
            ULTIMA_POSTAGEM = datetime.now()
            registrar_log("Ciclo concluído com sucesso!")
        except Exception as e:
            registrar_log(f"Erro Android: {e}")

if __name__ == "__main__":
    registrar_log("MONITOR INICIADO")
    try:
        while True:
            job()
            print("💤 Aguardando 15 min...")
            time.sleep(15 * 60) 
    except KeyboardInterrupt:
        registrar_log("Encerrado.")