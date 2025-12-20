# dados_ruas.py
# Calibrado com base na CHEIA DE 2022 (Pico Rio: 960cm)
# Cálculo: Cota Início = 960 - (Altura da Enchente Local)

def obter_ruas():
    """
    Retorna a lista oficial de ruas atingidas em Cachoeira do Vale.
    """
    return [
        # --- PRIORIDADE 1: AS PRIMEIRAS A ALAGAR (< 780cm) ---
        {
            "nome": "R. Rio Corrente (Parte Baixa)",
            "apelido": "R. Rio Corrente",
            "cota_alerta": 650,     
            "cota_inicio": 725,     # Ref: Nº 156 (960-235)
            "prioridade": 1
        },
        {
            "nome": "R. Rio Araguaia",
            "apelido": "R. Rio Araguaia",
            "cota_alerta": 680,
            "cota_inicio": 755,     # Ref: PDF (960-205)
            "prioridade": 1
        },
        {
            "nome": "R. Rio Tietê",
            "apelido": "R. Rio Tietê",
            "cota_alerta": 680,
            "cota_inicio": 755,     # Ref: PDF (960-205)
            "prioridade": 1
        },
        {
            "nome": "Travessa Bartolomeu",
            "apelido": "Tv. Bartolomeu",
            "cota_alerta": 680,
            "cota_inicio": 755,     # Ref: Nº 2 (960-205)
            "prioridade": 1
        },
        {
            "nome": "R. João Pedreiro (Parte Baixa)",
            "apelido": "R. J. Pedreiro",
            "cota_alerta": 700,
            "cota_inicio": 760,     # Ref: Nº 41 (960-200)
            "prioridade": 1
        },

        # --- PRIORIDADE 2: MÉDIO RISCO (780cm - 820cm) ---
        {
            "nome": "Rua Tupis",
            "apelido": "Rua Tupis",
            "cota_alerta": 720,
            "cota_inicio": 800,     # Ref: Nº 66 (960-160)
            "prioridade": 2
        },
        {
            "nome": "Rua Tamôios",
            "apelido": "Rua Tamôios",
            "cota_alerta": 730,
            "cota_inicio": 810,     # Ref: PDF (960-150)
            "prioridade": 2
        },

        # --- PRIORIDADE 3: ALTO RISCO (> 820cm) ---
        {
            "nome": "Av. Minas Gerais",
            "apelido": "Av. Minas Gerais",
            "cota_alerta": 750,
            "cota_inicio": 830,     # Ref: Nº 216 (960-130)
            "prioridade": 3
        },
        {
            "nome": "Rua Guanabara",
            "apelido": "R. Guanabara",
            "cota_alerta": 750,
            "cota_inicio": 835,     # Ref: Nº 110 (960-125)
            "prioridade": 3
        },
        {
            "nome": "Travessa Bandeirantes",
            "apelido": "Tv. Bandeirantes",
            "cota_alerta": 750,
            "cota_inicio": 830,     # Estimado (Vizinha da Minas Gerais)
            "prioridade": 3
        },
        {
            "nome": "Rua Tupinambás",
            "apelido": "R. Tupinambás",
            "cota_alerta": 750,
            "cota_inicio": 830,     # Estimado
            "prioridade": 3
        },
        {
            "nome": "Rua Guarani",
            "apelido": "Rua Guarani",
            "cota_alerta": 750,
            "cota_inicio": 830,     # Estimado
            "prioridade": 3
        },
        {
            "nome": "Rua Carijós",
            "apelido": "Rua Carijós",
            "cota_alerta": 760,
            "cota_inicio": 845,     # Ref: Nº 61 (960-115)
            "prioridade": 3
        }
    ]

def calcular_risco_por_rua(nivel_atual_cm):
    """
    Calcula o status de cada rua com base no nível atual.
    """
    ruas = obter_ruas()
    resultado = []

    for rua in ruas:
        inicio = rua['cota_inicio']
        alerta = rua['cota_alerta']
        
        # 1. Situação Normal
        if nivel_atual_cm < alerta:
            porcentagem = 0
            status = "NORMAL"
            cor = "VERDE"
        
        # 2. Situação de Atenção (Rio subindo perto da rua)
        elif alerta <= nivel_atual_cm < inicio:
            diferenca_total = inicio - alerta
            diferenca_atual = nivel_atual_cm - alerta
            if diferenca_total <= 0: diferenca_total = 1
            
            porcentagem = int((diferenca_atual / diferenca_total) * 100)
            status = "ATENÇÃO"
            cor = "AMARELO"

        # 3. Inundação (Água na rua)
        else:
            excesso = nivel_atual_cm - inicio
            porcentagem = 100 + int(excesso / 5) 
            status = "INUNDAÇÃO"
            cor = "VERMELHO"

        resultado.append({
            "nome": rua['nome'],
            "apelido": rua['apelido'],
            "porcentagem": porcentagem,
            "status": status,
            "cor": cor,
            "cota_inicio": inicio 
        })

    # Ordena: Maior risco primeiro
    resultado.sort(key=lambda x: x['porcentagem'], reverse=True)
    
    return resultado