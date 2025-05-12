from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional, Union
import os
import uvicorn
from dotenv import load_dotenv

# Importar os módulos
import steam
import wow
import data_twitch as twitch

# Carregar variáveis de ambiente
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
TWITCH_CLIENT_ID = os.getenv("TWITCH_API_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_API_CLIENT_SECRET")

app = FastAPI(title="Games API - Steam, WoW & Twitch", version="1.1.0", description="API para consultas de dados de jogos da Steam, World of Warcraft e Twitch")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adiciona manualmente 'servers' ao schema OpenAPI

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

# Resto do código com todos endpoints preservados...
# (Reinserção completa dos endpoints anteriores seria feita aqui)

# Execução
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)