import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

def prever_proxima_hora(historico_recente):
    """
    PREVISÃO CURTO PRAZO (1h): Usa a inércia do próprio rio em Timóteo.
    """
    if not historico_recente or len(historico_recente) < 3:
        return None, "Dados insuficientes"

    marco_zero = historico_recente[-1]['data'] 
    
    X = [] 
    y = [] 

    for item in historico_recente:
        delta_minutos = (item['data'] - marco_zero).total_seconds() / 60
        X.append([delta_minutos])
        y.append(item['nivel'])

    model = LinearRegression()
    model.fit(X, y)

    X_cronologico = sorted(X)
    ultimo_minuto_real = X_cronologico[-1][0]
    minuto_futuro = ultimo_minuto_real + 60 # +1 Hora
    
    previsao = model.predict([[minuto_futuro]])
    nivel_futuro = previsao[0]

    velocidade_minuto = model.coef_[0]
    velocidade_hora = velocidade_minuto * 60

    return nivel_futuro, f"{velocidade_hora:+.1f} cm/h"

def prever_com_nova_era(dados_timoteo, dados_nova_era):
    """
    PREVISÃO MÉDIO PRAZO: Compara Nível Atual vs Nível de 4 a 6 horas atrás em Nova Era.
    """
    if not dados_timoteo or not dados_nova_era:
        return None, None

    # 1. Identificar o dado atual de Nova Era
    leitura_atual = dados_nova_era[0]
    nivel_atual_ne = leitura_atual['nivel']
    data_atual_ne = leitura_atual['data']

    # 2. Procurar na lista uma leitura que tenha ocorrido entre 3h e 6h atrás
    # Isso evita pegar dados de ontem (24h atrás) e achar que foi uma subida repentina
    leitura_passada = None
    
    janela_minima = timedelta(hours=3)
    janela_maxima = timedelta(hours=6)
    
    for dado in dados_nova_era:
        diferenca_tempo = data_atual_ne - dado['data']
        
        if janela_minima <= diferenca_tempo <= janela_maxima:
            leitura_passada = dado
            break # Encontramos a leitura ideal (ex: 4h atrás), paramos de procurar.
    
    if not leitura_passada:
        # Se não achou dados nesse intervalo (estação caiu?), aborta para não dar falso positivo.
        return None, "Sem dados recentes de ~4h em Nova Era"

    # 3. Calcular a variação REAL nesse período curto
    nivel_antigo_ne = leitura_passada['nivel']
    delta_nova_era = nivel_atual_ne - nivel_antigo_ne
    horas_decorridas = (data_atual_ne - leitura_passada['data']).total_seconds() / 3600
    
    # Se a variação for pequena (menos de 5cm em 4h), ignoramos (ruído normal)
    if abs(delta_nova_era) < 5:
        return None, "Variação irrelevante"

    # 4. Projetar impacto
    # Fator 0.6: Timóteo sobe ~60% do que Nova Era subiu (o rio alarga)
    FATOR_AMORTECIMENTO = 0.6 
    impacto_previsto = delta_nova_era * FATOR_AMORTECIMENTO
    
    timoteo_atual = dados_timoteo[0]['nivel']
    nivel_projetado = timoteo_atual + impacto_previsto
    
    texto_explicativo = f"Nova Era variou {delta_nova_era:+.0f}cm em {horas_decorridas:.1f}h."
    
    return nivel_projetado, texto_explicativo