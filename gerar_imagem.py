from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES VISUAIS
# ==============================================================================
# Cores
COR_BRANCA = (255, 255, 255)
COR_PRETA = (0, 0, 0)

# Cores de Alerta (Fundo)
COR_NORMAL = (46, 204, 113)      # Verde
COR_ATENCAO = (241, 196, 15)     # Amarelo
COR_ALERTA = (230, 126, 34)      # Laranja
COR_PERIGO = (231, 76, 60)       # Vermelho
COR_INUNDACAO = (142, 68, 173)   # Roxo (Crítico)

def obter_cor_fundo(nivel):
    if nivel < 400: return COR_NORMAL
    if nivel < 600: return COR_ATENCAO
    if nivel < 760: return COR_ALERTA
    if nivel < 900: return COR_PERIGO
    return COR_INUNDACAO

def obter_texto_situacao(nivel):
    if nivel < 400: return "NÍVEL NORMAL"
    if nivel < 600: return "ATENÇÃO"
    if nivel < 760: return "ALERTA DE CHEIA"
    if nivel < 900: return "PERIGO: INUNDAÇÃO"
    return "CATASTRÓFICO"

# ==============================================================================
# FUNÇÃO 1: GERAR CAPA UNIFICADA (Nível + Histórico)
# ==============================================================================
def gerar_capa(dados_rio, tendencia, hist_2020, hist_2022):
    nivel = dados_rio['nivel_cm']
    data_leitura = dados_rio['data_leitura']
    
    # 1. Configurar Imagem
    largura, altura = 1080, 1920
    cor_fundo = obter_cor_fundo(nivel)
    img = Image.new('RGB', (largura, altura), color=cor_fundo)
    draw = ImageDraw.Draw(img)

    # 2. Carregar Fontes (Tenta carregar Arial, senão usa padrão)
    try:
        font_titulo = ImageFont.truetype("arial.ttf", 100)
        font_nivel = ImageFont.truetype("arialbd.ttf", 250) # Negrito Grande
        font_tendencia = ImageFont.truetype("arial.ttf", 80)
        font_hist_titulo = ImageFont.truetype("arialbd.ttf", 60)
        font_hist_valor = ImageFont.truetype("arial.ttf", 70)
        font_rodape = ImageFont.truetype("arial.ttf", 40)
    except:
        # Fallback se não tiver fonte instalada
        font_titulo = ImageFont.load_default()
        font_nivel = ImageFont.load_default()
        font_tendencia = ImageFont.load_default()
        font_hist_titulo = ImageFont.load_default()
        font_hist_valor = ImageFont.load_default()
        font_rodape = ImageFont.load_default()

    # 3. Desenhar Texto: SITUAÇÃO (Topo)
    situacao = obter_texto_situacao(nivel)
    # Centraliza o texto
    w = draw.textlength(situacao, font=font_titulo)
    draw.text(((largura-w)/2, 150), situacao, font=font_titulo, fill=COR_BRANCA)

    # 4. Desenhar Texto: NÍVEL ATUAL (Centro)
    texto_nivel = f"{nivel:.0f} cm"
    w = draw.textlength(texto_nivel, font=font_nivel)
    draw.text(((largura-w)/2, 350), texto_nivel, font=font_nivel, fill=COR_BRANCA)
    
    # 5. Desenhar Texto: TENDÊNCIA
    w = draw.textlength(tendencia, font=font_tendencia)
    draw.text(((largura-w)/2, 650), tendencia, font=font_tendencia, fill=COR_BRANCA)

    # --- LINHA DIVISÓRIA ---
    draw.line([(100, 800), (980, 800)], fill=COR_BRANCA, width=5)

    # 6. Desenhar Texto: COMPARATIVO HISTÓRICO (Abaixo da linha)
    # Título da Seção
    titulo_hist = "COMPARATIVO (Mesma data/hora):"
    w = draw.textlength(titulo_hist, font=font_hist_titulo)
    draw.text(((largura-w)/2, 850), titulo_hist, font=font_hist_titulo, fill=COR_BRANCA)

    # Valor 2022
    texto_2022 = f"Em 2022: {hist_2022} cm"
    w = draw.textlength(texto_2022, font=font_hist_valor)
    draw.text(((largura-w)/2, 950), texto_2022, font=font_hist_valor, fill=COR_BRANCA)

    # Valor 2020
    texto_2020 = f"Em 2020: {hist_2020} cm"
    w = draw.textlength(texto_2020, font=font_hist_valor)
    draw.text(((largura-w)/2, 1050), texto_2020, font=font_hist_valor, fill=COR_BRANCA)

    # 7. Rodapé (Data)
    texto_data = f"Atualizado: {data_leitura.strftime('%d/%m %H:%M')}"
    w = draw.textlength(texto_data, font=font_rodape)
    draw.text(((largura-w)/2, 1800), texto_data, font=font_rodape, fill=COR_BRANCA)

    # Salvar
    caminho = "output/capa_unificada.png"
    if not os.path.exists("output"): os.makedirs("output")
    img.save(caminho)
    return caminho

# ==============================================================================
# FUNÇÃO 2: GERAR PLACAR DAS RUAS (Mantida quase igual)
# ==============================================================================
def gerar_placar(risco_ruas):
    largura, altura = 1080, 1920
    img = Image.new('RGB', (largura, altura), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    try:
        font_titulo = ImageFont.truetype("arialbd.ttf", 80)
        font_rua = ImageFont.truetype("arial.ttf", 55) # Diminuí um pouco a fonte da rua para caber nomes longos
        font_status = ImageFont.truetype("arialbd.ttf", 60)
    except:
        font_titulo = ImageFont.load_default()
        font_rua = ImageFont.load_default()
        font_status = ImageFont.load_default()

    # Título
    draw.text((50, 100), "SITUAÇÃO DAS RUAS", font=font_titulo, fill=COR_BRANCA)
    draw.line([(50, 200), (1030, 200)], fill=COR_BRANCA, width=3)

    # === CONFIGURAÇÕES DO GRÁFICO (Mude aqui para ajustar) ===
    POS_X_NOME = 50          # Onde começa o nome da rua
    POS_X_BARRA = 520        # Onde começa a barra (Empurrei pra direita para dar espaço ao nome)
    LARGURA_MAX_BARRA = 350  # <--- REDUZI O TAMANHO (Era 400)
    POS_X_PORCENTAGEM = 910  # <--- PUXEI PARA A ESQUERDA (Era 970)
    ALTURA_BARRA = 40        # Grossura da barra
    # ========================================================

    y_pos = 250
    for rua in risco_ruas:
        nome = rua['apelido']
        pct = rua['porcentagem']
        
        # Cores baseadas no risco
        cor_barra = COR_NORMAL
        if pct > 50: cor_barra = COR_ATENCAO
        if pct > 80: cor_barra = COR_ALERTA
        if pct >= 100: cor_barra = COR_PERIGO

        # 1. Desenhar Nome da Rua
        draw.text((POS_X_NOME, y_pos), nome, font=font_rua, fill=COR_BRANCA)
        
        # 2. Desenhar Fundo da Barra (Cinza Escuro)
        # Vai do inicio da barra até o tamanho máximo
        draw.rectangle(
            [(POS_X_BARRA, y_pos + 10), (POS_X_BARRA + LARGURA_MAX_BARRA, y_pos + 10 + ALTURA_BARRA)], 
            fill=(50,50,50)
        )

        # 3. Desenhar Barra Colorida (Progresso)
        # TRAVA DE SEGURANÇA: Usamos min(pct, 100) para a barra nunca passar do limite visual
        pct_visual = min(pct, 100.0) 
        comprimento_atual = (pct_visual / 100) * LARGURA_MAX_BARRA
        
        draw.rectangle(
            [(POS_X_BARRA, y_pos + 10), (POS_X_BARRA + comprimento_atual, y_pos + 10 + ALTURA_BARRA)], 
            fill=cor_barra
        )
        
        # 4. Desenhar Porcentagem
        # O texto fica na posição fixa definida lá em cima
        draw.text((POS_X_PORCENTAGEM, y_pos), f"{pct:.0f}%", font=font_status, fill=cor_barra)

        y_pos += 120 # Pula para a próxima linha

    caminho = "output/placar_ruas.png"
    img.save(caminho)
    return caminho

# ==============================================================================
# ORQUESTRADOR
# ==============================================================================
def gerar_todas_imagens(dados_rio, dados_ruas, tendencia, h2020, h2022):
    """
    Gera a capa unificada e o placar.
    Retorna lista com 2 caminhos.
    """
    caminho1 = gerar_capa(dados_rio, tendencia, h2020, h2022)
    caminho2 = gerar_placar(dados_ruas)
    
    return [caminho1, caminho2]