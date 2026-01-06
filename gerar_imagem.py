from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES DE CORES
# ==============================================================================
COR_BRANCA = (255, 255, 255)
COR_CINZA_CLARO = (200, 200, 200)
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
# FUNÇÃO 1: GERAR CAPA (LISTA VERTICAL 2020-2025)
# ==============================================================================
def gerar_capa(dados_rio, tendencia, historico_dict, velocidade, em_recessao):
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
        font_velocidade = ImageFont.truetype("arial.ttf", 70)
        font_hist_titulo = ImageFont.truetype("arialbd.ttf", 60)
        # Fonte ajustada para a lista vertical
        font_hist_valor = ImageFont.truetype("arial.ttf", 65) 
        font_rodape = ImageFont.truetype("arial.ttf", 40)
    except:
        font_titulo = ImageFont.load_default()
        font_nivel = ImageFont.load_default()
        font_tendencia = ImageFont.load_default()
        font_velocidade = ImageFont.load_default()
        font_hist_titulo = ImageFont.load_default()
        font_hist_valor = ImageFont.load_default()
        font_rodape = ImageFont.load_default()

    # 1. Situação
    situacao = obter_texto_situacao(nivel, em_recessao)
    w = draw.textlength(situacao, font=font_titulo)
    draw.text(((largura-w)/2, 150), situacao, font=font_titulo, fill=COR_BRANCA)

    # 2. Nível Gigante
    texto_nivel = f"{nivel:.0f} cm"
    w = draw.textlength(texto_nivel, font=font_nivel)
    draw.text(((largura-w)/2, 350), texto_nivel, font=font_nivel, fill=COR_BRANCA)
    
    # 3. Tendência
    w = draw.textlength(tendencia, font=font_tendencia)
    draw.text(((largura-w)/2, 600), tendencia, font=font_tendencia, fill=COR_BRANCA)

    # 4. Velocidade
    texto_vel = f"({velocidade})"
    w = draw.textlength(texto_vel, font=font_velocidade)
    draw.text(((largura-w)/2, 700), texto_vel, font=font_velocidade, fill=COR_BRANCA)

    draw.line([(100, 800), (980, 800)], fill=COR_BRANCA, width=5)

    # 5. Histórico (Layout Vertical Centralizado)
    titulo_hist = "COMPARATIVO (Mesma data):"
    w = draw.textlength(titulo_hist, font=font_hist_titulo)
    draw.text(((largura-w)/2, 850), titulo_hist, font=font_hist_titulo, fill=COR_BRANCA)

    y_inicial = 980      # Começa logo abaixo do título
    espaco_linha = 110   # Espaçamento generoso para ficar legível
    
    # Ordena os anos (2020, 2021...) para garantir a sequência
    anos = sorted(historico_dict.keys()) 
    
    for i, ano in enumerate(anos):
        valor = historico_dict[ano]
        texto = f"{ano}: {valor} cm"
        
        # Centraliza cada linha
        w = draw.textlength(texto, font=font_hist_valor)
        x_pos = (largura - w) / 2
        y_pos = y_inicial + (i * espaco_linha)
        
        draw.text((x_pos, y_pos), texto, font=font_hist_valor, fill=COR_BRANCA)

    # 6. Rodapé
    texto_data = f"Atualizado: {data_leitura.strftime('%d/%m %H:%M')}"
    w = draw.textlength(texto_data, font=font_rodape)
    draw.text(((largura-w)/2, 1800), texto_data, font=font_rodape, fill=COR_BRANCA)

    caminho = "output/capa_unificada.png"
    if not os.path.exists("output"): os.makedirs("output")
    img.save(caminho)
    return caminho

# ==============================================================================
# FUNÇÃO 2: GERAR PLACAR (MANTIDO PADRÃO)
# ==============================================================================
def gerar_placares_paginados(risco_ruas):
    ITENS_POR_PAGINA = 14
    ESPACO_VERTICAL = 115
    
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

        titulo = "SITUAÇÃO DAS RUAS" if len(paginas) == 1 else f"SITUAÇÃO DAS RUAS ({i+1}/{len(paginas)})"
            
        draw.text((50, 100), titulo, font=font_titulo, fill=COR_BRANCA)
        draw.line([(50, 190), (1030, 190)], fill=COR_BRANCA, width=3)

        y_pos = 220
        for rua in ruas_pagina:
            nome_principal = rua['nome']
            detalhe_numero = rua['apelido']
            pct = rua['porcentagem']
            
            cor_barra = COR_NORMAL
            if pct > 50: cor_barra = COR_ATENCAO
            if pct > 80: cor_barra = COR_ALERTA
            if pct >= 100: cor_barra = COR_PERIGO

            draw.text((50, y_pos), nome_principal, font=font_nome_rua, fill=COR_BRANCA)
            draw.text((50, y_pos + 45), detalhe_numero, font=font_detalhe, fill=COR_CINZA_CLARO)

            draw.rectangle([(600, y_pos + 15), (900, y_pos + 55)], fill=(60,60,60))
            pct_visual = min(pct, 100.0)
            largura_barra = (pct_visual / 100) * 300
            draw.rectangle([(600, y_pos + 15), (600 + largura_barra, y_pos + 55)], fill=cor_barra)
            draw.text((920, y_pos + 5), f"{pct:.0f}%", font=font_pct, fill=cor_barra)

            y_pos += ESPACO_VERTICAL 

        if i < len(paginas) - 1:
            draw.text((350, 1800), "Continua no próximo story... ➡️", font=font_detalhe, fill=COR_BRANCA)

        nome_arquivo = f"output/placar_ruas_parte_{i+1}.png"
        img.save(nome_arquivo)
        caminhos_gerados.append(nome_arquivo)

    return caminhos_gerados

# ==============================================================================
# ORQUESTRADOR FINAL
# ==============================================================================
def gerar_todas_imagens(dados_rio, dados_ruas, tendencia, historico_dict, velocidade, em_recessao=False):
    # Passa o dicionário completo de histórico
    caminho_capa = gerar_capa(dados_rio, tendencia, historico_dict, velocidade, em_recessao)
    lista_placares = gerar_placares_paginados(dados_ruas)
    return [caminho_capa] + lista_placares