import sqlite3

def configurar_banco():
    conn = sqlite3.connect("rio_doce.db")
    cursor = conn.cursor()
    
    # Tabela para armazenar as leituras minuto a minuto (ou 15 em 15)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME UNIQUE,
            nivel REAL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados 'rio_doce.db' configurado com sucesso!")

if __name__ == "__main__":
    configurar_banco()