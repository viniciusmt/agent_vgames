from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional, Union
import os
import uvicorn
from dotenv import load_dotenv
import steam

# Carregar variáveis de ambiente
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

app = FastAPI(title="Steam Games API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameDataRequest(BaseModel):
    app_ids: Optional[List[Union[str, int]]] = None
    app_id: Optional[Union[str, int]] = None
    language: Optional[str] = "portuguese"
    max_reviews: Optional[int] = 50

class CurrentPlayersRequest(BaseModel):
    app_id: Union[str, int]

class HistoricalDataRequest(BaseModel):
    app_ids: Optional[List[Union[str, int]]] = None
    app_id: Optional[Union[str, int]] = None

class GameReviewsRequest(BaseModel):
    app_ids: Optional[List[Union[str, int]]] = None
    app_id: Optional[Union[str, int]] = None
    language: Optional[str] = "portuguese"
    max_reviews: Optional[int] = 50

class RecentGamesRequest(BaseModel):
    app_ids: Optional[List[Union[str, int]]] = None
    app_id: Optional[Union[str, int]] = None
    num_players: Optional[int] = 10

def process_app_ids(request_data) -> List[int]:
    app_ids = request_data.app_ids
    if not app_ids:
        if request_data.app_id:
            app_ids = [request_data.app_id]
        else:
            raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
    try:
        return [int(id) for id in app_ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="app_ids devem ser números válidos")

# ------------------ OPENAPI PERSONALIZADO ------------------
def get_custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Steam Games API",
        version="1.0.0",
        description="API para consultas de dados de jogos via Steam",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://agent-vgames.onrender.com", "description": "Servidor Render"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = get_custom_openapi

@app.get("/openapi.json")
def custom_openapi_route():
    return get_custom_openapi()

@app.get("/.well-known/openapi.json")
def mcp_openapi():
    return get_custom_openapi()
# ----------------------------------------------------------

@app.post("/steam/game-data")
async def steam_game_data(request: GameDataRequest):
    app_ids = process_app_ids(request)
    result = steam.get_steam_game_data(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/current-players")
async def current_players(request: CurrentPlayersRequest):
    app_id = int(request.app_id)
    result = steam.get_current_players(app_id)
    return {"success": True, "data": {"current_players": result}}

@app.post("/steam/historical-data")
async def historical_data(request: HistoricalDataRequest):
    app_ids = process_app_ids(request)
    result = steam.get_historical_data_for_games(app_ids)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/game-reviews")
async def game_reviews(request: GameReviewsRequest):
    app_ids = process_app_ids(request)
    result = steam.get_steam_game_reviews(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/recent-games")
async def recent_games(request: RecentGamesRequest):
    app_ids = process_app_ids(request)
    if not STEAM_API_KEY:
        raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada")
    result = steam.get_recent_games_for_multiple_apps(app_ids, STEAM_API_KEY, request.num_players)
    return {"success": True, "data": result.to_dict("records")}

@app.get("/")
async def root():
    return {"message": "Steam Games API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "steam_api_configured": bool(STEAM_API_KEY)}

# Configuração para execução no Render
if __name__ == "__main__":
    # O Render fornece a porta através da variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
