import sqlite3
import pandas as pd
from datetime import datetime
import os

def importar_planilha_manual():
    arquivo = "historico_anos.csv"
    
    if not os.path.exists(arquivo):
        print(f"❌ Erro: O arquivo '{arquivo}' não foi encontrado.")
        return

    print(f"⏳ Lendo arquivo {arquivo} com as novas colunas...")
    
    try:
        # Tenta ler o CSV (detectando separador automaticamente e usando latin1 para acentos)
        df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')

        # --- MAPEAMENTO COM OS NOVOS NOMES ---
        col_data = "Data_Hora"
        col_nivel = "Nivel_Adotado"

        # Verifica se as colunas existem mesmo no arquivo
        if col_data not in df.columns or col_nivel not in df.columns:
            print(f"❌ Erro: Colunas não encontradas! As colunas no arquivo são: {list(df.columns)}")
            return

        print("🧹 Formatando dados...")
        
        # Converte a coluna de data (Pandas é inteligente para detectar o formato)
        df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        
        # Remove linhas onde a data ou o nível são nulos
        df = df.dropna(subset=[col_data, col_nivel])

        # Conectar ao Banco de Dados
        conn = sqlite3.connect("rio_doce.db")
        cursor = conn.cursor()
        
        # Garante a existência da tabela
        cursor.execute("CREATE TABLE IF NOT EXISTS historico (data_hora DATETIME UNIQUE, nivel REAL)")

        registros_novos = 0
        print("📥 Inserindo dados no SQLite...")
        
        for _, linha in df.iterrows():
            try:
                dt_str = linha[col_data].strftime("%Y-%m-%d %H:%M:%S")
                nivel = float(linha[col_nivel])
                
                # INSERT OR IGNORE para não dar erro em datas duplicadas
                cursor.execute("INSERT OR IGNORE INTO historico (data_hora, nivel) VALUES (?, ?)", (dt_str, nivel))
                if cursor.rowcount > 0:
                    registros_novos += 1
            except:
                continue

        conn.commit()
        conn.close()
        
        print(f"✅ Sucesso total!")
        print(f"📊 Foram inseridos {registros_novos} registros no banco 'rio_doce.db'.")

    except Exception as e:
        print(f"❌ Erro crítico na importação: {e}")

if __name__ == "__main__":
    importar_planilha_manual()