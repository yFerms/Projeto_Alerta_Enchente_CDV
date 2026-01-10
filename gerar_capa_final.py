import os
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io
from datetime import datetime

# ======================================================
# CONFIGURAÇÕES DE ARQUIVOS
# ======================================================
PASTA_ASSETS = "assets"
PASTA_OUTPUT = "output"

# Caminhos das fontes e imagens base
IMG_BASE = os.path.join(PASTA_ASSETS, "fundo_capa.png")
FONTE_BOLD = os.path.join(PASTA_ASSETS, "Roboto-Bold.ttf")
FONTE_REGULAR = os.path.join(PASTA_ASSETS, "Roboto-Regular.ttf")

def gerar_grafico_transparente(dados_historicos):
    # Extrai horas e níveis
    horas = [d['hora'] for d in dados_historicos]
    niveis = [d['nivel'] for d in dados_historicos]

    # Tamanho do gráfico em polegadas (Largura, Altura)
    fig, ax = plt.subplots(figsize=(8, 3))

    # PLOTAGEM (Linha branca com bolinhas)
    ax.plot(horas, niveis, color='white', linewidth=3, marker='o', markersize=8)
    
    # Preenchimento degradê
    ax.fill_between(horas, niveis, color='white', alpha=0.1)

    # ESTILO "CLEAN" (Remove bordas e deixa texto branco)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('white')
    
    # Cor dos textos (Eixos)
    ax.tick_params(axis='x', colors='white', labelsize=12)
    ax.tick_params(axis='y', colors='white', labelsize=12)
    
    # Fundo 100% transparente
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    
    plt.tight_layout()

    # Salva na memória RAM
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    plt.close(fig)
    
    return Image.open(buf)

def gerar_capa_final(dados):
    print("Gerando capa final...")
    if not os.path.exists(PASTA_OUTPUT):
        os.makedirs(PASTA_OUTPUT)

    nivel = dados['nivel']

    # Lógica para definir qual fundo usar baseado no nível
    if nivel >= 600:
        arquivo_fundo = "fundo_critico.png"
    elif nivel >= 450:
        arquivo_fundo = "fundo_grave.png"
    else:
        arquivo_fundo = "fundo_normal.png"

    caminho_fundo = os.path.join(PASTA_ASSETS, arquivo_fundo)

    try:
        # Abre a imagem de fundo correspondente ao nível
        imagem = Image.open(caminho_fundo).convert("RGBA")
        draw = ImageDraw.Draw(imagem)
        centro_x = imagem.width / 2

        # Carregando as fontes
        fonte_nivel = ImageFont.truetype(FONTE_BOLD, 130)
        fonte_status = ImageFont.truetype(FONTE_BOLD, 70)
        fonte_velocidade = ImageFont.truetype(FONTE_REGULAR, 50)
        fonte_previsao = ImageFont.truetype(FONTE_BOLD, 53)
        fonte_rodape = ImageFont.truetype(FONTE_REGULAR, 35)

        # ELEMENTO 1: NÍVEL
        draw.text((centro_x, 450), f"{nivel} cm", font=fonte_nivel, fill=(255, 255, 255), anchor="mm")

        # ELEMENTO 2: STATUS
        draw.text((centro_x, 580), f"{dados['status']}", font=fonte_status, fill=(255, 255, 255), anchor="mm")

        # ELEMENTO 3: VELOCIDADE
        draw.text((centro_x, 640), f"({dados['velocidade']})", font=fonte_velocidade, fill=(255, 255, 255), anchor="mm")

        # --- ELEMENTO 4: PREVISÃO (Cálculo Real) ---
        # O monitor envia a velocidade como string "+2 cm/h", 
        # garantimos que o texto da previsão use o valor calculado pelo monitor
        ajuste_direita = 40
        pos_x_final = centro_x + ajuste_direita
        
        # Se o monitor passar o valor da previsão pronto:
        texto_previsao = f"Prev. +1h: {dados['previsao']} cm"
        
        # Previsão: Pegar exatamente o que o monitor enviou
        draw.text((pos_x_final, 760), f"Prev. +1h: {dados['previsao']} cm", font=fonte_previsao, fill=(0, 0, 0), anchor="mm")
        print("Gerando gráfico...")
        grafico_img = gerar_grafico_transparente(dados['historico'])
        pos_x_grafico = int((imagem.width - grafico_img.width) / 2)
        pos_y_grafico = 940
        imagem.paste(grafico_img, (pos_x_grafico, pos_y_grafico), grafico_img)

       # --- ELEMENTO 6: COMPARATIVO HISTÓRICO ---
        # Ajustando para usar os anos que o seu monitor_definitivo.py realmente busca
        print("Posicionando dados do comparativo real...")
        pos_x_esquerda = 350
        pos_x_direita = 840
        pos_y_linha_1 = 1530 
        pos_y_linha_2 = 1750 
        
        comp = dados['comparativo']

        # Função para evitar erro se o ano não existir no dicionário
        def formatar_valor(ano):
            valor = comp.get(ano, "---") # Mostra --- se não encontrar o dado
            return f"{ano}:\n{valor} cm"

        # Organizando conforme os dados que você coleta (2020 e 2022)
        # Coluna Esquerda
        draw.text((pos_x_esquerda, pos_y_linha_1), formatar_valor("2020"), font=fonte_previsao, fill=(255, 255, 255), anchor="mm", align="center")
        draw.text((pos_x_esquerda, pos_y_linha_2), formatar_valor("2021"), font=fonte_previsao, fill=(255, 255, 255), anchor="mm", align="center")

        # Coluna Direita
        draw.text((pos_x_direita, pos_y_linha_1), formatar_valor("2022"), font=fonte_previsao, fill=(255, 255, 255), anchor="mm", align="center")
        draw.text((pos_x_direita, pos_y_linha_2), formatar_valor("2023"), font=fonte_previsao, fill=(255, 255, 255), anchor="mm", align="center")

        # ELEMENTO 7: RODAPÉ
        data_hora_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        pos_y_rodape = imagem.height - 35
        draw.text((centro_x, pos_y_rodape), f"Atualizado: {data_hora_atual}", font=fonte_rodape, fill=(200, 200, 200), anchor="mm")

        # Salva o resultado final
        caminho_salvar = os.path.join(PASTA_OUTPUT, "capa_final.png")
        imagem.save(caminho_salvar)
        print(f"Imagem salva em: {caminho_salvar}")
        return caminho_salvar

    except Exception as e:
        print(f"Erro: {e}")
        return

if __name__ == "__main__":
    print("Iniciando teste com DADOS REAIS da ANA...")
    
    # IMPORTANTE: Usando a lógica do seu monitor_definitivo
    from monitor_definitivo import buscar_dados_xml, ESTACAO_TIMOTEO
    
    leituras = buscar_dados_xml(ESTACAO_TIMOTEO)
    
    if leituras:
        nivel_atual = leituras[0]['nivel']
        # Simula o formato que o seu monitor_definitivo usa
        dados_para_teste = {
            "nivel": nivel_atual,
            "status": "NORMAL" if nivel_atual < 450 else "ALERTA",
            "velocidade": "+2 cm/h",
            "previsao": nivel_atual + 2,
            "historico": [
                {'hora': l['data'].strftime('%Hh'), 'nivel': l['nivel']} 
                for l in leituras[:6] # Pega as últimas 6
            ],
            "comparativo": {
                "2020": 213, "2021": 189, "2022": 350, "2023": 445
            }
        }
        gerar_capa_final(dados_para_teste)
    else:
        print("Não foi possível conectar à ANA. Verifique a internet.")