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
import monitor_clima
import sqlite3

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

# Configurações Guilman (Valores obtidos do histórico)
ESTACAO_GUILMAN = "56675080"
ALERTA_VAZAO_AMARELO = 879   # Início de Atenção
ALERTA_VAZAO_VERMELHO = 1406  # Risco Real de Enchente

ULTIMA_DATA_ANA = None
ULTIMA_POSTAGEM = None


# Função para garantir o caminho correto do banco
def conectar_banco():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_db = os.path.join(diretorio_atual, "rio_doce.db")
    return sqlite3.connect(caminho_db)

def salvar_leitura_no_banco(data_hora, nivel):
    """Guarda a leitura atual no banco local para consultas futuras"""
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        # Converte a data para string no formato do SQLite
        dt_str = data_hora.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO historico (data_hora, nivel) VALUES (?, ?)", (dt_str, nivel))
        conn.commit()
        conn.close()
    except Exception as e:
        # Relança o erro para o try-except do loop capturar
        raise e

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def verificar_trava_instagram():
    """Retorna True se o sistema estiver LIBERADO, False se estiver TRAVADO manual."""
    arquivo = "trava_instagram.json"
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r") as f:
                dados = json.load(f)
                return dados.get("ativo", True)
        except:
            return True # Na dúvida, deixa ligado
    return True

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



def gerenciar_contador_stories(eh_rotina=True):
    arquivo_json = "stories_ativos.json"
    
    # --- CONFIGURAÇÃO DA JANELA DESLIZANTE ---
    limite_maximo = 6      # O teto do Instagram
    lote_postagem = 2      # Quantos stories postamos por vez (sempre de 2 em 2)
    qtd_a_apagar = 2       # Quantos a macro apaga de uma vez
    # -----------------------------------------
    
    # 1. Carrega Estado Atual
    dados = {"quantidade": 0}
    if os.path.exists(arquivo_json):
        try:
            with open(arquivo_json, "r") as f:
                dados = json.load(f)
        except Exception as e:
            registrar_log(f"Erro JSON (resetando): {e}", enviar_tg=False)

    qtd_atual = dados.get("quantidade", 0)
    precisa_limpar = False

    # 2. Verifica se vai estourar o limite
    # Ex: Tenho 6. Se somar 2, vai pra 8. 8 > 6? Sim. Então limpa.
    if (qtd_atual + lote_postagem) > limite_maximo:
        registrar_log(f"🧹 Manutenção de Stories: {qtd_atual} ativos. Apagando antigos para manter janela de {limite_maximo}...", enviar_tg=False)
        precisa_limpar = True
        
        # AQUI ESTÁ A CORREÇÃO:
        # Não zeramos. Subtraímos o que a macro vai apagar.
        # Ex: 6 - 2 = 4.
        qtd_atual = qtd_atual - qtd_a_apagar
        
        # Segurança: Se a conta der negativo (erro de sincronia), assume 0
        if qtd_atual < 0: qtd_atual = 0
    
    # 3. Soma os novos que vão entrar agora
    # Ex: Estava com 4 (após apagar), entram 2 => Vai para 6.
    qtd_nova = qtd_atual + lote_postagem
    
    # 4. Salva o futuro estado
    dados_atualizados = {
        "quantidade": qtd_nova,
        "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        with open(arquivo_json, "w") as f:
            json.dump(dados_atualizados, f, indent=4)
        print(f"💾 JSON Janela Deslizante: {qtd_atual + qtd_a_apagar if precisa_limpar else qtd_atual} - {qtd_a_apagar if precisa_limpar else 0} + {lote_postagem} = {qtd_nova} Stories.")
    except Exception as e:
        registrar_log(f"Erro ao salvar JSON stories: {e}")

    return precisa_limpar

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
    
def buscar_vazao_historica(ano_alvo, codigo_estacao):
    """Busca na ANA a VAZÃO na mesma data/hora, mas no ano solicitado."""
    try:
        agora = datetime.now()
        # Define a data no passado (mesmo dia/mês, ano diferente)
        data_historica = agora.replace(year=ano_alvo)
        inicio = data_historica - timedelta(days=1)
        fim = data_historica + timedelta(days=1)
        
        url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
        params = {
            "codEstacao": codigo_estacao,
            "dataInicio": inicio.strftime("%d/%m/%Y"),
            "dataFim": fim.strftime("%d/%m/%Y"),
        }
        
        # Timeout curto para não travar o robô se a ANA estiver lenta
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            melhor_diferenca = float('inf')
            vazao_encontrada = None
            
            for dado in root.iter("DadosHidrometereologicos"):
                vazao = dado.find("Vazao") # <--- Foco na Vazão
                data_hora = dado.find("DataHora")
                
                if vazao is not None and data_hora is not None and vazao.text:
                    try:
                        dt_leitura = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        
                        # Truque para comparar apenas dia/mês/hora ignorando o ano
                        dt_ajustada = dt_leitura.replace(year=agora.year, month=agora.month, day=agora.day)
                        diff = abs((agora - dt_ajustada).total_seconds())
                        
                        # Pega a leitura mais próxima do horário atual (ex: 18:00)
                        if diff < melhor_diferenca:
                            melhor_diferenca = diff
                            vazao_encontrada = float(vazao.text)
                    except: continue
            
            if vazao_encontrada is not None:
                return f"{vazao_encontrada:.0f}" # Retorna sem casas decimais (ex: 1200)
                
        return "N/D"
    except Exception as e:
        print(f"Erro histórico vazão ({ano_alvo}): {e}")
        return "Erro"

# ==============================================================================
# LÓGICA DO ROBÔ
# ==============================================================================
def buscar_dados_xml(codigo_estacao):
    # url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos" # Link antigo HTTP
    url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos" # Link novo HTTPS (Recomendado)
    
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)
    
    params = {
        "codEstacao": codigo_estacao,
        "dataInicio": ontem.strftime("%d/%m/%Y"),
        "dataFim": hoje.strftime("%d/%m/%Y")
    }

    try:
        # Adicionei timeout=30 para evitar travamentos
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            leituras = []
            
            for dado in root.iter("DadosHidrometereologicos"):
                nivel = dado.find("Nivel")
                vazao = dado.find("Vazao")  # <--- O SEGREDO ESTÁ AQUI
                data_hora = dado.find("DataHora")
                
                if data_hora is not None:
                    try:
                        dt = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        
                        # Garante que, se vier vazio, usa 0.0
                        val_nivel = float(nivel.text) if (nivel is not None and nivel.text) else 0.0
                        val_vazao = float(vazao.text) if (vazao is not None and vazao.text) else 0.0
                        
                        leituras.append({
                            "data": dt,
                            "nivel": val_nivel,
                            "vazao": val_vazao # Agora o dicionário tem a chave 'vazao'!
                        })
                    except ValueError:
                        continue
            
            leituras.sort(key=lambda x: x['data'], reverse=True)
            return leituras
            
    except Exception as e:
        registrar_log(f"Erro ao buscar estação {codigo_estacao}: {e}")
        return []
    
    return []

def salvar_historico_guilman(leitura):
    """Salva o histórico da Guilman em um CSV separado"""
    arquivo = "historico_guilman_coletado.csv"
    arquivo_existe = os.path.exists(arquivo)
    
    if not leitura: return

    try:
        with open(arquivo, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not arquivo_existe:
                writer.writerow(["Data", "Vazao_m3s", "Nivel_cm"])
            
            writer.writerow([
                leitura['data'].strftime("%Y-%m-%d %H:%M:%S"),
                leitura.get('vazao', 0.0), # <--- Usa .get() para evitar erro se a chave sumir
                leitura['nivel']
            ])
    except Exception as e:
        registrar_log(f"Erro ao salvar Guilman: {e}")

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
    """
    Define se devemos postar no Instagram e qual o intervalo de segurança.
    Regra de Ouro: Só dispara ALERTAS se o nível atual for MAIOR que o anterior.
    Caso contrário, trata como ROTINA (só posta a cada 4h).
    """
    if not dados_timoteo:
        return False, 60, "Sem dados"

    atual = dados_timoteo[0]
    nivel_atual = atual['nivel']
    dt_atual = atual['data']
    
    # 1. Recupera o Nível Anterior para comparação
    nivel_anterior = nivel_atual 
    if len(dados_timoteo) > 1:
        nivel_anterior = dados_timoteo[1]['nivel']

    # Calcula velocidade (agora pedindo o valor numérico corretamente)
    velocidade = calcular_velocidade_rio(nivel_atual, dt_atual, retornar_valor_numerico=True)

    # --- [A TRAVA DE SEGURANÇA] ---
    # Só consideramos "Alerta" se o rio realmente subiu nesta leitura.
    # Se for igual (estável) ou menor (baixando), ignoramos a velocidade calculada.
    realmente_subiu = (nivel_atual > nivel_anterior)

    # 2. CENÁRIO DE EMERGÊNCIA (> Cota de Alerta)
    if nivel_atual >= LIMITE_ALERTA:
        if realmente_subiu:
            return True, 20, f"🚨 EMERGÊNCIA (Subindo: {nivel_atual}cm)"
        # Se estiver na emergência mas parou de subir, cai para a Rotina (aguarda intervalo maior)

    # 3. CENÁRIO DE SUBIDA RÁPIDA (> 10 cm/h)
    if velocidade >= VELOCIDADE_ALERTA: 
        if realmente_subiu:
            intervalo = 30 
            if velocidade >= VELOCIDADE_PANICO: intervalo = 15
            return True, intervalo, f"🚀 SUBIDA RÁPIDA (+{velocidade:.1f} cm/h)"
        # Se a velocidade média é alta, mas agora travou, cai para a Rotina

    # 4. CENÁRIO DE SUBIDA GRADUAL (> 2 cm/h)
    if velocidade > 2:
        if realmente_subiu:
            return True, 60, "📈 Subida Gradual"
        # Se parou de subir, cai para a Rotina

    # 5. CENÁRIO DE ROTINA (O "Padrão")
    # Retorna True, mas o 'job' principal só vai postar se tiver passado 4 horas (240 min) da última postagem.
    return True, 240, "ROTINA (Estável/Baixando)"

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
# FUNÇÕES DE CÁLCULO E ESTRATÉGIA (Cole ACIMA do job)
# ==============================================================================

def calcular_velocidade_rio(nivel, data_hora, retornar_valor_numerico=False):
    """
    Calcula a velocidade de subida/descida baseada na última leitura salva.
    Usa um arquivo JSON auxiliar para persistir o último dado mesmo se reiniciar.
    """
    arquivo_memoria = "historico_velocidade.json"
    
    # Tenta carregar a leitura anterior
    leitura_anterior = None
    if os.path.exists(arquivo_memoria):
        try:
            with open(arquivo_memoria, "r") as f:
                leitura_anterior = json.load(f)
        except:
            pass

    # Salva a leitura ATUAL para a próxima vez
    # Convertemos data para string para salvar no JSON
    novo_estado = {
        "nivel": nivel,
        "data": data_hora.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(arquivo_memoria, "w") as f:
            json.dump(novo_estado, f)
    except Exception as e:
        registrar_log(f"Erro ao salvar memória velocidade: {e}", enviar_tg=False)

    # Se não tem histórico anterior, não dá para calcular velocidade
    if not leitura_anterior:
        if retornar_valor_numerico: return 0.0
        return "(Calculando...)"

    # CÁLCULO DA VELOCIDADE
    try:
        nivel_ant = float(leitura_anterior['nivel'])
        data_ant = datetime.strptime(leitura_anterior['data'], "%Y-%m-%d %H:%M:%S")
        
        # Diferença de Tempo em Horas
        diff_horas = (data_hora - data_ant).total_seconds() / 3600
        
        # Evita divisão por zero ou tempo muito curto (< 10 min)
        if diff_horas < 0.16: 
            if retornar_valor_numerico: return 0.0
            return "(Aguarda...)"

        delta_h = nivel - nivel_ant
        velocidade = delta_h / diff_horas # cm/h
        
        # --- [CORREÇÃO] O CÓDIGO QUE FALTAVA ---
        if retornar_valor_numerico:
            return velocidade
        # ---------------------------------------

        # Formatação do Texto (Comportamento antigo)
        seta = "⬆️" if velocidade > 0 else "⬇️"
        if abs(velocidade) < 1: seta = "➡️"
        
        return f"({seta} {abs(velocidade):.1f} cm/h)"

    except Exception as e:
        registrar_log(f"Erro cálculo velocidade: {e}", enviar_tg=False)
        if retornar_valor_numerico: return 0.0
        return "(Erro Calc)"

def definir_estrategia_postagem(dados_timoteo, dados_barragem, dados_nova_era):
    """
    Define se devemos postar no Instagram e qual o intervalo de segurança.
    Retorna: (deve_postar: bool, intervalo_minutos: int, motivo: str)
    """
    if not dados_timoteo:
        return False, 60, "Sem dados"

    atual = dados_timoteo[0]
    nivel_atual = atual['nivel']
    dt_atual = atual['data']
    
    # Pega o nível anterior para verificar estagnação
    nivel_anterior = nivel_atual 
    if len(dados_timoteo) > 1:
        nivel_anterior = dados_timoteo[1]['nivel']

    # Chama a função acima pedindo o NÚMERO (agora vai funcionar!)
    velocidade = calcular_velocidade_rio(nivel_atual, dt_atual, retornar_valor_numerico=True)

    # 1. CENÁRIO DE EMERGÊNCIA (> 600cm)
    if nivel_atual >= LIMITE_ALERTA:
        if velocidade > 0:
            return True, 20, f"EMERGÊNCIA (Nível {nivel_atual})"
        else:
            return True, 60, "Nível Alto (Estável/Descendo)"

    # 2. CENÁRIO DE SUBIDA RÁPIDA (> 10 cm/h)
    if velocidade >= VELOCIDADE_ALERTA: 
        # Trava: Só posta se o nível realmente subiu em relação à última leitura
        if nivel_atual <= nivel_anterior:
             return False, 30, f"Subida Rápida ({velocidade:.1f}cm/h), mas nível estagnou agora."

        intervalo = 30 
        if velocidade >= VELOCIDADE_PANICO: # > 30 cm/h
            intervalo = 15
            
        return True, intervalo, f"SUBIDA RÁPIDA (+{velocidade:.1f} cm/h)"

    # 3. CENÁRIO DE SUBIDA LENTA (> 2 cm/h)
    if velocidade > 2:
        return True, 60, "Subida Gradual"

    # 4. CENÁRIO DE ROTINA
    return True, 240, "ROTINA (Estável/Baixando)"

# ==============================================================================
# JOB PRINCIPAL
# ==============================================================================

def job():
    global ULTIMA_DATA_ANA, ULTIMA_POSTAGEM
    registrar_log("--- Iniciando Varredura ---", enviar_tg=False)
    
    # 1. INICIALIZAÇÃO SEGURA DE VARIÁVEIS
    nivel_futuro = None         
    previsao_ia_texto = None    
    msg_ia_longa = ""            
    
    # --- [MODIFICAÇÃO 1] Inicializa variáveis da Guilman ---
    msg_guilman_tg = "" 
    status_guilman = "Normal"

    if MODO_TESTE:
        # (Seus dados de teste...)
        d_timoteo = [{'data': datetime.now(), 'nivel': 800.0}, {'data': datetime.now() - timedelta(hours=1), 'nivel': 790.0}, {'data': datetime.now() - timedelta(hours=2), 'nivel': 780.0}, {'data': datetime.now() - timedelta(hours=3), 'nivel': 770.0}]
        d_barragem = [{'data': datetime.now(), 'nivel': 200.0}, {'data': datetime.now(), 'nivel': 200.0}]
        d_nova_era = [{'data': datetime.now(), 'nivel': 150.0}, {'data': datetime.now(), 'nivel': 150.0}]
        d_guilman = [{'data': datetime.now(), 'nivel': 0, 'vazao': 1300}] # Mock para teste
        ULTIMA_DATA_ANA = None 
    else:
        d_timoteo = buscar_dados_xml(ESTACAO_TIMOTEO)
        d_barragem = buscar_dados_xml(ESTACAO_BARRAGEM)
        d_nova_era = buscar_dados_xml(ESTACAO_NOVA_ERA)
        # --- [MODIFICAÇÃO 2] Busca Guilman ---
        d_guilman = buscar_dados_xml(ESTACAO_GUILMAN)
    
    if not d_timoteo: 
        registrar_log("❌ Varredura cancelada: Sem dados de Timóteo.")
        return

    atual_t = d_timoteo[0]
    tendencia = analisar_tendencia(d_timoteo)

    if atual_t:
        try:
            salvar_leitura_no_banco(atual_t['data'], atual_t['nivel'])
            print(f"✅ Leitura de {atual_t['nivel']}cm salva no banco local.")
        except Exception as e:
            registrar_log(f"⚠️ Erro ao salvar no banco (o robô continuará): {e}")
    
    # --- [MODIFICAÇÃO 3] Processa e Salva Guilman ---
    if d_guilman:
        atual_g = d_guilman[0]
        vazao_g = atual_g.get('vazao', 0)
        
        # 1. Salva no CSV
        salvar_historico_guilman(atual_g)
        
        # 2. Define ícones de alerta para o Telegram
        icone_g = "🌊"
        if vazao_g >= ALERTA_VAZAO_VERMELHO:
            icone_g = "🚨 PERIGO"
            msg_ia_longa += f"⚠️ *URGENTE:* Vazão Guilman CRÍTICA ({vazao_g:.0f} m³/s). Água chega em ~8h!\n"
        elif vazao_g >= ALERTA_VAZAO_AMARELO:
            icone_g = "⚠️ Atenção"
            msg_ia_longa += f"🔸 *Alerta:* Guilman aumentou vazão ({vazao_g:.0f} m³/s).\n"
            
        msg_guilman_tg = f"{icone_g} Guilman: *{vazao_g:.0f} m³/s*"
    else:
        msg_guilman_tg = "Guilman: Sem dados"


    if MODO_TESTE or (ULTIMA_DATA_ANA != atual_t['data']):
        salvar_csv(atual_t['data'], atual_t['nivel'], tendencia, "Timoteo")
        ULTIMA_DATA_ANA = atual_t['data']

    # Você pode passar d_guilman aqui no futuro para melhorar a estratégia
    deve_postar, intervalo_min, motivo = definir_estrategia_postagem(d_timoteo, d_barragem, d_nova_era)
    
    # -------------------------------------------------------------
    # 2. BUSCA HISTÓRICA (NÍVEL TIMÓTEO + VAZÃO GUILMAN)
    # -------------------------------------------------------------
    historico_anos = {}
    for ano in [2020, 2021, 2022, 2023, 2024, 2025]:
        val = buscar_nivel_historico(ano)
        historico_anos[ano] = val
    
    velocidade_texto = calcular_velocidade_rio(atual_t['nivel'], atual_t['data'])
    em_recessao = verificar_modo_vazante(atual_t['nivel'])
    risco = calcular_risco_por_rua(atual_t['nivel'])
    
    if em_recessao: registrar_log("MODO VAZANTE DETECTADO! 📉", enviar_tg=False)

    historico_vazao_guilman = {}
    for ano in [2020, 2022, 2024, 2025]: 
        val_vazao = buscar_vazao_historica(ano, ESTACAO_GUILMAN)
        historico_vazao_guilman[ano] = val_vazao

    # -------------------------------------------------------------
    # 3. CÉREBRO IA 
    # -------------------------------------------------------------
    # (Seu código de IA continua igual aqui...)
    try:
        if d_timoteo and len(d_timoteo) >= 4:
            prev_curta, vel_ia = cerebro_ia.prever_proxima_hora(d_timoteo[:6])
            if prev_curta:
                nivel_futuro = prev_curta 
                previsao_ia_texto = f"Prev. +1h: {prev_curta:.0f} cm"
                msg_ia_longa += f"🔮 Previsão Imediata (+1h): *{prev_curta:.0f} cm* ({vel_ia})\n"
    except Exception as e:
        registrar_log(f"Erro IA Curta: {e}", enviar_tg=False)

    # (Seu código de IA Nova Era continua igual aqui...)
    
    # -------------------------------------------------------------
    # 3.5 CONSULTA METEOROLOGIA
    # -------------------------------------------------------------
    texto_clima = ""
    try:
        texto_clima = monitor_clima.gerar_boletim_completo()
    except Exception as e:
        registrar_log(f"Erro Clima: {e}", enviar_tg=False)    


    # --- [NOVA LÓGICA] DETECTOR DE TEMPESTADE FUTURA ---
    # Vamos "ler" o texto do clima para ver se tem acumulados altos
    alerta_futuro_emoji = ""
    mensagem_extra_risco = ""

    # -------------------------------------------------------------
    # 4. ENVIA RELATÓRIO TELEGRAM (ATUALIZADO)
    # -------------------------------------------------------------
    try:
        msg_tg = f"🚨 *MONITORAMENTO DO RIO* (Ciclo 15min)\n"
        msg_tg += f"Nível Atual: *{atual_t['nivel']} cm*\n"
        msg_tg += f"{msg_guilman_tg}\n" # <--- [NOVO] Linha da Guilman adicionada
        
        if msg_ia_longa:
            msg_tg += f"\n{msg_ia_longa}\n"

        if texto_clima:
            msg_tg += f"\n{texto_clima}\n"    
            
        msg_tg += f"Tendência: {tendencia} {velocidade_texto}\n"
        # ... (O resto do Telegram continua igual)
        
        # ... (Continuação do código original: Histórico, Ruas, Envio...)
        msg_tg += f"Status: {motivo}\n"
        if em_recessao: msg_tg += "📉 *MODO VAZANTE ATIVO*\n"
        
        msg_tg += "\n📅 *HISTÓRICO (Mesma data):*\n"
        for ano in sorted(historico_anos.keys()):
            val = historico_anos[ano]
            msg_tg += f"• {ano}: {val} cm\n"

        msg_tg += "\n🌊 *HISTÓRICO GUILMAN (Vazão):*\n"
        for ano in sorted(historico_vazao_guilman.keys()):
            val = historico_vazao_guilman[ano]
            unidade = " m³/s" if val != "N/D" and val != "Erro" else ""
            msg_tg += f"• {ano}: {val}{unidade}\n"
        
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
    # VERIFICAÇÃO DA TRAVA MANUAL
    sistema_liberado = verificar_trava_instagram()
    
    if not sistema_liberado:
        if deve_postar: # Se ia postar, mas foi barrado
            registrar_log(f"⛔ POSTAGEM BLOQUEADA MANUALMENTE. (Motivo original: {motivo})", enviar_tg=False)
        deve_postar = False # Força o cancelamento
        motivo = "DESATIVADO MANUALMENTE"
    
    if deve_postar and not MODO_TESTE:
         if "ROTINA" in motivo:
              if ULTIMA_POSTAGEM and (datetime.now() - ULTIMA_POSTAGEM).total_seconds() < 3600: deve_postar = False
         elif ULTIMA_POSTAGEM:
            tempo_passado = (datetime.now() - ULTIMA_POSTAGEM).total_seconds() / 60
            if tempo_passado < intervalo_min:
                registrar_log(f"Aguardando intervalo IG ({tempo_passado:.0f}/{intervalo_min} min).", enviar_tg=False)
                deve_postar = False
    
    if deve_postar:
        # ... (Resto do código de postagem)
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
                dados_grafico=d_timoteo 
            )
            caminhos_abs = [str(Path(p).resolve()) for p in caminhos]
        except Exception as e:
            registrar_log(f"Erro ao gerar imagens: {e}")
            return

        # ENVIA EMAIL
        if "ROTINA" not in motivo:
            try: enviar_email_alerta(caminhos_abs, atual_t['nivel'], f"{tendencia} - {motivo}")
            except: pass
        
        # ENVIA INSTAGRAM
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

        import sqlite3

def salvar_leitura_no_banco(data_hora, nivel):
    """Guarda a leitura atual no banco local para consultas futuras"""
    try:
        conn = sqlite3.connect("rio_doce.db")
        cursor = conn.cursor()
        # Converte a data para string para o SQLite
        dt_str = data_hora.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO historico (data_hora, nivel) VALUES (?, ?)", (dt_str, nivel))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")

def buscar_historico_local(dia, mes):
    """Busca o nível médio do rio para o dia/mês em cada ano no banco SQLite"""
    resultados = {}
    try:
        # Garante que o caminho para o banco está correto
        caminho_banco = os.path.join(os.path.dirname(__file__), "rio_doce.db")
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()
        
        # Query para pegar a média do nível naquele dia específico de cada ano
        query = """
            SELECT strftime('%Y', data_hora) as ano, AVG(nivel) 
            FROM historico 
            WHERE strftime('%d', data_hora) = ? 
              AND strftime('%m', data_hora) = ?
            GROUP BY ano
            ORDER BY ano ASC
        """
        # Passa dia e mês com dois dígitos (ex: 01, 02...)
        cursor.execute(query, (f"{dia:02d}", f"{mes:02d}"))
        
        for ano, nivel in cursor.fetchall():
            # Retorna apenas os anos que temos dados (2019 a 2025)
            resultados[int(ano)] = round(nivel, 0)
            
        conn.close()
    except Exception as e:
        print(f"Erro ao consultar histórico local: {e}")
        
    return resultados