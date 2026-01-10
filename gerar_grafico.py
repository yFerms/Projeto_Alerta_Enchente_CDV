import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from PIL import Image

def criar_grafico_linha(historico_recente):
    """
    Gera um gráfico de linha transparente com os dados recentes.
    Retorna: Objeto PIL Image
    """
    if not historico_recente or len(historico_recente) < 2:
        return None

    # 1. Preparar dados (Ordena do mais antigo para o mais novo)
    dados_ordenados = sorted(historico_recente, key=lambda x: x['data'])
    
    # Pega apenas as últimas 12 ou 24 leituras para não poluir
    dados_corte = dados_ordenados[-24:] 
    
    datas = [d['data'] for d in dados_corte]
    niveis = [d['nivel'] for d in dados_corte]

    # 2. Configurar Estilo (Clean/Dark)
    plt.style.use('dark_background')
    # Tamanho em polegadas (Wide para caber na tela vertical)
    fig, ax = plt.subplots(figsize=(8, 3), dpi=120) 
    
    # Fundo transparente total
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    # 3. Desenhar a Linha (Ciano Neon)
    cor_linha = '#00E5FF' # Ciano
    ax.plot(datas, niveis, color=cor_linha, linewidth=4, marker='o', markersize=6, markerfacecolor='white')
    
    # Preenchimento suave abaixo da linha
    ax.fill_between(datas, niveis, min(niveis) - 50, color=cor_linha, alpha=0.15)

    # 4. Formatação dos Eixos
    # X (Datas)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Hh'))
    ax.tick_params(axis='x', colors='white', labelsize=12, rotation=0)
    
    # Y (Níveis)
    ax.tick_params(axis='y', colors='white', labelsize=12)
    
    # Remover bordas (caixa)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('white')
    ax.spines['bottom'].set_linewidth(2)
    
    # Grade suave horizontal
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # Ajuste de escala (foca na variação)
    margem = (max(niveis) - min(niveis)) * 0.2
    if margem < 10: margem = 10
    ax.set_ylim(min(niveis) - margem, max(niveis) + margem)

    plt.tight_layout()

    # 5. Salvar em memória e retornar imagem
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    plt.close('all')
    
    return Image.open(buf)