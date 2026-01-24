# reset_stories.py atualizado
import json
from datetime import datetime

arquivo = "stories_ativos.json"

estado_inicial = {
    "quantidade": 2,  # <--- Coloque aqui quantos stories tem HOJE no seu perfil
    "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

with open(arquivo, "w") as f:
    json.dump(estado_inicial, f, indent=4)

print("✅ Sincronizado!")