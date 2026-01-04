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
    timestamp = datetime.now().strftime("%H:%M") 
    texto_completo = f"[{timestamp}] {mensagem}"
    
    print(texto_completo)
    
    with open("sistema.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n")
        
    try:
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

def gerenciar_contador_stories(eh_rotina=False):
    """
    Controla o limite de stories (Máximo 6 ativos).
    - Se for ROTINA: Reseta o contador para 2 (Instagram limpa os velhos).
    - Se for CRISE: 
        - Acumula de 2 em 2.
        - Se chegar em 6, ativa flag para apagar os 2 mais antigos.
    """
    if os.path.exists(ARQUIVO_CONTADOR):
        with open(ARQUIVO_CONTADOR, "r") as f:
            try: dados = json.load(f)
            except: dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    else:
        dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    
    qtd_atual = dados["qtd"]
    deve_limpar = False
    
    # CONFIGURAÇÃO DA CONTAGEM
    LOTE_IMAGENS = 2      # Quantas imagens postamos por vez (Capa + Placar)
    LIMITE_STORIES = 6    # Máximo permitido antes de apagar (3 ciclos de 2)
    
    if eh_rotina:
        # ROTINA (07:00/19:00):
        # Não apagamos manualmente. O Instagram já expirou os de 24h atrás.
        # Apenas resetamos o contador para o lote atual.
        registrar_log("Modo ROTINA: Resetando contador (Limpeza natural do IG).")
        nova_qtd = LOTE_IMAGENS
        deve_limpar = False
    else:
        # CRISE (15 em 15 min):
        if qtd_atual >= LIMITE_STORIES:
            registrar_log(f"Limite ({qtd_atual}) atingido. Solicitando exclusão de {LOTE_IMAGENS} antigos.")
            deve_limpar = True
            
            # MATEMÁTICA DA JANELA DESLIZANTE:
            # Tínhamos 6. Apagamos 2 (LOTE). Postamos 2 (LOTE).
            # 6 - 2 + 2 = 6.
            # O contador estaciona no limite.
            nova_qtd = LIMITE_STORIES 
        else:
            nova_qtd = qtd_atual + LOTE_IMAGENS
            registrar_log(f"Contador stories acumulando: {qtd_atual} -> {nova_qtd}")
            deve_limpar = False
        
    dados["qtd"] = nova_qtd
    dados["ultima_limpeza"] = str(datetime.now())
    
    with open(ARQUIVO_CONTADOR, "w") as f:
        json.dump(dados, f)
        
    return deve_limpar

# ==============================================================================
# NOVA FUNÇÃO: MEMÓRIA HISTÓRICA
# ==============================================================================
def buscar_nivel_historico(ano_alvo):
    """Busca na ANA o nível do rio na mesma data/hora, mas no ano solicitado."""
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
        
        response = requests.get(url, params=params, timeout=5) # Timeout rápido
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
                        # Compara apenas dia/mês/hora (ignora ano)
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

ARQUIVO_HISTORICO_RECENTE = "historico_velocidade.json"

def calcular_velocidade_rio(nivel_atual, data_atual):
    """
    Calcula a velocidade de subida/descida em cm/h comparando com 1 hora atrás.
    Também gerencia o arquivo de histórico recente.
    """
    # 1. Carregar histórico existente
    historico = []
    if os.path.exists(ARQUIVO_HISTORICO_RECENTE):
        try:
            with open(ARQUIVO_HISTORICO_RECENTE, "r") as f:
                historico = json.load(f)
        except: pass

    # 2. Adicionar leitura atual
    # Convertemos data para string para salvar no JSON
    historico.append({
        "data": data_atual.strftime("%Y-%m-%d %H:%M:%S"),
        "nivel": nivel_atual
    })

    # 3. Limpar dados muito antigos (manter apenas últimas 3 horas para não pesar)
    # Convertemos de volta para datetime para comparar
    agora = data_atual
    historico_limpo = []
    leitura_referencia = None
    
    for item in historico:
        item_data = datetime.strptime(item["data"], "%Y-%m-%d %H:%M:%S")
        diferenca_horas = (agora - item_data).total_seconds() / 3600
        
        # Mantém no arquivo se for menor que 3 horas
        if diferenca_horas <= 3:
            historico_limpo.append(item)
            
        # Procura a leitura mais próxima de 1 hora atrás (entre 0.8h e 1.2h)
        if 0.8 <= diferenca_horas <= 1.5:
            leitura_referencia = item

    # 4. Salvar histórico limpo
    with open(ARQUIVO_HISTORICO_RECENTE, "w") as f:
        json.dump(historico_limpo, f)

    # 5. Calcular Velocidade
    if leitura_referencia:
        nivel_antigo = leitura_referencia["nivel"]
        delta_nivel = nivel_atual - nivel_antigo
        
        # Formatar texto
        if delta_nivel > 0:
            return f"+{delta_nivel:.0f} cm/h" # Ex: +15 cm/h
        elif delta_nivel < 0:
            return f"{delta_nivel:.0f} cm/h"  # Ex: -5 cm/h
        else:
            return "Estável"
    else:
        # Se não tiver dados de 1h atrás (primeira execução), compara com o último
        if len(historico_limpo) >= 2:
            # Pega o penúltimo
            ultimo = historico_limpo[-2] 
            delta = nivel_atual - ultimo["nivel"]
            return f"Var. Recente: {delta:+.0f} cm"
            
        return "Calculando..."

def verificar_modo_vazante(nivel_atual):
    """
    Verifica se o rio entrou em modo de vazante (Recessão).
    Critérios:
    1. Nível alto (> 400cm) - Para não ativar em oscilações normais de seca.
    2. Últimas 3 leituras caindo consistentemente.
    """
    # Só faz sentido falar em "Vazante" se o rio estiver cheio
    if nivel_atual < 400:
        return False

    try:
        with open(ARQUIVO_HISTORICO_RECENTE, "r") as f:
            historico = json.load(f)
            
        # Precisamos de pelo menos 3 leituras anteriores + a atual (que já deve estar lá ou não)
        # Vamos pegar as últimas 4 entradas do histórico
        if len(historico) < 3:
            return False
            
        ultimos = historico[-3:] # Pega os 3 últimos registros
        
        # Extrai apenas os níveis numa lista: [nivel_antigo, nivel_medio, nivel_recente]
        niveis = [item['nivel'] for item in ultimos]
        
        # Verifica se está estritamente decrescente: A > B > C
        # Ex: 700 > 690 > 680
        if niveis[0] > niveis[1] > niveis[2]:
            return True
            
        return False
    except:
        return False

def job():
    global ULTIMA_DATA_ANA, ULTIMA_POSTAGEM
    registrar_log("--- Iniciando Varredura ---")
    
    # ---------------------------------------------------------
    # BLOCO SIMULAÇÃO
    # ---------------------------------------------------------
    if MODO_TESTE:
        # Simulando Nível Grave (800cm)
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
    
    # --- NOVO: BUSCA HISTÓRICA ---
    # Busca os dados reais na ANA mesmo em modo teste
    hist_2020 = buscar_nivel_historico(2020)
    hist_2022 = buscar_nivel_historico(2022)
    
    msg_extra = f"\n📅 Comparativo Hoje:\n• 2022: {hist_2022}cm\n• 2020: {hist_2020}cm"
    registrar_log(f"Status: {motivo} | Nível: {atual_t['nivel']}cm{msg_extra}")
    
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
        
        # 1. VERIFICAÇÃO DE ROTINA (Para não limpar stories errados)
        # Se for rotina, passamos True para o contador apenas resetar, não apagar
        eh_rotina = "ROTINA" in motivo
        try:
            precisa_limpar = gerenciar_contador_stories(eh_rotina=eh_rotina)
        except: 
            precisa_limpar = False
            
        # 2. PREPARAR DADOS
        dados_rio = {'nivel_cm': atual_t['nivel'], 'data_leitura': atual_t['data']}
    
        # --- NOVO: CALCULAR VELOCIDADE ---
        velocidade_texto = calcular_velocidade_rio(atual_t['nivel'], atual_t['data'])
        registrar_log(f"Velocidade calculada: {velocidade_texto}")
        # --- NOVO: DETECTAR VAZANTE ---
        em_recessao = verificar_modo_vazante(atual_t['nivel'])
        if em_recessao:
            registrar_log("MODO VAZANTE DETECTADO! 📉")
        # ------------------------------

        risco = calcular_risco_por_rua(atual_t['nivel'])
    
        # Passamos o flag 'em_recessao' para a função de imagem
        caminhos = gerar_todas_imagens(dados_rio, risco, tendencia, hist_2020, hist_2022, velocidade_texto, em_recessao)
    
        # ATENÇÃO: Agora passamos 'velocidade_texto' para a função de imagem
        caminhos = gerar_todas_imagens(dados_rio, risco, tendencia, hist_2020, hist_2022, velocidade_texto)
        
        # Garante caminhos absolutos para o ADB
        caminhos_abs = [str(Path(p).resolve()) for p in caminhos]
        
        # 4. ENVIAR E-MAIL (Apenas se for ALERTA/CRÍTICO)
        if "ROTINA" not in motivo:
            try: enviar_email_alerta(caminhos_abs, atual_t['nivel'], f"{tendencia} - {motivo}")
            except: pass
            
        # 5. POSTAR NO INSTAGRAM (Via Android)
        try:
            enviar_carrossel_android(caminhos_abs, deve_limpar=precisa_limpar)
            ULTIMA_POSTAGEM = datetime.now()
            registrar_log("Ciclo concluído com sucesso!")
        except Exception as e:
            registrar_log(f"Erro Android: {e}")

if __name__ == "__main__":
    registrar_log("MONITOR INICIADO (COM COMPARATIVO HISTÓRICO)")
    try:
        while True:
            job()
            print("💤 Aguardando 15 min...")
            time.sleep(15 * 60) 
    except KeyboardInterrupt:
        registrar_log("Encerrado.")