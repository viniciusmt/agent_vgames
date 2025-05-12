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

# Carregar variáveis de ambiente
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")

app = FastAPI(title="Games API - Steam & WoW", version="1.0.0", description="API para consultas de dados de jogos da Steam e World of Warcraft")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================== STEAM MODELS ===================
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

class SearchGamesRequest(BaseModel):
    game_names: List[str]
    max_results: Optional[int] = 10

class SearchGameByNameRequest(BaseModel):
    game_name: str

class AdvancedSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None

# =================== WOW MODELS ===================
class WoWCharacterRequest(BaseModel):
    character_name: str
    realm: str
    region: Optional[str] = "us"

class WoWMultipleCharactersRequest(BaseModel):
    names: List[str]
    realm: str
    region: Optional[str] = "us"

class WoWGuildRequest(BaseModel):
    guild_name: str
    realm: str
    region: Optional[str] = "us"

class WoWMultipleGuildsRequest(BaseModel):
    guild_names: List[str]
    realm: str
    region: Optional[str] = "us"

class WoWAuctionRequest(BaseModel):
    realm: str
    region: Optional[str] = "us"
    limit: Optional[int] = 100

# =================== UTILITY FUNCTIONS ===================
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

# =================== OPENAPI CONFIGURATION ===================
def get_custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Games API - Steam & WoW",
        version="1.0.0",
        description="API para consultas de dados de jogos da Steam e World of Warcraft",
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

# =================== STEAM ENDPOINTS ===================
@app.post("/steam/game-data")
async def steam_game_data(request: GameDataRequest):
    """Obtém dados detalhados de jogos da Steam"""
    app_ids = process_app_ids(request)
    result = steam.get_steam_game_data(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/current-players")
async def current_players(request: CurrentPlayersRequest):
    """Obtém o número atual de jogadores de um jogo"""
    app_id = int(request.app_id)
    result = steam.get_current_players(app_id)
    return {"success": True, "data": {"current_players": result}}

@app.post("/steam/historical-data")
async def historical_data(request: HistoricalDataRequest):
    """Obtém dados históricos de jogadores da Steam"""
    app_ids = process_app_ids(request)
    result = steam.get_historical_data_for_games(app_ids)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/game-reviews")
async def game_reviews(request: GameReviewsRequest):
    """Obtém avaliações de jogos da Steam"""
    app_ids = process_app_ids(request)
    result = steam.get_steam_game_reviews(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/recent-games")
async def recent_games(request: RecentGamesRequest):
    """Obtém jogos recentes jogados por usuários que avaliaram jogos específicos"""
    app_ids = process_app_ids(request)
    if not STEAM_API_KEY:
        raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada")
    result = steam.get_recent_games_for_multiple_apps(app_ids, STEAM_API_KEY, request.num_players)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/search-games")
async def search_games(request: SearchGamesRequest):
    """Busca IDs de jogos pelos nomes"""
    result = steam.search_game_ids(request.game_names, request.max_results)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/search-game-by-name")
async def search_game_by_name(request: SearchGameByNameRequest):
    """Busca detalhes completos de um jogo pelo nome"""
    result = steam.get_game_details_by_name(request.game_name)
    return result

@app.post("/steam/advanced-search")
async def advanced_search(request: AdvancedSearchRequest):
    """Busca avançada com filtros"""
    result = steam.search_games_advanced(request.query, request.filters)
    return {"success": True, "data": result.to_dict("records")}

# =================== WOW ENDPOINTS ===================
@app.post("/wow/character")
async def get_character_info(request: WoWCharacterRequest):
    """Obtém informações detalhadas de um personagem do WoW"""
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Credenciais da Blizzard não configuradas")
    
    result = wow.get_complete_character_info(
        BLIZZARD_CLIENT_ID,
        BLIZZARD_CLIENT_SECRET,
        request.region,
        request.realm,
        request.character_name
    )
    return result

@app.post("/wow/characters")
async def search_multiple_characters(request: WoWMultipleCharactersRequest):
    """Pesquisa múltiplos personagens do WoW"""
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Credenciais da Blizzard não configuradas")
    
    result = wow.search_characters(
        BLIZZARD_CLIENT_ID,
        BLIZZARD_CLIENT_SECRET,
        request.region,
        request.realm,
        request.names
    )
    return result

@app.post("/wow/guild")
async def get_guild_info(request: WoWGuildRequest):
    """Obtém informações detalhadas de uma guilda do WoW"""
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Credenciais da Blizzard não configuradas")
    
    result = wow.get_guild_info(
        BLIZZARD_CLIENT_ID,
        BLIZZARD_CLIENT_SECRET,
        request.region,
        request.realm,
        request.guild_name
    )
    return result

@app.post("/wow/guilds")
async def search_multiple_guilds(request: WoWMultipleGuildsRequest):
    """Pesquisa múltiplas guildas do WoW"""
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Credenciais da Blizzard não configuradas")
    
    result = wow.search_guilds(
        BLIZZARD_CLIENT_ID,
        BLIZZARD_CLIENT_SECRET,
        request.region,
        request.realm,
        request.guild_names
    )
    return result

@app.post("/wow/auction")
async def get_auction_data(request: WoWAuctionRequest):
    """Obtém dados do leilão (auction house) do WoW"""
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Credenciais da Blizzard não configuradas")
    
    result = wow.get_auction_data(
        BLIZZARD_CLIENT_ID,
        BLIZZARD_CLIENT_SECRET,
        request.region,
        request.realm,
        request.limit
    )
    return result

# =================== GENERAL ENDPOINTS ===================
@app.get("/")
async def root():
    return {
        "message": "Games API - Steam & WoW",
        "status": "running",
        "services": {
            "steam": {
                "api_configured": bool(STEAM_API_KEY),
                "endpoints": [
                    "/steam/game-data",
                    "/steam/current-players",
                    "/steam/historical-data",
                    "/steam/game-reviews",
                    "/steam/recent-games",
                    "/steam/search-games",
                    "/steam/search-game-by-name",
                    "/steam/advanced-search"
                ]
            },
            "wow": {
                "api_configured": bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET),
                "endpoints": [
                    "/wow/character",
                    "/wow/characters",
                    "/wow/guild",
                    "/wow/guilds",
                    "/wow/auction"
                ]
            }
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "steam_api": bool(STEAM_API_KEY),
            "blizzard_api": bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET)
        }
    }

# =================== MAIN EXECUTION ===================
if __name__ == "__main__":
    # O Render fornece a porta através da variável de ambiente PORT
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    print(f"Steam API configured: {bool(STEAM_API_KEY)}")
    print(f"Blizzard API configured: {bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET)}")
    uvicorn.run(app, host="0.0.0.0", port=port)
