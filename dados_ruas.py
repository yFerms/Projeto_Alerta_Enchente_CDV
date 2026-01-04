"""
MÓDULO DE DADOS DAS RUAS (VERSÃO 6.0 - ORDEM AGRUPADA)
Focado na identificação por número da residência.
Ordem fixa para facilitar a leitura dos moradores.
"""

def calcular_risco_por_rua(nivel_atual_rio):
    ruas = [
        # ==========================================================
        # GRUPO 1: AS PRIMEIRAS A SEREM ATINGIDAS
        # ==========================================================
        {
            "nome": "Rua Rio Corrente",
            "apelido": "Toda a extensão",
            "cota": 563,
            "prioridade": 1
        },
        {
            "nome": "Rua Rio Tietê / Araguaia",
            "apelido": "Toda a extensão",
            "cota": 590,
            "prioridade": 1
        },

        # ==========================================================
        # GRUPO 2: RUA TAMOIOS (Acesso)
        # ==========================================================
        {
            "nome": "Rua Tamoios",
            "apelido": "Base (Acesso ao Rio)",
            "cota": 651,
            "prioridade": 2
        },
        {
            "nome": "Rua Tamoios",
            "apelido": "Nº 1 (Esq. J. Pedreiro)",
            "cota": 810,
            "prioridade": 3
        },

        # ==========================================================
        # GRUPO 3: RUA JOÃO PEDREIRO (Sequencial)
        # ==========================================================
        {
            "nome": "Rua João Pedreiro",
            "apelido": "Nº 21 ao 651",
            "cota": 760,
            "prioridade": 2
        },
        {
            "nome": "Rua João Pedreiro",
            "apelido": "Nº 673 ao 715",
            "cota": 890,
            "prioridade": 4
        },
        {
            "nome": "Rua João Pedreiro",
            "apelido": "Nº 721 ao 1001",
            "cota": 910,
            "prioridade": 4
        },

        # ==========================================================
        # GRUPO 4: RUA GUANABARA (Sequencial)
        # ==========================================================
        {
            "nome": "Rua Guanabara",
            "apelido": "Nº 51 ao 133",
            "cota": 835,
            "prioridade": 3
        },
        {
            "nome": "Rua Guanabara",
            "apelido": "Nº 197 ao 264",
            "cota": 865,
            "prioridade": 3
        },
        {
            "nome": "Rua Guanabara",
            "apelido": "Nº 513 (Final)",
            "cota": 920,
            "prioridade": 4
        },

        # ==========================================================
        # GRUPO 5: RUA MINAS GERAIS (Sequencial)
        # ==========================================================
        {
            "nome": "Rua Minas Gerais",
            "apelido": "Nº 188 ao 400",
            "cota": 860,
            "prioridade": 3
        },
        {
            "nome": "Rua Minas Gerais",
            "apelido": "Nº 440 ao Final",
            "cota": 900,
            "prioridade": 4
        },

        # ==========================================================
        # GRUPO 6: OUTRAS
        # ==========================================================
        {
            "nome": "Travessa Bartolomeu",
            "apelido": "Toda a extensão",
            "cota": 718,
            "prioridade": 2
        }
    ]

    relatorio = []

    for rua in ruas:
        porcentagem = (nivel_atual_rio / rua['cota']) * 100
        if porcentagem > 100: porcentagem = 100.0
            
        relatorio.append({
            "nome": rua['nome'],
            "apelido": rua['apelido'],
            "cota_limite": rua['cota'],
            "porcentagem": round(porcentagem, 1),
            "status": "ALAGADA" if nivel_atual_rio >= rua['cota'] else "Livre"
        })

    # IMPORTANTE: A linha de ordenação (sort) foi REMOVIDA.
    # Agora respeita estritamente a ordem definida na lista acima.
    
    return relatorio