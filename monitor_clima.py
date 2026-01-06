import requests
import logging

# SUA CHAVE (CUIDADO AO COMPARTILHAR)
API_KEY = "d0f38c65064509a72a3908302d36eacf"

# Coordenadas Estratégicas (Latitude, Longitude)
LOCAIS = {
    "Timoteo":      {"lat": "-19.58", "lon": "-42.64"}, # Local
    "Nova Era":     {"lat": "-19.76", "lon": "-43.03"}, # Meio do caminho
    "Santa Barbara": {"lat": "-19.96", "lon": "-43.41"}  # Cabeceira/Nascente
}

def consultar_previsao_chuva():
    """
    Consulta a API OpenWeatherMap para ver se vai chover nas próximas 24h.
    Retorna um texto resumido para o relatório.
    """
    alertas = []
    
    # URL da API (Previsão de 5 dias / 3 horas)
    base_url = "https://api.openweathermap.org/data/2.5/forecast"

    print("⛈️ Consultando Meteorologia...")

    try:
        for cidade, coords in LOCAIS.items():
            params = {
                "lat": coords['lat'],
                "lon": coords['lon'],
                "appid": API_KEY,
                "units": "metric", # Graus Celsius
                "lang": "pt_br",
                "cnt": 8 # Pega apenas as próximas 8 previsões (8 * 3h = 24h)
            }
            
            resposta = requests.get(base_url, params=params)
            
            if resposta.status_code != 200:
                print(f"Erro na API Clima ({cidade}): {resposta.status_code}")
                continue
                
            dados = resposta.json()
            
            # Analisar os dados das próximas 24h
            chuva_acumulada = 0.0
            descricao_principal = ""
            
            for item in dados['list']:
                # Tenta pegar volume de chuva (se houver)
                if 'rain' in item:
                    chuva_acumulada += item['rain'].get('3h', 0)
                
                # Pega a descrição do tempo (ex: "chuva moderada")
                if not descricao_principal:
                    descricao_principal = item['weather'][0]['description']

            # SÓ AVISA SE TIVER CHUVA RELEVANTE (> 5mm nas próximas 24h)
            if chuva_acumulada > 5:
                emoji = "🌧️"
                if chuva_acumulada > 20: emoji = "⛈️"
                if chuva_acumulada > 50: emoji = "🚨"
                
                alertas.append(f"{emoji} {cidade}: Previstos {chuva_acumulada:.1f}mm (24h)")
            elif cidade == "Timoteo":
                # Para Timóteo, avisa mesmo se não chover, para dar paz
                alertas.append(f"☁️ Timóteo: Sem chuva grave prevista.")

        if not alertas:
            return "🌤️ Bacia do Rio Piracicaba sem chuvas previstas."
            
        return "\n".join(alertas)

    except Exception as e:
        return f"Erro ao consultar clima: {e}"

# Teste rápido se rodar o arquivo direto
if __name__ == "__main__":
    resultado = consultar_previsao_chuva()
    print("\n--- RESULTADO ---")
    print(resultado)