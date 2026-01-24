import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
ARQUIVO_TIMOTEO = "historico_timoteo.csv" # Nome do seu arquivo de Timóteo
ARQUIVO_GUILMAN = "historico_guilman.csv" # Nome do seu arquivo da Guilman

# Ajuste os nomes das colunas conforme seus arquivos CSV
# Exemplo: Se no CSV estiver "Data", mude para "Data". Se for "data_hora", mantenha.
COLUNA_DATA_TIMOTEO = "data"
COLUNA_NIVEL_TIMOTEO = "nivel"

COLUNA_DATA_GUILMAN = "data_hora"
COLUNA_VAZAO_GUILMAN = "vazao" # Ou "nivel", dependendo do que quer comparar

def gerar_grafico():
    print("⏳ Carregando dados... (Isso pode demorar um pouco)")

    # ==========================================================================
    # 2. CARREGAMENTO E LIMPEZA DE DADOS
    # ==========================================================================
    
    # --- A. Carregar Timóteo ---
    try:
        df_timoteo = pd.read_csv(ARQUIVO_TIMOTEO, sep=None, engine='python') # Tenta detectar separador auto
        # Converte a coluna de data para datetime (o Python entender que é tempo)
        df_timoteo[COLUNA_DATA_TIMOTEO] = pd.to_datetime(df_timoteo[COLUNA_DATA_TIMOTEO], dayfirst=True, errors='coerce')
        # Remove datas que falharam na conversão
        df_timoteo = df_timoteo.dropna(subset=[COLUNA_DATA_TIMOTEO])
        # Ordena por data
        df_timoteo = df_timoteo.sort_values(by=COLUNA_DATA_TIMOTEO)
        print(f"✅ Timóteo carregado: {len(df_timoteo)} registros.")
    except Exception as e:
        print(f"❌ Erro ao ler Timóteo: {e}")
        return

    # --- B. Carregar Guilman ---
    try:
        df_guilman = pd.read_csv(ARQUIVO_GUILMAN, sep=None, engine='python')
        
        # Tratamento especial para números com vírgula (padrão brasileiro)
        if df_guilman[COLUNA_VAZAO_GUILMAN].dtype == object:
            df_guilman[COLUNA_VAZAO_GUILMAN] = df_guilman[COLUNA_VAZAO_GUILMAN].astype(str).str.replace(',', '.').astype(float)
            
        df_guilman[COLUNA_DATA_GUILMAN] = pd.to_datetime(df_guilman[COLUNA_DATA_GUILMAN], dayfirst=True, errors='coerce')
        df_guilman = df_guilman.dropna(subset=[COLUNA_DATA_GUILMAN])
        df_guilman = df_guilman.sort_values(by=COLUNA_DATA_GUILMAN)
        print(f"✅ Guilman carregada: {len(df_guilman)} registros.")
    except Exception as e:
        print(f"❌ Erro ao ler Guilman: {e}")
        return

    # ==========================================================================
    # 3. PLOTAGEM (O Gráfico)
    # ==========================================================================
    print("📈 Gerando gráfico...")
    
    # Cria uma figura e um eixo principal (ax1)
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # --- EIXO 1 (ESQUERDA): TIMÓTEO (Nível em cm) ---
    cor_timoteo = 'tab:blue'
    ax1.set_xlabel('Data/Ano')
    ax1.set_ylabel('Nível Timóteo (cm)', color=cor_timoteo, fontsize=12, fontweight='bold')
    ax1.plot(df_timoteo[COLUNA_DATA_TIMOTEO], df_timoteo[COLUNA_NIVEL_TIMOTEO], color=cor_timoteo, linewidth=1, label='Timóteo (Nível)')
    ax1.tick_params(axis='y', labelcolor=cor_timoteo)
    ax1.grid(True, linestyle='--', alpha=0.5)

    # --- EIXO 2 (DIREITA): GUILMAN (Vazão em m³/s) ---
    # Criamos um eixo "gêmeo" que compartilha a mesma data (X) mas tem escala diferente (Y)
    ax2 = ax1.twinx()  
    cor_guilman = 'tab:red'
    ax2.set_ylabel('Vazão Guilman (m³/s)', color=cor_guilman, fontsize=12, fontweight='bold')
    ax2.plot(df_guilman[COLUNA_DATA_GUILMAN], df_guilman[COLUNA_VAZAO_GUILMAN], color=cor_guilman, linewidth=1, linestyle='-', alpha=0.7, label='Guilman (Vazão)')
    ax2.tick_params(axis='y', labelcolor=cor_guilman)

    # --- DETALHES FINAIS ---
    plt.title('Comparativo Histórico: Nível Timóteo x Vazão Guilman', fontsize=14)
    
    # Formatação das datas no eixo X (Mostra Ano-Mês)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    
    # Adiciona legenda combinada
    linhas_1, labels_1 = ax1.get_legend_handles_labels()
    linhas_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(linhas_1 + linhas_2, labels_1 + labels_2, loc='upper left')

    plt.tight_layout()
    plt.savefig("grafico_comparativo_historico.png", dpi=300)
    print("✨ Sucesso! Gráfico salvo como 'grafico_comparativo_historico.png'")
    plt.show()

if __name__ == "__main__":
    # Verifica se tem o pandas e matplotlib instalados
    try:
        gerar_grafico()
    except ImportError:
        print("⚠️ Você precisa instalar as bibliotecas. Rode no terminal:")
        print("pip install pandas matplotlib")