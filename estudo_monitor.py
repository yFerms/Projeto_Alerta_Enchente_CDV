"""
SISTEMA SENTINELA DE MONITORAMENTO HIDROLÓGICO - RIO PIRACICABA
------------------------------------------------------------------
Autor: [Seu Nome]
Objetivo: Monitorar níveis de rios e barragens, prever enchentes e alertar a população via Instagram.
Lógica: Utiliza dados oficiais da ANA (Agência Nacional de Águas) e autômatos para postagem.
"""

# --- IMPORTAÇÃO DE BIBLIOTECAS ---
import requests                         # Para fazer requisições HTTP (baixar o XML da ANA)
import xml.etree.ElementTree as ET      # Para ler e "traduzir" o formato XML que a ANA entrega
from datetime import datetime, timedelta # Para lidar com datas, horas e cálculos de tempo
import time                             # Para pausar o código (sleep)
import os                               # Para mexer em arquivos do sistema (verificar se existe arquivo)
import csv                              # Para salvar o histórico em planilhas Excel/CSV
import json                             # Para salvar o contador de stories (banco de dados simples)
from pathlib import Path                # Para lidar com caminhos de pastas de forma correta no Windows
from dotenv import load_dotenv          # Para carregar senhas e configurações seguras (arquivo .env)

# --- MÓDULOS DO PRÓPRIO PROJETO (ARQUIVOS .PY SEPARADOS) ---
from gerar_imagem import gerar_todas_imagens     # Função que desenha os infográficos
from dados_ruas import calcular_risco_por_rua    # Função matemática que cruza cota do rio x cota da rua
from android_bot import enviar_carrossel_android # Automação que controla o celular via ADB
from email_bot import enviar_email_alerta        # Função de envio de e-mail (backup)

# Carrega as variáveis de ambiente (se houver senhas salvas)
load_dotenv()

# ==========================================
# 🎛️ PAINEL DE CONTROLE (CONSTANTES DE CALIBRAÇÃO)
# ==========================================
# Define se estamos testando (False = Modo Real, conectado à ANA)
MODO_TESTE = False           

# --- LIMITES DE SEGURANÇA (ESTAÇÃO TIMÓTEO) ---
# Níveis baseados na cota de inundação do Cachoeira do Vale
LIMITE_ALERTA = 600          # 600cm (6 metros) -> Água começa a preocupar áreas baixas
LIMITE_GRAVE = 760           # 760cm (7.6 metros) -> Água invade ruas críticas

# --- GATILHOS DE VELOCIDADE (FLASH FLOOD) ---
# Baseado na análise histórica da enchente de 2022 e 2020
VELOCIDADE_ALERTA = 10       # Se subir +10cm em 1 hora = Sinal amarelo
VELOCIDADE_PANICO = 30       # Se subir +30cm em 1 hora = "Cabeça d'água" (Perigo Imediato)

# --- GATILHOS PREDITIVOS (RIO ACIMA) ---
# Se a Barragem (Sá Carvalho) subir 40cm em 15min, indica abertura de comportas
DELTA_BARRAGEM_CRITICO = 40  
# Se Nova Era (8h de distância) subir 50cm em 1h, indica onda de cheia chegando
DELTA_NOVA_ERA_ALERTA = 50   

# Arquivo onde salvamos quantos stories já postamos hoje
ARQUIVO_CONTADOR = "stories_ativos.json" 
# ==========================================

# --- IDENTIFICAÇÃO DAS ESTAÇÕES (CÓDIGOS DA ANA) ---
# IDs extraídos dos relatórios PDF históricos
ESTACAO_TIMOTEO = "56696000"    # Local (Onde a enchente acontece)
ESTACAO_BARRAGEM = "56688080"   # Antônio Dias (Monitora vazão da usina - Previsão de 2h)
ESTACAO_NOVA_ERA = "56661000"   # Nova Era (Cabeceira do rio - Previsão de 8h)

# Variáveis globais para controlar o estado do robô na memória
ULTIMA_DATA_ANA = None      # Guarda a data da última leitura para não repetir dados
ULTIMA_POSTAGEM = None      # Guarda o horário do último post para respeitar intervalos

# --- FUNÇÃO 1: SISTEMA DE LOGS ---
def registrar_log(mensagem):
    """
    Escreve mensagens no terminal e salva num arquivo de texto (sistema.log).
    Isso serve para 'auditoria' caso o robô dê erro de madrugada.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Pega hora atual
    texto_formatado = f"[{timestamp}] {mensagem}"            # Formata: [Hora] Mensagem
    print(texto_formatado)                                   # Mostra na tela preta
    # Abre o arquivo em modo 'append' (adicionar ao final)
    with open("sistema.log", "a", encoding="utf-8") as f:
        f.write(texto_formatado + "\n")

# --- FUNÇÃO 2: BANCO DE DADOS CSV ---
def salvar_csv(data_hora, nivel, tendencia, estacao):
    """
    Salva os dados brutos num arquivo Excel (.csv) para estudos futuros.
    """
    arquivo = "historico_rio.csv"
    existe = os.path.exists(arquivo) # Verifica se o arquivo já foi criado antes
    
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Se for arquivo novo, escreve o cabeçalho primeiro
        if not existe:
            writer.writerow(["DataHora", "Estacao", "Nivel", "Tendencia"]) 
        # Escreve a linha de dados
        writer.writerow([data_hora, estacao, nivel, tendencia])

# --- FUNÇÃO 3: O "FAXINEIRO" DE STORIES ---
def gerenciar_contador_stories():
    """
    Controla quantos stories estão ativos.
    Se tiver 9 ou mais, retorna True para o robô apagar os 3 mais antigos.
    Isso evita que o perfil vire um 'formigueiro' de tracinhos.
    """
    # Tenta ler o arquivo JSON salvo no disco
    if os.path.exists(ARQUIVO_CONTADOR):
        with open(ARQUIVO_CONTADOR, "r") as f:
            try:
                dados = json.load(f)
            except: dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    else:
        # Se não existir, cria um zerado
        dados = {"qtd": 0, "ultima_limpeza": str(datetime.now())}
    
    qtd_atual = dados["qtd"]
    deve_limpar = False
    
    # Lógica: O limite é 9. Se já tem 9, precisamos limpar antes de postar.
    if qtd_atual >= 9:
        registrar_log(f"🧹 Limite de stories atingido ({qtd_atual}). Agendando limpeza.")
        deve_limpar = True
        nova_qtd = qtd_atual # (Apaga 3, Soma 3 = Mantém a quantidade)
    else:
        registrar_log(f"➕ Adicionando stories. Total será: {qtd_atual + 3}")
        deve_limpar = False
        nova_qtd = qtd_atual + 3 # Apenas soma
        
    # Salva o novo número no arquivo para a próxima vez
    dados["qtd"] = nova_qtd
    dados["ultima_limpeza"] = str(datetime.now())
    with open(ARQUIVO_CONTADOR, "w") as f:
        json.dump(dados, f)
        
    return deve_limpar # Retorna True ou False para o robô

# --- FUNÇÃO 4: BUSCADOR DE DADOS (O "CRAWLER") ---
def buscar_dados_xml(codigo_estacao):
    """
    Conecta no site da ANA, baixa o XML da estação específica e trata os dados.
    """
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1) # Pega dados das últimas 24h
    
    # Parâmetros exigidos pela API da ANA
    params = {
        "codEstacao": codigo_estacao,
        "dataInicio": ontem.strftime("%d/%m/%Y"),
        "dataFim": hoje.strftime("%d/%m/%Y"),
    }

    try:
        # Faz a requisição na internet (timeout de 20s para não travar se cair a rede)
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200: # 200 = Sucesso
            root = ET.fromstring(response.content) # Converte texto em estrutura XML
            leituras = []
            
            # Navega pelas tags do XML procurando <Nivel> e <DataHora>
            for dado in root.iter("DadosHidrometereologicos"):
                nivel = dado.find("Nivel")
                data_hora = dado.find("DataHora")
                
                # Só aceita se os dados existirem e não forem vazios
                if (nivel is not None and nivel.text is not None and 
                    data_hora is not None and data_hora.text is not None):
                    try:
                        dt = datetime.strptime(data_hora.text.strip(), "%Y-%m-%d %H:%M:%S")
                        leituras.append({"data": dt, "nivel": float(nivel.text)})
                    except: continue 
            
            # Ordena do mais recente para o mais antigo
            leituras.sort(key=lambda x: x['data'], reverse=True)
            return leituras # Devolve a lista limpa
        return []
    except Exception as e:
        registrar_log(f"❌ Erro de Conexão ANA ({codigo_estacao}): {e}")
        return []

# --- FUNÇÃO 5: CÁLCULO DE VELOCIDADE ---
def analisar_velocidade(leituras, janela_horas=1):
    """
    Calcula quantos cm o rio subiu na última hora (ou janela de tempo).
    É vital para detectar enchentes relâmpago (Flash Floods).
    """
    if len(leituras) < 2: return 0 # Se não tem histórico, retorna 0
    
    agora = leituras[0] # Leitura mais recente
    
    # Procura na lista uma leitura que aconteceu ~1 hora atrás
    for l in leituras:
        # Calcula diferença de tempo em horas
        diff_tempo = (agora['data'] - l['data']).total_seconds() / 3600
        
        # Aceita leituras entre 48min (0.8h) e 1h12min (1.2h) atrás
        if (janela_horas * 0.8) <= diff_tempo <= (janela_horas * 1.2):
            delta = agora['nivel'] - l['nivel'] # Diferença de nível
            return delta # Retorna ex: +15 ou -5
            
    return 0

# --- FUNÇÃO 6: DEFINIÇÃO DE TENDÊNCIA ---
def analisar_tendencia(leituras):
    """
    Diz se o rio está subindo, descendo ou parado com base na última leitura.
    """
    if len(leituras) < 2: return "Estável ➖"
    diff = leituras[0]['nivel'] - leituras[1]['nivel']
    
    if diff > 0: return f"SUBINDO 🔺 (+{diff:.0f}cm)"
    elif diff < 0: return f"BAIXANDO 🔻 ({diff:.0f}cm)"
    return "ESTÁVEL ➖"

# --- FUNÇÃO 7: O CÉREBRO (ESTRATÉGIA) ---
def definir_estrategia_postagem(dados_timoteo, dados_barragem, dados_nova_era):
    """
    Analisa os 3 pontos (Nova Era, Barragem, Timóteo) e decide o 'MODO' do robô.
    Retorna: (Deve Postar?, Intervalo em minutos, Texto do Motivo)
    """
    
    # 1. Verifica Timóteo (Realidade Local)
    if not dados_timoteo: return False, 720, "Erro Timóteo"
    nivel_timoteo = dados_timoteo[0]['nivel']
    vel_timoteo = analisar_velocidade(dados_timoteo, 1) # Variação na última hora

    # 2. Verifica Barragem (Previsão de 2h)
    delta_barragem = 0
    if dados_barragem and len(dados_barragem) >= 2:
        # Variação imediata (últimos 15 min a 30 min)
        delta_barragem = dados_barragem[0]['nivel'] - dados_barragem[1]['nivel']

    # 3. Verifica Nova Era (Previsão de 8h)
    delta_nova_era = 0
    if dados_nova_era:
        delta_nova_era = analisar_velocidade(dados_nova_era, 1)

    # --- MATRIZ DE DECISÃO (A LÓGICA DO TCC) ---

    # A. CENÁRIO DE GUERRA (Emergência Total -> Posta a cada 15 min)
    if delta_barragem >= DELTA_BARRAGEM_CRITICO:
        return True, 15, f"🚨 BARRAGEM CRÍTICA (+{delta_barragem}cm)"
    
    if vel_timoteo >= VELOCIDADE_PANICO:
        # Rio subindo mais que 30cm/h = Pânico
        return True, 15, f"⚡ FLASH FLOOD LOC (+{vel_timoteo}cm/h)"
    
    if nivel_timoteo >= LIMITE_GRAVE:
        # Nível acima de 7.60m
        return True, 15, "🔴 NÍVEL GRAVE"

    # B. CENÁRIO DE ALERTA (Atenção -> Posta a cada 30 min)
    if delta_nova_era >= DELTA_NOVA_ERA_ALERTA:
        # Água vindo de longe
        return True, 30, f"🌊 ONDA VINDO DE NOVA ERA (+{delta_nova_era}cm/h)"
    
    if nivel_timoteo >= LIMITE_ALERTA:
        # Nível acima de 6.00m
        return True, 30, "🟠 NÍVEL DE ALERTA"
    
    if vel_timoteo >= VELOCIDADE_ALERTA:
        # Rio subindo 10cm/h
        return True, 30, f"⚠️ RIO SUBINDO (+{vel_timoteo}cm/h)"

    # C. CENÁRIO DE PAZ / SENTINELA (Posta apenas rotina às 07h e 19h)
    agora = datetime.now()
    
    # Verifica se é hora cheia (7 ou 19) e se está nos primeiros 25min (janela de postagem)
    if (agora.hour == 7 or agora.hour == 19) and agora.minute <= 25:
        return True, 720, "🟢 ROTINA (07h/19h)"
    
    # Se não caiu em nenhuma regra acima, o robô dorme.
    return False, 720, "💤 MONITORANDO (Rio Estável)"

# --- FUNÇÃO 8: LOOP PRINCIPAL (JOB) ---
def job():
    global ULTIMA_DATA_ANA, ULTIMA_POSTAGEM
    
    registrar_log("--- 📡 Iniciando Varredura Tripla ---")
    
    # 1. Busca Dados das 3 Estações
    d_timoteo = buscar_dados_xml(ESTACAO_TIMOTEO)
    d_barragem = buscar_dados_xml(ESTACAO_BARRAGEM)
    d_nova_era = buscar_dados_xml(ESTACAO_NOVA_ERA)

    if not d_timoteo:
        registrar_log("⚠️ Sem dados de Timóteo.")
        return # Aborta se não tem dados locais

    # Pega dados mais recentes
    atual_t = d_timoteo[0]
    tendencia = analisar_tendencia(d_timoteo)
    
    # Salva no CSV se chegou dado novo
    if ULTIMA_DATA_ANA != atual_t['data']:
        salvar_csv(atual_t['data'], atual_t['nivel'], tendencia, "Timoteo")
        # Também salva dados das outras estações para referência
        if d_barragem: salvar_csv(d_barragem[0]['data'], d_barragem[0]['nivel'], "-", "Barragem")
        if d_nova_era: salvar_csv(d_nova_era[0]['data'], d_nova_era[0]['nivel'], "-", "NovaEra")
        ULTIMA_DATA_ANA = atual_t['data']

    # 2. Decide a estratégia baseada na Tríade de Monitoramento
    deve_postar_agora, intervalo_min, motivo = definir_estrategia_postagem(d_timoteo, d_barragem, d_nova_era)
    
    registrar_log(f"📊 Status: {motivo} | Timóteo: {atual_t['nivel']}cm")

    # 3. Verificações de Tempo (Para não postar duplicado)
    if deve_postar_agora:
        # Caso 1: É postagem de Rotina (Verde)?
        if "🟢" in motivo:
            # Só posta se faz mais de 1 hora que não posta (evita repetição na janela das 7h)
            if ULTIMA_POSTAGEM and (datetime.now() - ULTIMA_POSTAGEM).total_seconds() < 3600:
                registrar_log("   ⏳ Já postado nesta janela de horário.")
                deve_postar_agora = False
        
        # Caso 2: É postagem de Alerta (Amarelo/Vermelho)?
        elif ULTIMA_POSTAGEM:
            # Respeita o intervalo definido (15min ou 30min)
            tempo_passado = (datetime.now() - ULTIMA_POSTAGEM).total_seconds() / 60
            if tempo_passado < intervalo_min:
                registrar_log(f"   ⏳ Aguardando intervalo ({tempo_passado:.0f}/{intervalo_min} min).")
                deve_postar_agora = False

    # 4. Execução da Postagem
    if deve_postar_agora:
        registrar_log("🚀 INICIANDO POSTAGEM...")
        
        # Chama o faxineiro para saber se precisa apagar stories antigos
        try:
            precisa_limpar = gerenciar_contador_stories()
        except Exception as e:
            registrar_log(f"⚠️ Erro no contador: {e}")
            precisa_limpar = False # Na dúvida, não apaga

        # Prepara dados para gerar a imagem
        dados_rio = {'nivel_cm': atual_t['nivel'], 'data_leitura': atual_t['data']}
        
        # Calcula risco das ruas (Data Science)
        relatorio_bruto = calcular_risco_por_rua(atual_t['nivel'])
        lista_ruas_formatada = [{'nome': i['apelido'], 'percentual': i['porcentagem']} for i in relatorio_bruto]

        # Gera as 3 imagens (Capa, Lista, Gráfico)
        caminhos = gerar_todas_imagens(dados_rio, lista_ruas_formatada, tendencia)
        # Garante caminhos absolutos para o ADB não se perder
        caminhos_absolutos = [str(Path(p).resolve()) for p in caminhos]

        # Se for Grave ou Alerta, manda E-mail também
        if "🟢" not in motivo:
            try:
                enviar_email_alerta(caminhos_absolutos, atual_t['nivel'], f"{tendencia} - {motivo}")
            except: pass

        # Manda para o celular (MacroDroid)
        try:
            # Passa a flag 'precisa_limpar' para o bot decidir se apaga ou não
            enviar_carrossel_android(caminhos_absolutos, deve_limpar=precisa_limpar)
            
            ULTIMA_POSTAGEM = datetime.now()
            registrar_log("✅ Postado com Sucesso!")
        except Exception as e:
            registrar_log(f"⚠️ Erro Android: {e}")

# --- BLOCO PRINCIPAL (EXECUÇÃO) ---
if __name__ == "__main__":
    registrar_log("🛡️ MONITOR SENTINELA INICIADO")
    registrar_log("   (Nova Era -> Barragem Antônio Dias -> Timóteo)")
    registrar_log("   Postagens de Rotina: 07:00 e 19:00")
    
    try:
        # Loop infinito (Roda 24h por dia)
        while True:
            job() # Executa a verificação
            print("   💤 Aguardando 15 min...")
            time.sleep(15 * 60) # Dorme por 15 minutos (900 segundos)
    except KeyboardInterrupt:
        # Se o usuário apertar Ctrl+C, encerra bonito
        registrar_log("🛑 Encerrado.")