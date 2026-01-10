import requests
import xml.etree.ElementTree as ET
import sqlite3
from datetime import datetime
import time

# Estação Timóteo
ESTACAO_ID = "56750000" 

def salvar_no_banco(dados):
    if not dados: return
    conn = sqlite3.connect("rio_doce.db")
    cursor = conn.cursor()
    # Usamos INSERT OR IGNORE para evitar duplicados
    cursor.executemany(
        "INSERT OR IGNORE INTO historico (data_hora, nivel) VALUES (?, ?)", dados
    )
    conn.commit()
    conn.close()

def buscar_ana_v2(data_inicio, data_fim):
    """
    Usa o endpoint de telemetria que é mais estável para dados históricos.
    """
    # A API da ANA exige o formato dd/mm/yyyy
    url = "https://www.snirh.gov.br/ServiceANA/ServiceANA.asmx/DadosHidrometrologicos"
    params = {
        "codEstacao": ESTACAO_ID,
        "dataInicio": data_inicio,
        "dataFim": data_fim
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        
        # Se não for 200 ou estiver vazio, aborta
        if response.status_code != 200 or not response.content:
            print(f"⚠️ Erro API: Status {response.status_code}")
            return []

        # Tenta parsear o XML
        tree = ET.fromstring(response.content)
        dados_batch = []
        
        for dado in tree.findall(".//DadosHidrometrologicos"):
            # A API da ANA pode retornar 'Cota' ou 'Nivel' dependendo do endpoint
            data_str = dado.find("DataHora").text if dado.find("DataHora") is not None else None
            nivel = dado.find("Cota").text if dado.find("Cota") is not None else None
            
            if data_str and nivel and nivel.strip():
                try:
                    # Formata a data para o padrão do SQLite (YYYY-MM-DD HH:MM:SS)
                    # A ANA envia: 2019-11-01 00:00:00 ou dd/mm/yyyy...
                    # Vamos garantir o parse correto:
                    if "-" in data_str:
                        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        dt = datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
                    
                    dados_batch.append((dt.strftime("%Y-%m-%d %H:%M:%S"), float(nivel)))
                except:
                    continue
        
        return dados_batch
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return []

def executor_colheita_historica():
    print("🌊 Iniciando Colheita Automática de Dados Críticos (Nov-Fev)...")
    
    # Range de anos solicitado
    anos = range(2019, 2026) # De 2019 até 2025
    
    for ano in anos:
        # Definimos os dois blocos críticos por ano
        periodos = [
            (f"01/11/{ano}", f"31/12/{ano}"),  # Início da temporada
            (f"01/01/{ano+1}", f"28/02/{ano+1}") # Pico da temporada
        ]
        
        for inicio, fim in periodos:
            # Não buscar datas no futuro (ex: fev/2026)
            dt_fim_obj = datetime.strptime(fim, "%d/%m/%Y")
            if dt_fim_obj > datetime.now():
                continue

            print(f"⏳ Baixando: {inicio} até {fim}...")
            dados = buscar_ana_v2(inicio, fim)
            
            if dados:
                salvar_no_banco(dados)
                print(f"✅ {len(dados)} registros salvos no banco.")
            else:
                print("ℹ️ Nenhum dado encontrado neste período.")
            
            # Pausa para não sobrecarregar a API
            time.sleep(3)

if __name__ == "__main__":
    # Garante que a tabela existe antes de começar
    conn = sqlite3.connect("rio_doce.db")
    conn.execute("CREATE TABLE IF NOT EXISTS historico (data_hora DATETIME UNIQUE, nivel REAL)")
    conn.close()
    
    executor_colheita_historica()
    print("\n✨ Processo finalizado! Seu banco local agora tem os dados críticos.")