from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES DE CORES
# ==============================================================================
COR_BRANCA = (255, 255, 255)
COR_CINZA_CLARO = (200, 200, 200) # Para o número da casa
COR_NORMAL = (46, 204, 113)
COR_ATENCAO = (241, 196, 15)
COR_ALERTA = (230, 126, 34)
COR_PERIGO = (231, 76, 60)
COR_INUNDACAO = (142, 68, 173)
COR_VAZANTE = (0, 150, 136)

def obter_cor_fundo(nivel, em_recessao):
    if em_recessao and nivel < 900: return COR_VAZANTE
    if nivel < 400: return COR_NORMAL
    if nivel < 600: return COR_ATENCAO
    if nivel < 760: return COR_ALERTA
    if nivel < 900: return COR_PERIGO
    return COR_INUNDACAO

def obter_texto_situacao(nivel, em_recessao):
    if em_recessao and nivel < 900: return "NÍVEL BAIXANDO"
    if nivel < 400: return "NÍVEL NORMAL"
    if nivel < 600: return "ATENÇÃO"
    if nivel < 760: return "ALERTA DE CHEIA"
    if nivel < 900: return "PERIGO: INUNDAÇÃO"
    return "CATASTRÓFICO"

# ==============================================================================
# FUNÇÃO 1: GERAR CAPA UNIFICADA
# ==============================================================================
def gerar_capa(dados_rio, tendencia, hist_2020, hist_2022, velocidade, em_recessao):
    nivel = dados_rio['nivel_cm']
    data_leitura = dados_rio['data_leitura']
    largura, altura = 1080, 1920
    cor_fundo = obter_cor_fundo(nivel, em_recessao)
    img = Image.new('RGB', (largura, altura), color=cor_fundo)
    draw = ImageDraw.Draw(img)

    try:
        font_titulo = ImageFont.truetype("arial.ttf", 100)
        font_nivel = ImageFont.truetype("arialbd.ttf", 250)
        font_tendencia = ImageFont.truetype("arial.ttf", 80)
        font_hist_valor = ImageFont.truetype("arial.ttf", 70)
        font_hist_titulo = ImageFont.truetype("arialbd.ttf", 60)
        font_rodape = ImageFont.truetype("arial.ttf", 40)
    except:
        font_titulo = ImageFont.load_default()
        font_nivel = ImageFont.load_default()
        font_tendencia = ImageFont.load_default()
        font_hist_valor = ImageFont.load_default()
        font_hist_titulo = ImageFont.load_default()
        font_rodape = ImageFont.load_default()

    situacao = obter_texto_situacao(nivel, em_recessao)
    w = draw.textlength(situacao, font=font_titulo)
    draw.text(((largura-w)/2, 150), situacao, font=font_titulo, fill=COR_BRANCA)

    texto_nivel = f"{nivel:.0f} cm"
    w = draw.textlength(texto_nivel, font=font_nivel)
    draw.text(((largura-w)/2, 350), texto_nivel, font=font_nivel, fill=COR_BRANCA)
    
    w = draw.textlength(tendencia, font=font_tendencia)
    draw.text(((largura-w)/2, 600), tendencia, font=font_tendencia, fill=COR_BRANCA)

    texto_vel = f"({velocidade})"
    w = draw.textlength(texto_vel, font=font_hist_valor)
    draw.text(((largura-w)/2, 700), texto_vel, font=font_hist_valor, fill=COR_BRANCA)

    draw.line([(100, 800), (980, 800)], fill=COR_BRANCA, width=5)

    titulo_hist = "COMPARATIVO (Mesma data/hora):"
    w = draw.textlength(titulo_hist, font=font_hist_titulo)
    draw.text(((largura-w)/2, 850), titulo_hist, font=font_hist_titulo, fill=COR_BRANCA)

    texto_2022 = f"Em 2022: {hist_2022} cm"
    w = draw.textlength(texto_2022, font=font_hist_valor)
    draw.text(((largura-w)/2, 950), texto_2022, font=font_hist_valor, fill=COR_BRANCA)

    texto_2020 = f"Em 2020: {hist_2020} cm"
    w = draw.textlength(texto_2020, font=font_hist_valor)
    draw.text(((largura-w)/2, 1050), texto_2020, font=font_hist_valor, fill=COR_BRANCA)

    texto_data = f"Atualizado: {data_leitura.strftime('%d/%m %H:%M')}"
    w = draw.textlength(texto_data, font=font_rodape)
    draw.text(((largura-w)/2, 1800), texto_data, font=font_rodape, fill=COR_BRANCA)

    caminho = "output/capa_unificada.png"
    if not os.path.exists("output"): os.makedirs("output")
    img.save(caminho)
    return caminho

# ==============================================================================
# FUNÇÃO 2: GERAR PLACAR PAGINADO (VERSÃO COMPACTA - 8 POR PAGINA)
# ==============================================================================
def gerar_placares_paginados(risco_ruas):
    """
    Gera imagens paginadas. 
    Meta: Caber tudo em 2 imagens (até 16 itens).
    """
    ITENS_POR_PAGINA = 13  # Compacto
    ESPACO_VERTICAL = 120 # Compacto
    
    paginas = [risco_ruas[i:i + ITENS_POR_PAGINA] for i in range(0, len(risco_ruas), ITENS_POR_PAGINA)]
    
    caminhos_gerados = []

    try:
        font_titulo = ImageFont.truetype("arialbd.ttf", 70)
        font_nome_rua = ImageFont.truetype("arialbd.ttf", 45)
        font_detalhe = ImageFont.truetype("arial.ttf", 40)
        font_pct = ImageFont.truetype("arialbd.ttf", 50)
    except:
        font_titulo = ImageFont.load_default()
        font_nome_rua = ImageFont.load_default()
        font_detalhe = ImageFont.load_default()
        font_pct = ImageFont.load_default()

    for i, ruas_pagina in enumerate(paginas):
        largura, altura = 1080, 1920
        img = Image.new('RGB', (largura, altura), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)

        # Cabeçalho
        titulo = f"SITUAÇÃO DAS RUAS ({i+1}/{len(paginas)})"
        draw.text((50, 100), titulo, font=font_titulo, fill=COR_BRANCA)
        draw.line([(50, 190), (1030, 190)], fill=COR_BRANCA, width=3)

        y_pos = 230
        
        for rua in ruas_pagina:
            nome_principal = rua['nome']
            detalhe_numero = rua['apelido']
            pct = rua['porcentagem']
            
            # Cores
            cor_barra = COR_NORMAL
            if pct > 50: cor_barra = COR_ATENCAO
            if pct > 80: cor_barra = COR_ALERTA
            if pct >= 100: cor_barra = COR_PERIGO

            # AQUI ESTAVA O CORTE! AGORA ESTÁ COMPLETO:
            
            # 1. Nome da Rua (Negrito)
            draw.text((50, y_pos), nome_principal, font=font_nome_rua, fill=COR_BRANCA)
            
            # 2. Números (Mais perto do nome agora)
            draw.text((50, y_pos + 50), detalhe_numero, font=font_detalhe, fill=COR_CINZA_CLARO)

            # 3. Barra de Progresso
            draw.rectangle([(600, y_pos + 15), (900, y_pos + 55)], fill=(60,60,60))
            
            pct_visual = min(pct, 100.0)
            largura_barra = (pct_visual / 100) * 300
            draw.rectangle([(600, y_pos + 15), (600 + largura_barra, y_pos + 55)], fill=cor_barra)
            
            # 4. Porcentagem
            draw.text((920, y_pos + 5), f"{pct:.0f}%", font=font_pct, fill=cor_barra)

            # Próxima linha
            y_pos += ESPACO_VERTICAL 

        # Rodapé indicativo (Só aparece se não for a última página)
        if i < len(paginas) - 1:
            draw.text((350, 1800), "Continua no próximo story... ➡️", font=font_detalhe, fill=COR_BRANCA)

        nome_arquivo = f"output/placar_ruas_parte_{i+1}.png"
        img.save(nome_arquivo)
        caminhos_gerados.append(nome_arquivo)

    return caminhos_gerados

# ==============================================================================
# ORQUESTRADOR FINAL
# ==============================================================================
def gerar_todas_imagens(dados_rio, dados_ruas, tendencia, h2020, h2022, velocidade, em_recessao=False):
    # 1. Gera Capa
    caminho_capa = gerar_capa(dados_rio, tendencia, h2020, h2022, velocidade, em_recessao)
    
    # 2. Gera Placares (Pode retornar lista com várias imagens)
    lista_placares = gerar_placares_paginados(dados_ruas)
    
    # Retorna lista única: [Capa, Placar1, Placar2...]
    return [caminho_capa] + lista_placares