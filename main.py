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

# =================== MODELS ===================
# Steam
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

# WoW
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

# Twitch
class TwitchGameSearchRequest(BaseModel):
    game_names: List[str]

class TwitchChannelsRequest(BaseModel):
    channel_names: List[str]

class TwitchGameInfoRequest(BaseModel):
    game_name: str

class TwitchLiveStreamsRequest(BaseModel):
    game_ids: List[str]
    language: Optional[str] = "pt"
    limit: Optional[int] = 100

class TwitchTopGamesRequest(BaseModel):
    limit: Optional[int] = 100

# =================== ENDPOINTS ===================
@app.get("/openapi.json")
def custom_openapi_route():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "steam_api": bool(STEAM_API_KEY),
            "blizzard_api": bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET)
        }
    }

# Steam
@app.post("/steam/game-data")
async def steam_game_data(request: GameDataRequest):
    app_ids = steam.process_app_ids(request)
    result = steam.get_steam_game_data(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/current-players")
async def current_players(request: CurrentPlayersRequest):
    result = steam.get_current_players(int(request.app_id))
    return {"success": True, "data": {"current_players": result}}

@app.post("/steam/historical-data")
async def historical_data(request: HistoricalDataRequest):
    app_ids = steam.process_app_ids(request)
    result = steam.get_historical_data_for_games(app_ids)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/game-reviews")
async def game_reviews(request: GameReviewsRequest):
    app_ids = steam.process_app_ids(request)
    result = steam.get_steam_game_reviews(app_ids, request.language, request.max_reviews)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/recent-games")
async def recent_games(request: RecentGamesRequest):
    app_ids = steam.process_app_ids(request)
    result = steam.get_recent_games_for_multiple_apps(app_ids, STEAM_API_KEY, request.num_players)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/search-games")
async def search_games(request: SearchGamesRequest):
    result = steam.search_game_ids(request.game_names, request.max_results)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/steam/search-game-by-name")
async def search_game_by_name(request: SearchGameByNameRequest):
    return steam.get_game_details_by_name(request.game_name)

@app.post("/steam/advanced-search")
async def advanced_search(request: AdvancedSearchRequest):
    result = steam.search_games_advanced(request.query, request.filters)
    return {"success": True, "data": result.to_dict("records")}

# WoW
@app.post("/wow/character")
async def get_character_info(request: WoWCharacterRequest):
    return wow.get_complete_character_info(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, request.region, request.realm, request.character_name)

@app.post("/wow/characters")
async def search_multiple_characters(request: WoWMultipleCharactersRequest):
    return wow.search_characters(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, request.region, request.realm, request.names)

@app.post("/wow/guild")
async def get_guild_info(request: WoWGuildRequest):
    return wow.get_guild_info(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, request.region, request.realm, request.guild_name)

@app.post("/wow/guilds")
async def search_multiple_guilds(request: WoWMultipleGuildsRequest):
    return wow.search_guilds(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, request.region, request.realm, request.guild_names)

@app.post("/wow/auction")
async def get_auction_data(request: WoWAuctionRequest):
    return wow.get_auction_data(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, request.region, request.realm, request.limit)

# Twitch
@app.post("/twitch/search-games")
async def twitch_search_games(request: TwitchGameSearchRequest):
    result = twitch.search_game_ids(request.game_names, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/twitch/channels")
async def twitch_get_channels(request: TwitchChannelsRequest):
    result = twitch.get_twitch_channel_data_bulk(request.channel_names, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/twitch/game-info")
async def twitch_get_game_info(request: TwitchGameInfoRequest):
    result = twitch.get_twitch_game_data(request.game_name, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    return result

@app.post("/twitch/live-streams")
async def twitch_get_live_streams(request: TwitchLiveStreamsRequest):
    result = twitch.get_live_streams_for_games(request.game_ids, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, request.language, request.limit)
    return {"success": True, "data": result.to_dict("records")}

@app.post("/twitch/top-games")
async def twitch_get_top_games(request: TwitchTopGamesRequest):
    result = twitch.get_top_games(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, request.limit)
    return {"success": True, "data": result.to_dict("records")}

# Execução
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
