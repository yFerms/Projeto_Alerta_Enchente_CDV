from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

# Importa o gerador de gráfico
from gerar_grafico import criar_grafico_linha

# ==============================================================================
# CONFIGURAÇÕES DE CORES
# ==============================================================================
COR_BRANCA = (255, 255, 255)
COR_AMARELO_IA = (255, 221, 0)
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
# FUNÇÃO 1: GERAR CAPA (COM GRÁFICO)
# ==============================================================================
def gerar_capa(dados_rio, tendencia, historico_dict, velocidade, em_recessao, texto_previsao=None, dados_grafico=None):
    nivel = dados_rio['nivel_cm']
    data_leitura = dados_rio['data_leitura']
    largura, altura = 1080, 1920
    cor_fundo = obter_cor_fundo(nivel, em_recessao)
    img = Image.new('RGB', (largura, altura), color=cor_fundo)
    draw = ImageDraw.Draw(img)

    try:
        font_titulo = ImageFont.truetype("arial.ttf", 90)
        font_nivel = ImageFont.truetype("arialbd.ttf", 220)
        font_tendencia = ImageFont.truetype("arial.ttf", 70)
        font_velocidade = ImageFont.truetype("arial.ttf", 60)
        font_previsao = ImageFont.truetype("arialbd.ttf", 65) 
        font_hist_titulo = ImageFont.truetype("arialbd.ttf", 50)
        font_hist_valor = ImageFont.truetype("arial.ttf", 55) 
        font_rodape = ImageFont.truetype("arial.ttf", 35)
    except:
        font_titulo = ImageFont.load_default()
        # ... fallback simples ...
        font_nivel = ImageFont.load_default()
        font_tendencia = ImageFont.load_default()
        font_velocidade = ImageFont.load_default()
        font_previsao = ImageFont.load_default()
        font_hist_titulo = ImageFont.load_default()
        font_hist_valor = ImageFont.load_default()
        font_rodape = ImageFont.load_default()

    # 1. Situação (Topo)
    situacao = obter_texto_situacao(nivel, em_recessao)
    w = draw.textlength(situacao, font=font_titulo)
    draw.text(((largura-w)/2, 120), situacao, font=font_titulo, fill=COR_BRANCA)

    # 2. Nível Gigante
    texto_nivel = f"{nivel:.0f} cm"
    w = draw.textlength(texto_nivel, font=font_nivel)
    draw.text(((largura-w)/2, 280), texto_nivel, font=font_nivel, fill=COR_BRANCA)
    
    # 3. Tendência e Velocidade
    w_tend = draw.textlength(tendencia, font=font_tendencia)
    draw.text(((largura-w_tend)/2, 530), tendencia, font=font_tendencia, fill=COR_BRANCA)
    
    texto_vel = f"({velocidade})"
    w_vel = draw.textlength(texto_vel, font=font_velocidade)
    draw.text(((largura-w_vel)/2, 610), texto_vel, font=font_velocidade, fill=COR_BRANCA)

    # 4. Previsão IA
    y_cursor = 700
    if texto_previsao:
        w = draw.textlength(texto_previsao, font=font_previsao)
        draw.text(((largura-w)/2, y_cursor), texto_previsao, font=font_previsao, fill=COR_AMARELO_IA)
        y_cursor += 100

    # 5. GRÁFICO (NOVO)
    # Gera o gráfico na memória e cola na imagem
    if dados_grafico:
        try:
            img_grafico = criar_grafico_linha(dados_grafico)
            if img_grafico:
                # Centralizar o gráfico
                largura_g, altura_g = img_grafico.size
                pos_x_g = (largura - largura_g) // 2
                pos_y_g = y_cursor
                
                # Cola o gráfico sobre o fundo (o terceiro parâmetro é a máscara de transparência)
                img.paste(img_grafico, (pos_x_g, pos_y_g), img_grafico)
                y_cursor += altura_g + 20
        except Exception as e:
            print(f"Erro ao plotar gráfico: {e}")

    # Linha Divisória
    y_linha = y_cursor + 20
    draw.line([(100, y_linha), (980, y_linha)], fill=COR_BRANCA, width=4)

    # 6. Histórico Comparativo
    y_hist = y_linha + 50
    titulo_hist = "COMPARATIVO (Mesma data):"
    w = draw.textlength(titulo_hist, font=font_hist_titulo)
    draw.text(((largura-w)/2, y_hist), titulo_hist, font=font_hist_titulo, fill=COR_BRANCA)

    y_inicial_lista = y_hist + 80
    espaco_linha = 65
    
    anos = sorted(historico_dict.keys()) 
    for i, ano in enumerate(anos):
        valor = historico_dict[ano]
        texto = f"{ano}: {valor} cm"
        w = draw.textlength(texto, font=font_hist_valor)
        draw.text(((largura-w)/2, y_inicial_lista + (i * espaco_linha)), texto, font=font_hist_valor, fill=COR_BRANCA)

    # 7. Rodapé
    texto_data = f"Atualizado: {data_leitura.strftime('%d/%m %H:%M')}"
    w = draw.textlength(texto_data, font=font_rodape)
    draw.text(((largura-w)/2, 1820), texto_data, font=font_rodape, fill=COR_BRANCA)

    caminho = "output/capa_unificada.png"
    if not os.path.exists("output"): os.makedirs("output")
    img.save(caminho)
    return caminho

def gerar_placares_paginados(risco_ruas):
    # Mantive igual, apenas copiei para o arquivo ficar completo
    ITENS_POR_PAGINA = 14
    ESPACO_VERTICAL = 115
    paginas = [risco_ruas[i:i + ITENS_POR_PAGINA] for i in range(0, len(risco_ruas), ITENS_POR_PAGINA)]
    caminhos_gerados = []
    COR_BRANCA = (255, 255, 255)
    COR_CINZA_CLARO = (200, 200, 200)
    COR_NORMAL = (46, 204, 113)
    COR_ATENCAO = (241, 196, 15)
    COR_ALERTA = (230, 126, 34)
    COR_PERIGO = (231, 76, 60)

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

def gerar_todas_imagens(dados_rio, dados_ruas, tendencia, historico_dict, velocidade, em_recessao=False, texto_previsao=None, dados_grafico=None):
    caminho_capa = gerar_capa(dados_rio, tendencia, historico_dict, velocidade, em_recessao, texto_previsao, dados_grafico)
    lista_placares = gerar_placares_paginados(dados_ruas)
    return [caminho_capa] + lista_placares