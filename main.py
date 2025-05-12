import sys
import traceback
import os
from typing import List, Optional, Union
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
import uvicorn

# Garante que o diretório atual está no sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importação de módulos com logs
try:
    import steam
    print("Módulo steam importado com sucesso", file=sys.stderr)
except ImportError as e:
    print(f"Erro ao importar steam: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

try:
    import wow
    print("Módulo wow importado com sucesso", file=sys.stderr)
except ImportError as e:
    print(f"Erro ao importar wow: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

try:
    import data_twitch
    print("Módulo data_twitch importado com sucesso", file=sys.stderr)
except ImportError as e:
    print(f"Erro ao importar data_twitch: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# Carrega variáveis de ambiente
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
TWITCH_CLIENT_ID = os.getenv("TWITCH_API_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_API_CLIENT_SECRET")

# Inicializa o FastAPI
app = FastAPI(title="Games API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adiciona campo `servers` ao OpenAPI

def get_custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://agent-vgames.onrender.com", "description": "Servidor Render"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = get_custom_openapi

# Exemplo de rota de saúde
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "steam": bool(STEAM_API_KEY),
        "blizzard": bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET),
        "twitch": bool(TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET)
    }

# Entrypoint local
if __name__ == "__main__":
    try:
        print("Iniciando API Games...", file=sys.stderr)
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    except Exception as e:
        print(f"Erro ao executar a API: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)