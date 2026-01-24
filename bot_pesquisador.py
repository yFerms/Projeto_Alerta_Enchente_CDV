import telebot
from telebot import types
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import csv
import os
import re

# --- CORREÇÃO DO ERRO GUI ---
import matplotlib
matplotlib.use('Agg') # <--- ESSA É A LINHA MÁGICA. Coloque antes do pyplot!
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
# ----------------------------

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# Crie um novo bot no BotFather para não conflitar com o Monitor de Alertas
TOKEN_PESQUISADOR = "8421767351:AAGDWLADJ95X4Xz6j3MBfWNGa7v98-jMN5c" 

bot = telebot.TeleBot(TOKEN_PESQUISADOR)

# Mapeamento de Nomes para Códigos ANA
ESTACOES = {
    "timoteo": "56696000",
    "timóteo": "56696000",
    "nova era": "56661000",
    "guilman": "56675080",
    "barragem": "56675080",
    "sa carvalho": "56675080"
}

def criar_menu_principal():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    # Botões Dinâmicos (Calculam a data na hora)
    btn1 = types.KeyboardButton("🌊 Timóteo (24h)")
    btn2 = types.KeyboardButton("📅 Timóteo (7 dias)")
    
    # Botões Históricos (Datas Fixas das Enchentes)
    btn3 = types.KeyboardButton("⚠️ Enchente 2020")
    btn4 = types.KeyboardButton("⚠️ Enchente 2022")
    
    # Botão de Ajuda
    btn_help = types.KeyboardButton("❓ Como usar")
    
    markup.add(btn1, btn2, btn3, btn4, btn_help)
    return markup

# ==============================================================================
# FUNÇÕES DE BUSCA
# ==============================================================================
def buscar_historico_ana(codigo, data_inicio, data_fim):
    """Busca dados brutos na ANA e retorna uma lista de dicionários"""
    url = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
    
    params = {
        "codEstacao": codigo,
        "dataInicio": data_inicio,
        "dataFim": data_fim
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            dados = []
            
            for leitura in root.iter("DadosHidrometereologicos"):
                dt_str = leitura.find("DataHora")
                nivel = leitura.find("Nivel")
                vazao = leitura.find("Vazao")
                chuva = leitura.find("Chuva") # <--- [NOVO]
                
                if dt_str is not None:
                    try:
                        val_nivel = float(nivel.text) if (nivel is not None and nivel.text) else 0.0
                        val_vazao = float(vazao.text) if (vazao is not None and vazao.text) else 0.0
                        # [NOVO] Captura Chuva (se vazio, assume 0)
                        val_chuva = float(chuva.text) if (chuva is not None and chuva.text) else 0.0
                        
                        dados.append({
                            "Data": dt_str.text.strip(),
                            "Nivel_cm": val_nivel,
                            "Vazao_m3s": val_vazao,
                            "Chuva_mm": val_chuva # <--- [NOVO]
                        })
                    except: continue
            
            dados.sort(key=lambda x: datetime.strptime(x['Data'], "%Y-%m-%d %H:%M:%S"))
            return dados
    except Exception as e:
        print(f"Erro na API: {e}")
        return []
    return []

def gerar_csv(dados, nome_arquivo):
    if not dados: return None
    caminho = f"{nome_arquivo}.csv"
    with open(caminho, mode='w', newline='') as f:
        # [NOVO] Adicionado "Chuva_mm" no cabeçalho
        writer = csv.DictWriter(f, fieldnames=["Data", "Nivel_cm", "Vazao_m3s", "Chuva_mm"])
        writer.writeheader()
        writer.writerows(dados)
    return caminho

# ==============================================================================
# LÓGICA DO CHAT (BOT)
# ==============================================================================
def gerar_grafico_memoria(dados, nome_estacao):
    datas = [datetime.strptime(d['Data'], "%Y-%m-%d %H:%M:%S") for d in dados]
    chuvas = [d['Chuva_mm'] for d in dados]
    
    # Define se o foco principal é Vazão (Guilman) ou Nível (Timóteo)
    if "Vazao_m3s" in dados[0] and dados[0]["Vazao_m3s"] > 0 and "Guilman" in nome_estacao:
        valores_principais = [d['Vazao_m3s'] for d in dados]
        label_principal = "Vazão (m³/s)"
        cor_principal = "#d35400" # Laranja Escuro
        limite_alerta = 1200
    else:
        valores_principais = [d['Nivel_cm'] for d in dados]
        label_principal = "Nível (cm)"
        cor_principal = "#c0392b" # Vermelho Escuro
        limite_alerta = 620
        
    # --- CRIAÇÃO DO GRÁFICO ---
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # 1. Plot da CHUVA (Barras no Eixo Secundário)
    # Criamos o eixo "gêmeo" que compartilha o mesmo eixo X (Datas)
    ax2 = ax1.twinx() 
    # width=0.01 ajusta a largura da barra para não cobrir tudo (escala de dias)
    ax2.bar(datas, chuvas, color='#3498db', alpha=0.3, label="Chuva (mm)", width=0.015)
    ax2.set_ylabel("Chuva (mm)", color='#3498db')
    ax2.tick_params(axis='y', labelcolor='#3498db')
    
    # Define limite mínimo para o eixo da chuva para as barras não ocuparem a tela toda
    # Se a chuva máx for 10mm, o eixo vai até 30mm, deixando as barras baixinhas
    if max(chuvas) > 0:
        ax2.set_ylim(0, max(chuvas) * 3) 
    
    # 2. Plot do RIO (Linha no Eixo Principal - Fica POR CIMA das barras)
    # zorder=10 garante que a linha desenhe sobre a barra
    ax1.plot(datas, valores_principais, color=cor_principal, linewidth=2.5, label=label_principal, zorder=10)
    ax1.set_ylabel(label_principal, color=cor_principal)
    ax1.tick_params(axis='y', labelcolor=cor_principal)
    
    # Linha de Alerta (Tracejada)
    ax1.axhline(y=limite_alerta, color='red', linestyle='--', linewidth=1, label='Cota de Alerta', zorder=11)
    
    # Títulos e Grades
    plt.title(f"Monitoramento: {nome_estacao}\n(Linha = Rio | Barras = Chuva)")
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # Formatação de Datas
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate()
    
    # Legenda Unificada (Truque para juntar linha e barra na mesma legenda)
    linhas, labels = ax1.get_legend_handles_labels()
    barras, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(linhas + barras, labels + labels2, loc='upper left')

    # Salvar
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "👋 **Painel de Pesquisa do Rio Piracicaba**\n\n"
        "Selecione uma opção rápida abaixo ou digite manualmente.\n"
        "Ex manual: *Timóteo 23/01/2020 a 25/01/2020*"
    )
    # Envia a mensagem COM o menu acoplado
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(func=lambda message: True)
def processar_pedido(message):
    msg = message.text
    chat_id = message.chat.id
    
    # Variáveis para busca
    codigo_estacao = "56696000" # Padrão Timóteo
    nome_estacao = "Timóteo"
    dt_inicio = ""
    dt_fim = ""
    
    agora = datetime.now()

    # --- LÓGICA DOS BOTÕES ---
    if msg == "🌊 Timóteo (24h)":
        dt_inicio = (agora - timedelta(days=1)).strftime("%d/%m/%Y")
        dt_fim = agora.strftime("%d/%m/%Y")
        
    elif msg == "📅 Timóteo (7 dias)":
        dt_inicio = (agora - timedelta(days=7)).strftime("%d/%m/%Y")
        dt_fim = agora.strftime("%d/%m/%Y")
        
    elif msg == "⚠️ Enchente 2020":
        # Data histórica da grande cheia de 2020
        dt_inicio = "23/01/2020"
        dt_fim = "28/01/2020"
        
    elif msg == "⚠️ Enchente 2022":
        # Data histórica da grande cheia de 2022
        dt_inicio = "07/01/2022"
        dt_fim = "12/01/2022"
        
    elif msg == "❓ Como usar":
        bot.reply_to(message, "Digite o local e as datas.\nEx: 'Guilman 01/01/2023 a 05/01/2023'")
        return

    # --- LÓGICA MANUAL (Se não for botão, tenta ler o que o usuário escreveu) ---
    else:
        # Tenta achar datas no texto (Regex)
        datas_encontradas = re.findall(r"\d{2}/\d{2}/\d{4}", msg)
        
        if len(datas_encontradas) >= 2:
            dt_inicio = datas_encontradas[0]
            dt_fim = datas_encontradas[1]
            
            # Verifica se o usuário pediu outra estação
            if "guilman" in msg.lower() or "barragem" in msg.lower():
                codigo_estacao = "56675080"
                nome_estacao = "UHE Guilman"
            elif "nova era" in msg.lower():
                codigo_estacao = "56661000"
                nome_estacao = "Nova Era"
        else:
            bot.reply_to(message, "⚠️ Não entendi. Use os botões abaixo ou digite datas no formato DD/MM/AAAA.")
            return

    # --- EXECUÇÃO DA BUSCA (Igual ao anterior) ---
    bot.reply_to(message, f"🔎 Buscando **{nome_estacao}**\n📅 {dt_inicio} até {dt_fim}...", parse_mode="Markdown")

    dados = buscar_historico_ana(codigo_estacao, dt_inicio, dt_fim)
    
    if not dados:
        bot.reply_to(message, "❌ Nenhum dado encontrado ou erro na ANA.")
        return

    # Gera Resumo Texto
    niveis = [d['Nivel_cm'] for d in dados if d['Nivel_cm'] > 0]
    resumo = f"📊 **Resultados: {nome_estacao}**\n"
    if niveis:
        resumo += f"🌊 Máx: {max(niveis)} cm | Mín: {min(niveis)} cm\n"
    
    # Gera Gráfico (Função que criamos antes)
    try:
        foto = gerar_grafico_memoria(dados, nome_estacao)
        bot.send_photo(chat_id, foto, caption=resumo, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Erro no gráfico: {e}")

    # Gera CSV
    arquivo_csv = gerar_csv(dados, f"dados_{nome_estacao}")
    with open(arquivo_csv, 'rb') as f:
        bot.send_document(chat_id, f)
    os.remove(arquivo_csv)

# INICIA O BOT (LOOP INFINITO)
print("🤖 Bot Pesquisador Iniciado...")
bot.polling()