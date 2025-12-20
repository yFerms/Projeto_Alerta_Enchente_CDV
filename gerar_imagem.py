from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path

# --- CONFIGURAÇÃO DE CAMINHOS ---
PASTA_ATUAL = Path(__file__).resolve().parent
PASTA_ASSETS = PASTA_ATUAL / 'assets'
PASTA_OUTPUT = PASTA_ATUAL / 'output'
PASTA_OUTPUT.mkdir(exist_ok=True)

CAMINHO_TEMPLATE = PASTA_ASSETS / "template_story.png"
CAMINHO_FONTE_BOLD = PASTA_ASSETS / "Roboto-Bold.ttf"
CAMINHO_FONTE_REGULAR = PASTA_ASSETS / "Roboto-Regular.ttf"

# --- CORES ---
COR_VERDE = (46, 204, 113)
COR_AMARELO = (241, 196, 15)
COR_LARANJA = (230, 126, 34)
COR_VERMELHO = (231, 76, 60)
COR_CINZA = (50, 50, 50)
COR_BRANCO = (255, 255, 255)
COR_PRETO = (0, 0, 0)

def carregar_fonte(caminho, tamanho):
    try: return ImageFont.truetype(str(caminho), tamanho)
    except: return ImageFont.load_default()

def _base_imagem():
    try: return Image.open(str(CAMINHO_TEMPLATE)).convert("RGBA")
    except: return Image.new('RGBA', (1080, 1920), COR_BRANCO)

def _rodape(draw):
    font = carregar_fonte(CAMINHO_FONTE_REGULAR, 30)
    hora = datetime.now().strftime("%d/%m às %H:%M")
    draw.text((350, 1880), f"Atualizado em: {hora}", font=font, fill=(0, 0, 0))

# 1. CAPA (SEMÁFORO)
def gerar_capa(dados_rio, tendencia):
    img = Image.new('RGBA', (1080, 1920), COR_CINZA)
    draw = ImageDraw.Draw(img)
    nivel = dados_rio['nivel_cm']
    
    cor_fundo = COR_VERDE
    texto = "NÍVEL NORMAL"
    if nivel > 450: cor_fundo, texto = COR_AMARELO, "ATENÇÃO"
    if nivel > 650: cor_fundo, texto = COR_LARANJA, "ALERTA"
    if nivel > 786: cor_fundo, texto = COR_VERMELHO, "INUNDAÇÃO"
        
    draw.rectangle([0, 0, 1080, 1920], fill=cor_fundo)
    
    f_status = carregar_fonte(CAMINHO_FONTE_BOLD, 100)
    f_nivel = carregar_fonte(CAMINHO_FONTE_BOLD, 250)
    f_tend = carregar_fonte(CAMINHO_FONTE_BOLD, 55)
    f_cm = carregar_fonte(CAMINHO_FONTE_REGULAR, 100)
    
    draw.text((50, 400), texto, font=f_status, fill=COR_BRANCO)
    draw.text((50, 700), f"{nivel:.0f}", font=f_nivel, fill=COR_BRANCO)
    draw.text((750, 840), "cm", font=f_cm, fill=COR_BRANCO)
    draw.text((50, 1100), f"Tendência: {tendencia}", font=f_tend, fill=COR_BRANCO)
    
    _rodape(draw)
    path = PASTA_OUTPUT / "1_capa.png"
    img.save(path)
    return str(path)

# 2. PLACAR DAS RUAS (VERSÃO EXPANDIDA - 16 RUAS)
def gerar_placar(dados_rio, lista_ruas):
    img = _base_imagem()
    draw = ImageDraw.Draw(img)
    
    f_titulo = carregar_fonte(CAMINHO_FONTE_BOLD, 70)
    f_subtitulo = carregar_fonte(CAMINHO_FONTE_REGULAR, 40)
    f_item = carregar_fonte(CAMINHO_FONTE_BOLD, 28)
    
    draw.text((50, 630), "RISCO POR RUA", font=f_titulo, fill=COR_PRETO)
    draw.text((50, 700), f"Nível: {dados_rio['nivel_cm']:.0f} cm", font=f_subtitulo, fill=COR_PRETO)
    
    # --- CONFIGURAÇÃO OTIMIZADA ---
    y_start = 770       # Subimos um pouco (era 800) para caber mais
    espacamento = 75    # Espaço compacto confirmado
    altura_barra = 25   
    
    # Agora exibe as TOP 16 ruas
    lista_ordenada = sorted(lista_ruas, key=lambda k: k['percentual'], reverse=True)[:16]
    
    for i, item in enumerate(lista_ordenada):
        y = y_start + (i * espacamento)
        pct = item['percentual']
        
        # Cores e Barras
        draw.rectangle([50, y+35, 1030, y+35+altura_barra], fill=(220, 220, 220)) # Fundo
        
        cor = COR_VERDE
        if pct > 50: cor = COR_AMARELO
        if pct > 80: cor = COR_VERMELHO
        
        largura = int(980 * (pct/100))
        if largura > 980: largura = 980
        if largura < 0: largura = 0
        
        if largura > 0:
            draw.rectangle([50, y+35, 50+largura, y+35+altura_barra], fill=cor) # Progresso
            
        # Textos
        draw.text((50, y), item['nome'], font=f_item, fill=COR_PRETO)
        draw.text((950, y), f"{int(pct)}%", font=f_item, fill=cor)

    _rodape(draw)
    path = PASTA_OUTPUT / "2_placar.png"
    img.save(path)
    return str(path)

# 3. COMPARATIVO
def gerar_comparativo(dados_rio):
    img = _base_imagem()
    draw = ImageDraw.Draw(img)
    nivel = dados_rio['nivel_cm']
    pico = 960
    
    f_titulo = carregar_fonte(CAMINHO_FONTE_BOLD, 60)
    f_sub = carregar_fonte(CAMINHO_FONTE_REGULAR, 40)
    f_bold_pq = carregar_fonte(CAMINHO_FONTE_BOLD, 40)
    
    draw.text((50, 630), "COMPARATIVO", font=f_titulo, fill=COR_PRETO)
    draw.text((50, 730), "Hoje vs. Pico 2022", font=f_sub, fill=COR_PRETO)
    
    base_y, topo_y = 1650, 900
    altura_total = base_y - topo_y
    
    # Barra Histórica
    draw.rectangle([200, topo_y, 400, base_y], fill=(200, 200, 200))
    draw.text((200, base_y+20), "PICO 2022", font=f_bold_pq, fill=COR_PRETO)
    draw.text((240, topo_y-60), f"{pico}cm", font=f_bold_pq, fill=COR_PRETO)
    
    # Barra Atual
    ratio = nivel / pico
    if ratio > 1.1: ratio = 1.1 
    
    altura_atual = ratio * altura_total
    y_topo_atual = base_y - altura_atual
    if y_topo_atual < topo_y: y_topo_atual = topo_y - 50 
    if y_topo_atual > base_y: y_topo_atual = base_y
    
    cor = (52, 152, 219) 
    if nivel > 650: cor = COR_LARANJA
    if nivel > 786: cor = COR_VERMELHO
    
    draw.rectangle([600, y_topo_atual, 800, base_y], fill=cor)
    draw.text((600, base_y+20), "HOJE", font=f_bold_pq, fill=COR_PRETO)
    draw.text((640, y_topo_atual-60), f"{nivel:.0f}cm", font=f_bold_pq, fill=cor)

    _rodape(draw)
    path = PASTA_OUTPUT / "3_comparativo.png"
    img.save(path)
    return str(path)

def gerar_todas_imagens(dados_rio, lista_ruas, tendencia):
    print("--- 🎨 Iniciando Geração de Imagens ---")
    c1 = gerar_capa(dados_rio, tendencia)
    c2 = gerar_placar(dados_rio, lista_ruas)
    c3 = gerar_comparativo(dados_rio)
    return [c1, c2, c3]