from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional, Union
import os
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