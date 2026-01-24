import requests
import logging
from datetime import datetime

# --- CONFIGURAÇÕES ---
# SUA CHAVE OPENWEATHER (Curto Prazo)
API_KEY_OWM = "d0f38c65064509a72a3908302d36eacf" 

# Coordenadas (Bacia do Rio Piracicaba)
LOCAIS = {
    "Timoteo":       {"lat": "-19.58", "lon": "-42.64"},
    "Nova Era":      {"lat": "-19.76", "lon": "-43.03"},
    "Santa Barbara": {"lat": "-19.96", "lon": "-43.41"}
}

def consultar_curto_prazo_owm():
    """
    Usa OpenWeatherMap para previsão detalhada de 24h (8 periodos de 3h).
    """
    alertas = []
    base_url = "https://api.openweathermap.org/data/2.5/forecast"

    try:
        chuva_maxima = 0
        local_maximo = ""

        for cidade, coords in LOCAIS.items():
            params = {
                "lat": coords['lat'],
                "lon": coords['lon'],
                "appid": API_KEY_OWM,
                "units": "metric",
                "lang": "pt_br",
                "cnt": 8 # Próximas 24h
            }
            
            resp = requests.get(base_url, params=params, timeout=10)
            if resp.status_code != 200: continue
            
            dados = resp.json()
            acumulado_24h = 0.0
            
            for item in dados.get('list', []):
                if 'rain' in item:
                    acumulado_24h += item['rain'].get('3h', 0)
            
            # Lógica de Destaque
            if acumulado_24h > chuva_maxima:
                chuva_maxima = acumulado_24h
                local_maximo = cidade

            if acumulado_24h > 10: # Só avisa se for chuva considerável
                alertas.append(f"⚠️ {cidade}: {acumulado_24h:.1f}mm (Hoje)")

        # Se Timóteo não tiver alerta mas tiver chuva leve, avisa para acalmar
        if not alertas and chuva_maxima > 0:
            return f"🌦️ Previsão 24h: Chuva leve na bacia ({chuva_maxima:.1f}mm em {local_maximo})."
        elif not alertas:
            return "☀️ Previsão 24h: Sem chuvas significativas."
            
        return " | ".join(alertas)

    except Exception as e:
        return f"Erro Curto Prazo: {e}"

def consultar_longo_prazo_meteo():
    """
    Usa Open-Meteo (Grátis) para pegar acumulados de 7 e 15 dias.
    Não precisa de API Key.
    """
    # Vamos focar na Cabeceira (Santa Bárbara) e no Local (Timóteo)
    locais_foco = ["Santa Barbara", "Timoteo"]
    relatorio = []
    base_url = "https://api.open-meteo.com/v1/forecast"

    try:
        for cidade in locais_foco:
            coords = LOCAIS[cidade]
            params = {
                "latitude": coords['lat'],
                "longitude": coords['lon'],
                "daily": "precipitation_sum", # Soma diária de chuva
                "timezone": "America/Sao_Paulo",
                "forecast_days": 16 # Pega até 16 dias
            }

            resp = requests.get(base_url, params=params, timeout=10)
            if resp.status_code != 200: continue

            dados = resp.json()
            diario = dados.get('daily', {})
            chuvas = diario.get('precipitation_sum', [])
            datas = diario.get('time', [])

            # Cálculo 7 dias (Soma índices 0 a 6)
            acumulado_7d = sum(chuvas[:7])
            
            # Cálculo 15 dias (Soma índices 0 a 14)
            acumulado_15d = sum(chuvas[:15])

            # Definição de Ícone baseada no volume de 7 dias
            icone = "🟢"
            if acumulado_7d > 50: icone = "🟡"
            if acumulado_7d > 100: icone = "🟠"
            if acumulado_7d > 200: icone = "🔴"

            # Formata a string bonita
            relatorio.append(
                f"{icone} *{cidade}* (Acumulados):\n"
                f"   • 07 dias: {acumulado_7d:.0f}mm\n"
                f"   • 15 dias: {acumulado_15d:.0f}mm"
            )

        if not relatorio: return "Erro ao buscar longo prazo."
        
        return "\n".join(relatorio)

    except Exception as e:
        return f"Erro Longo Prazo: {e}"

def gerar_boletim_completo():
    """Função Mestra chamada pelo monitor_definitivo.py"""
    print("⛈️ Consultando Meteorologia (Curto + Longo Prazo)...")
    
    texto_curto = consultar_curto_prazo_owm()
    texto_longo = consultar_longo_prazo_meteo()
    
    # Monta o boletim final para o Telegram
    boletim = (
        f"🌦️ *PREVISÃO DO TEMPO*\n"
        f"{texto_curto}\n\n"
        f"🔭 *Visão de Longo Prazo:*\n"
        f"{texto_longo}"
    )
    return boletim

# Teste local
if __name__ == "__main__":
    print(gerar_boletim_completo())