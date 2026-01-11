import os
import io
import sqlite3
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES DE CAMINHOS E CORES
# ==============================================================================
PASTA_ASSETS = "assets"
PASTA_OUTPUT = "output"

# Fontes (Certifique-se que os arquivos existem na pasta assets)
FONTE_BOLD = os.path.join(PASTA_ASSETS, "Roboto-Bold.ttf")
FONTE_REGULAR = os.path.join(PASTA_ASSETS, "Roboto-Regular.ttf")

# Cores do Sistema
COR_BRANCA = (255, 255, 255)
COR_CINZA_CLARO = (200, 200, 200)
COR_NORMAL = (46, 204, 113)
COR_ATENCAO = (241, 196, 15)
COR_ALERTA = (230, 126, 34)
COR_PERIGO = (231, 76, 60)

if not os.path.exists(PASTA_OUTPUT):
    os.makedirs(PASTA_OUTPUT)

# ==============================================================================
# FUNÇÕES DE APOIO
# ==============================================================================


def obter_caminho_base(nivel):
    """Seleciona a imagem de fundo baseada nos limites críticos conforme sua arte"""
    if nivel < 400:
        return os.path.join(PASTA_ASSETS, "capa_verde.png")
    elif nivel < 600:
        return os.path.join(PASTA_ASSETS, "capa_amarela.png")
    else:
        return os.path.join(PASTA_ASSETS, "capa_vermelha.png")

# ==============================================================================
# FUNÇÃO DE APOIO: GERADOR DE GRÁFICO (AJUSTADO PARA 25 PONTOS)
# ==============================================================================


def gerar_grafico_transparente(dados_historicos):
    """Gera o gráfico de linha transparente com melhor espaçamento para 25 pontos"""
    if not dados_historicos:
        return None

    # Extração dos dados
    horas = [d['hora'] for d in dados_historicos]
    niveis = [d['nivel'] for d in dados_historicos]

    # Criar a figura (Aumentamos um pouco a largura para caber mais pontos)
    fig, ax = plt.subplots(figsize=(7.0, 3.0))

    # Plotagem: Linha mais fina e pontos menores para não poluir com 25 registros
    ax.plot(horas, niveis, color='white', linewidth=2,
            marker='o', markersize=4, markerfacecolor='white')

    # CONFIGURAÇÃO DO EIXO X (Pular etiquetas para não sobrepor)
    # Mostra a hora apenas de 4 em 4 pontos (ex: de hora em hora)
    for i, label in enumerate(ax.get_xticklabels()):
        if i % 4 != 0 and i != len(horas) - 1:
            label.set_visible(False)

    # Estilização Transparente
    ax.set_facecolor('none')
    fig.patch.set_alpha(0)
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='both', colors='white', labelsize=11)
    ax.grid(True, linestyle='--', alpha=0.2, color='white')

    # Salva em memória
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True,
                bbox_inches='tight', dpi=120)
    plt.close('all')
    buf.seek(0)
    return Image.open(buf).convert("RGBA")

# ==============================================================================
# FUNÇÃO 1: GERAR CAPA (ATUALIZADA PARA 25 LEITURAS)
# ==============================================================================


def gerar_capa(dados_rio, tendencia, historico_dict, velocidade, em_recessao, texto_previsao=None, dados_grafico=None):
    nivel = dados_rio['nivel_cm']
    caminho_base = obter_caminho_base(nivel)

    try:
        imagem = Image.open(caminho_base).convert("RGBA")
    except:
        imagem = Image.new('RGB', (1080, 1920), color=(30, 30, 30))

    draw = ImageDraw.Draw(imagem)
    centro_x = imagem.width // 2

    # ... (Carregamento de fontes e Elementos 1, 2, 3 e 4 permanecem iguais) ...
    # [Mantendo o código das fontes e textos anteriores para brevidade]
    try:
        fonte_nivel = ImageFont.truetype(FONTE_BOLD, 130)
        fonte_status = ImageFont.truetype(FONTE_BOLD, 50)
        fonte_velocidade = ImageFont.truetype(FONTE_REGULAR, 50)
        fonte_previsao = ImageFont.truetype(FONTE_BOLD, 53)
        fonte_rodape = ImageFont.truetype(FONTE_REGULAR, 35)
    except:
        fonte_nivel = fonte_status = fonte_velocidade = fonte_previsao = fonte_rodape = ImageFont.load_default()

    draw.text((centro_x, 450), f"{int(nivel)} cm",
              font=fonte_nivel, fill=COR_BRANCA, anchor="mm")
    draw.text((centro_x, 580), f"{tendencia.upper()}",
              font=fonte_status, fill=COR_BRANCA, anchor="mm")
    draw.text((centro_x, 640), f"({velocidade})",
              font=fonte_velocidade, fill=COR_BRANCA, anchor="mm")
    txt_prev = texto_previsao if texto_previsao else f"Prev. +1h: {int(nivel)} cm"
    draw.text((centro_x, 760), txt_prev, font=fonte_previsao,
              fill=(0, 0, 0), anchor="mm")

    # ELEMENTO 5: GRÁFICO
    if dados_grafico:
        # Pegamos as últimas 15 leituras para o gráfico
        # Invertemos para que o gráfico flua da esquerda (passado) para a direita (atual)
        fatia_grafico = dados_grafico[:20]
        hist_graf = [{'hora': d['data'].strftime(
            '%H:%M'), 'nivel': d['nivel']} for d in fatia_grafico]
        hist_graf.reverse()

        graf_img = gerar_grafico_transparente(hist_graf)
        if graf_img:
            # Ajuste leve na posição Y para acomodar o gráfico maior
            pos_x = (imagem.width - graf_img.width) // 2
            imagem.paste(graf_img, (pos_x, 920), graf_img)

    # ... (Restante do Histórico e Rodapé permanecem iguais) ...
    pos_x_esq, pos_x_dir = 350, 840
    pos_y_l1, pos_y_l2 = 1530, 1750

    def fmt_h(ano):
        val = historico_dict.get(int(ano), "---")
        return f"{ano}:\n{val} cm"

    draw.text((pos_x_esq, pos_y_l1), fmt_h("2020"), font=fonte_previsao,
              fill=COR_BRANCA, anchor="mm", align="center")
    draw.text((pos_x_esq, pos_y_l2), fmt_h("2021"), font=fonte_previsao,
              fill=COR_BRANCA, anchor="mm", align="center")
    draw.text((pos_x_dir, pos_y_l1), fmt_h("2022"), font=fonte_previsao,
              fill=COR_BRANCA, anchor="mm", align="center")
    draw.text((pos_x_dir, pos_y_l2), fmt_h("2023"), font=fonte_previsao,
              fill=COR_BRANCA, anchor="mm", align="center")
    dt_atual = dados_rio['data_leitura'].strftime("%d/%m/%Y às %H:%M")
    draw.text((centro_x, imagem.height - 35),
              f"Atualizado: {dt_atual}", font=fonte_rodape, fill=COR_CINZA_CLARO, anchor="mm")

    caminho = os.path.join(PASTA_OUTPUT, "capa_final.png")
    imagem.save(caminho)
    return caminho

# ==============================================================================
# FUNÇÃO 2: GERAR PLACARES DAS RUAS (PAGINADOS)
# ==============================================================================


def gerar_placares_paginados(risco_ruas):
    ITENS_POR_PAGINA = 14
    ESPACO_VERTICAL = 115
    paginas = [risco_ruas[i:i + ITENS_POR_PAGINA]
               for i in range(0, len(risco_ruas), ITENS_POR_PAGINA)]
    caminhos_gerados = []

    try:
        font_titulo = ImageFont.truetype(FONTE_BOLD, 70)
        font_nome_rua = ImageFont.truetype(FONTE_BOLD, 45)
        font_detalhe = ImageFont.truetype(FONTE_REGULAR, 40)
        font_pct = ImageFont.truetype(FONTE_BOLD, 50)
    except:
        font_titulo = font_nome_rua = font_detalhe = font_pct = ImageFont.load_default()

    for i, ruas_pagina in enumerate(paginas):
        largura, altura = 1080, 1920
        img = Image.new('RGB', (largura, altura), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)

        # DEFINIÇÃO DO CENTRO_X PARA ESTA FUNÇÃO
        centro_x = largura // 2

        titulo = "SITUAÇÃO DAS RUAS" if len(
            paginas) == 1 else f"SITUAÇÃO DAS RUAS ({i+1}/{len(paginas)})"
        draw.text((50, 100), titulo, font=font_titulo, fill=COR_BRANCA)
        draw.line([(50, 190), (1030, 190)], fill=COR_BRANCA, width=3)

        y_pos = 220
        for rua in ruas_pagina:
            nome_p = rua['nome']
            detalhe = rua.get('apelido', '')
            pct = rua['porcentagem']

            cor_b = COR_NORMAL
            if pct > 50:
                cor_b = COR_ATENCAO
            if pct > 80:
                cor_b = COR_ALERTA
            if pct >= 100:
                cor_b = COR_PERIGO

            draw.text((50, y_pos), nome_p, font=font_nome_rua, fill=COR_BRANCA)
            draw.text((50, y_pos + 45), detalhe,
                      font=font_detalhe, fill=COR_CINZA_CLARO)

            draw.rectangle(
                [(600, y_pos + 15), (900, y_pos + 55)], fill=(60, 60, 60))
            largura_b = (min(pct, 100) / 100) * 300
            draw.rectangle(
                [(600, y_pos + 15), (600 + largura_b, y_pos + 55)], fill=cor_b)

            draw.text((920, y_pos + 5),
                      f"{pct:.0f}%", font=font_pct, fill=cor_b)
            y_pos += ESPACO_VERTICAL

        # Correção aqui: centro_x agora existe neste escopo
        if i < len(paginas) - 1:
            draw.text((centro_x, 1850), "Continua no próximo story... ➡️",
                      font=font_detalhe, fill=COR_BRANCA, anchor="mm")

        caminho = os.path.join(PASTA_OUTPUT, f"placar_ruas_parte_{i+1}.png")
        img.save(caminho)
        caminhos_gerados.append(caminho)

    return caminhos_gerados

# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================


def gerar_todas_imagens(dados_rio, dados_ruas, tendencia, historico_dict, velocidade, em_recessao=False, texto_previsao=None, dados_grafico=None):
    caminho_capa = gerar_capa(dados_rio, tendencia, historico_dict,
                              velocidade, em_recessao, texto_previsao, dados_grafico)
    lista_placares = gerar_placares_paginados(dados_ruas)
    return [caminho_capa] + lista_placares
