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
import data_twitch

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

# MODELS TWITCH
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

# ENDPOINTS TWITCH
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
