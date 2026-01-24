import csv
from datetime import datetime

# Nome do arquivo CSV (Verifique se o nome está exato)
ARQUIVO = "historico_guilman.csv"

def analisar_padroes():
    print(f"📊 Analisando histórico de: {ARQUIVO}...")
    
    maxima_historica = 0.0
    data_maxima = ""
    
    # Dicionário para guardar o pico de cada ano/temporada
    picos_anuais = {} 

    linhas_lidas = 0
    linhas_ignoradas = 0

    try:
        with open(ARQUIVO, newline='', encoding='utf-8-sig') as csvfile:
            # Detecta automaticamente se usa vírgula ou ponto e vírgula
            sample = csvfile.read(1024)
            csvfile.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            
            leitor = csv.DictReader(csvfile, dialect=dialect)
            
            # Normaliza os nomes das colunas (remove espaços extras)
            leitor.fieldnames = [nome.strip() for nome in leitor.fieldnames]
            
            # Verifica se as colunas existem
            if 'vazao' not in leitor.fieldnames or 'data_hora' not in leitor.fieldnames:
                print(f"❌ Erro: As colunas 'vazao' e 'data_hora' não foram encontradas.")
                print(f"Colunas detectadas: {leitor.fieldnames}")
                return

            print(f"✅ Colunas detectadas: {leitor.fieldnames}")

            for linha in leitor:
                try:
                    # Lendo a DATA (data_hora)
                    # Tenta formatos comuns (dia/mês/ano ou ano-mês-dia)
                    data_str = linha['data_hora']
                    
                    # Lendo a VAZÃO (vazao)
                    # Substitui vírgula por ponto para o Python entender decimal
                    vazao_str = linha['vazao'].replace(',', '.')
                    if not vazao_str or vazao_str.strip() == '':
                        continue
                        
                    vazao = float(vazao_str)
                    
                    linhas_lidas += 1
                    
                    # 1. Checar Máxima Histórica
                    if vazao > maxima_historica:
                        maxima_historica = vazao
                        data_maxima = data_str
                        
                    # 2. Agrupar por Ano (para ver tendências)
                    # Pega os últimos 4 caracteres da data (supõe formato .../YYYY)
                    # Se sua data for YYYY-..., ajustaremos
                    if "/" in data_str:
                        ano = data_str.split('/')[-1][:4]
                    elif "-" in data_str:
                        ano = data_str.split('-')[0]
                    else:
                        ano = "Desc."

                    if ano not in picos_anuais or vazao > picos_anuais[ano]:
                        picos_anuais[ano] = vazao
                        
                except ValueError:
                    linhas_ignoradas += 1
                    continue

        print(f"\n--- 🌊 ANÁLISE CONCLUÍDA ({linhas_lidas} registros) ---")
        print(f"🚨 MAIOR VAZÃO JÁ REGISTRADA: {maxima_historica:.0f} m³/s")
        print(f"📅 Data do recorde: {data_maxima}")
        
        print("\n📈 Picos de Vazão por Ano:")
        anos_ordenados = sorted(picos_anuais.keys())
        for ano in anos_ordenados:
            print(f"   • {ano}: {picos_anuais[ano]:.0f} m³/s")
            
        # CÁLCULO DOS GATILHOS (A parte mais importante!)
        # Sugestão: Alerta em 50% do pior caso, Crítico em 80%
        gatilho_alerta = maxima_historica * 0.5 
        gatilho_critico = maxima_historica * 0.8 
        
        print("\n⚙️ COPIL NO 'MONITOR_DEFINITIVO.PY':")
        print("-" * 40)
        print(f"VAZAO_ALERTA_GUILMAN = {gatilho_alerta:.0f}   # Início de Atenção")
        print(f"VAZAO_CRITICA_GUILMAN = {gatilho_critico:.0f}  # Risco Real de Enchente")
        print("-" * 40)

    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{ARQUIVO}' não encontrado.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    analisar_padroes()