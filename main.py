import sys
import traceback
import os
from typing import List, Optional, Union
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import logging

# Configuração de logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger(__name__)

# Garante que o diretório atual está no sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importação de módulos com logs
try:
    import steam
    log.info("Módulo steam importado com sucesso")
except ImportError as e:
    log.error(f"Erro ao importar steam: {e}")
    traceback.print_exc(file=sys.stderr)

try:
    import wow
    log.info("Módulo wow importado com sucesso")
except ImportError as e:
    log.error(f"Erro ao importar wow: {e}")
    traceback.print_exc(file=sys.stderr)

try:
    import data_twitch
    log.info("Módulo data_twitch importado com sucesso")
except ImportError as e:
    log.error(f"Erro ao importar data_twitch: {e}")
    traceback.print_exc(file=sys.stderr)

# Carrega variáveis de ambiente
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
TWITCH_CLIENT_ID = os.getenv("TWITCH_API_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_API_CLIENT_SECRET")

# Configuração do FastAPI
app = FastAPI(
    title="Gaming API",
    description="API completa para dados de Steam, World of Warcraft e Twitch",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== CONFIGURAÇÃO OPENAPI =====================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Detecta o ambiente e define servidor apropriado
    is_production = os.getenv("RENDER_SERVICE_NAME") is not None
    
    if is_production:
        # Em produção, apenas o servidor do Render
        openapi_schema["servers"] = [
            {
                "url": "https://agent-vgames.onrender.com",
                "description": "Servidor Render (Produção)"
            }
        ]
    else:
        # Em desenvolvimento, adiciona servidor local
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Servidor Local (Desenvolvimento)"
            },
            {
                "url": "https://agent-vgames.onrender.com",
                "description": "Servidor Render (Produção)"
            }
        ]
    
    # Adiciona informações de contato
    openapi_schema["info"]["contact"] = {
        "name": "Gaming API Support",
        "url": "https://agent-vgames.onrender.com",
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ===================== ROOT ENDPOINT =====================
@app.get("/", summary="Gaming API - Página Principal")
def read_root():
    """Endpoint principal da Gaming API"""
    return {
        "message": "Gaming API v1.0.0",
        "description": "API completa para dados de Steam, World of Warcraft e Twitch",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "health_check": "/health",
        "endpoints": {
            "steam": [
                "/steam/game-data",
                "/steam/current-players",
                "/steam/historical-data",
                "/steam/game-reviews",
                "/steam/recent-games",
                "/steam/search-games",
                "/steam/game-by-name",
                "/steam/advanced-search"
            ],
            "wow": [
                "/wow/character-info",
                "/wow/search-characters",
                "/wow/guild-info",
                "/wow/search-guilds",
                "/wow/auction-data"
            ],
            "twitch": [
                "/twitch/search-games",
                "/twitch/channels",
                "/twitch/game-info",
                "/twitch/live-streams",
                "/twitch/top-games"
            ]
        }
    }

# ===================== HEALTH CHECK =====================
@app.get("/health", summary="Verificação de saúde da API")
def health_check():
    """Verifica o status da API e das credenciais configuradas"""
    return {
        "status": "ok",
        "steam": bool(STEAM_API_KEY),
        "blizzard": bool(BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET),
        "twitch": bool(TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET)
    }

# ===================== ENDPOINT PARA OPENAPI.JSON =====================
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    return JSONResponse(app.openapi())

# ===================== MODELS STEAM =====================
class SteamGameDataRequest(BaseModel):
    app_ids: List[int]
    language: Optional[str] = "portuguese"
    max_reviews: Optional[int] = 50

class SteamCurrentPlayersRequest(BaseModel):
    app_id: int

class SteamHistoricalDataRequest(BaseModel):
    app_ids: List[int]

class SteamGameReviewsRequest(BaseModel):
    app_ids: List[int]
    language: Optional[str] = "portuguese"
    max_reviews: Optional[int] = 50

class SteamRecentGamesRequest(BaseModel):
    app_ids: List[int]
    num_players: Optional[int] = 10

class SteamSearchGamesRequest(BaseModel):
    game_names: List[str]
    max_results: Optional[int] = 10

class SteamGameByNameRequest(BaseModel):
    game_name: str

class SteamAdvancedSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None

class SteamGameIDsRequest(BaseModel):
    game_names: List[str]
    max_results: Optional[int] = 10

# ===================== ENDPOINTS STEAM =====================
@app.post("/steam/game-data", 
          summary="Obter dados detalhados de jogos",
          tags=["Steam"])
async def steam_game_data(request: SteamGameDataRequest):
    """
    Obtém dados detalhados de jogos da Steam.
    
    Args:
        app_ids: Lista de IDs de jogos na Steam
        language: Idioma para as descrições e reviews (padrão: portuguese)
        max_reviews: Número máximo de reviews a serem coletados
        
    Returns:
        dict: Informações detalhadas dos jogos
    """
    try:
        result = steam.get_steam_game_data(request.app_ids, request.language, request.max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em steam_game_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/current-players", 
          summary="Obter número atual de jogadores",
          tags=["Steam"])
async def current_players(request: SteamCurrentPlayersRequest):
    """
    Obtém o número atual de jogadores para um jogo específico.
    
    Args:
        app_id: ID do jogo na Steam
        
    Returns:
        dict: Número atual de jogadores
    """
    try:
        result = steam.get_current_players(request.app_id)
        return {"success": True, "data": {"app_id": request.app_id, "current_players": result}}
    except Exception as e:
        log.error(f"Erro em current_players: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/historical-data", 
          summary="Obter dados históricos de jogadores",
          tags=["Steam"])
async def historical_data(request: SteamHistoricalDataRequest):
    """
    Obtém dados históricos de jogadores para jogos da Steam.
    
    Args:
        app_ids: Lista de IDs de jogos na Steam
        
    Returns:
        dict: Dados históricos de jogadores
    """
    try:
        result = steam.get_historical_data_for_games(request.app_ids)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em historical_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/game-reviews", 
          summary="Obter avaliações de jogos",
          tags=["Steam"])
async def game_reviews(request: SteamGameReviewsRequest):
    """
    Obtém avaliações de jogos da Steam.
    
    Args:
        app_ids: Lista de IDs de jogos na Steam
        language: Idioma das avaliações (padrão: portuguese)
        max_reviews: Número máximo de avaliações por jogo
        
    Returns:
        dict: Avaliações de jogos
    """
    try:
        result = steam.get_steam_game_reviews(request.app_ids, request.language, request.max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em game_reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/recent-games", 
          summary="Obter jogos recentes populares",
          tags=["Steam"])
async def recent_games(request: SteamRecentGamesRequest):
    """
    Obtém jogos recentes jogados por usuários que avaliaram jogos específicos.
    
    Args:
        app_ids: Lista de IDs de jogos na Steam
        num_players: Número de jogadores a analisar
        
    Returns:
        dict: Jogos recentes populares entre jogadores
    """
    try:
        if not STEAM_API_KEY:
            raise HTTPException(status_code=400, detail="Steam API Key não configurada")
        result = steam.get_recent_games_for_multiple_apps(request.app_ids, STEAM_API_KEY, request.num_players)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em recent_games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/search-games", 
          summary="Buscar jogos por nome",
          tags=["Steam"])
async def search_games(request: SteamSearchGamesRequest):
    """
    Busca por jogos na Steam baseado nos nomes.
    
    Args:
        game_names: Lista de nomes de jogos para buscar
        max_results: Número máximo de resultados por jogo
        
    Returns:
        dict: DataFrame com informações dos jogos encontrados
    """
    try:
        result = steam.search_game_ids(request.game_names, request.max_results)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em search_games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/game-by-name", 
          summary="Obter detalhes de jogo por nome",
          tags=["Steam"])
async def get_game_by_name(request: SteamGameByNameRequest):
    """
    Busca detalhes completos de um jogo específico pelo nome.
    
    Args:
        game_name: Nome do jogo
        
    Returns:
        dict: Informações detalhadas do primeiro resultado encontrado
    """
    try:
        result = steam.get_game_details_by_name(request.game_name)
        return result
    except Exception as e:
        log.error(f"Erro em get_game_by_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/advanced-search", 
          summary="Busca avançada de jogos",
          tags=["Steam"])
async def advanced_search(request: SteamAdvancedSearchRequest):
    """
    Busca avançada de jogos com filtros opcionais.
    
    Args:
        query: Termo de busca
        filters: Filtros opcionais como:
            - price_range: (min, max) - faixa de preço em USD
            - platforms: ['windows', 'mac', 'linux'] - plataformas
            - type: 'game' | 'dlc' | 'music' - tipo de item
            
    Returns:
        dict: DataFrame com resultados filtrados
    """
    try:
        result = steam.search_games_advanced(request.query, request.filters)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em advanced_search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== MODELS WOW =====================
class WoWCharacterInfoRequest(BaseModel):
    character_name: str
    realm: str
    region: Optional[str] = "us"

class WoWSearchCharactersRequest(BaseModel):
    names: List[str]
    realm: str
    region: Optional[str] = "us"

class WoWGuildInfoRequest(BaseModel):
    guild_name: str
    realm: str
    region: Optional[str] = "us"

class WoWSearchGuildsRequest(BaseModel):
    guild_names: List[str]
    realm: str
    region: Optional[str] = "us"

class WoWAuctionDataRequest(BaseModel):
    realm: str
    region: Optional[str] = "us"
    limit: Optional[int] = 100

# ===================== ENDPOINTS WOW =====================
@app.post("/wow/character-info", 
          summary="Obter informações de personagem",
          tags=["World of Warcraft"])
async def wow_character_info(request: WoWCharacterInfoRequest):
    """
    Obtém informações completas de um personagem WoW.
    
    Args:
        character_name: Nome do personagem
        realm: Nome do reino (servidor)
        region: Região do servidor (padrão: "us")
        
    Returns:
        dict: Perfil, estatísticas, equipamentos e conquistas
    """
    try:
        if not (BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET):
            raise HTTPException(status_code=400, detail="Credenciais da Blizzard não configuradas")
        result = wow.get_complete_character_info(
            BLIZZARD_CLIENT_ID, 
            BLIZZARD_CLIENT_SECRET, 
            request.region, 
            request.realm, 
            request.character_name
        )
        return {"success": True, "data": result}
    except Exception as e:
        log.error(f"Erro em wow_character_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wow/search-characters", 
          summary="Pesquisar múltiplos personagens",
          tags=["World of Warcraft"])
async def wow_search_characters(request: WoWSearchCharactersRequest):
    """
    Pesquisa múltiplos personagens de World of Warcraft.
    
    Args:
        names: Lista de nomes de personagens
        realm: Nome do reino (servidor)
        region: Região do servidor (padrão: "us")
        
    Returns:
        dict: Informações básicas dos personagens encontrados
    """
    try:
        if not (BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET):
            raise HTTPException(status_code=400, detail="Credenciais da Blizzard não configuradas")
        
        results = []
        for character_name in request.names:
            result = wow.get_complete_character_info(
                BLIZZARD_CLIENT_ID, 
                BLIZZARD_CLIENT_SECRET, 
                request.region, 
                request.realm, 
                character_name
            )
            if result.get("info"):
                results.append(result)
        
        return {"success": True, "data": results}
    except Exception as e:
        log.error(f"Erro em wow_search_characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wow/guild-info", 
          summary="Obter informações de guilda",
          tags=["World of Warcraft"])
async def wow_guild_info(request: WoWGuildInfoRequest):
    """
    Obtém informações detalhadas de uma guilda de World of Warcraft.
    
    Args:
        guild_name: Nome da guilda
        realm: Nome do reino (servidor)
        region: Região do servidor (padrão: "us")
        
    Returns:
        dict: Informações da guilda, incluindo lista de membros
    """
    try:
        if not (BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET):
            raise HTTPException(status_code=400, detail="Credenciais da Blizzard não configuradas")
        result = wow.consulta_guilda_wow(
            [request.guild_name], 
            request.realm, 
            request.region, 
            limit=50
        )
        return {"success": True, "data": result}
    except Exception as e:
        log.error(f"Erro em wow_guild_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wow/search-guilds", 
          summary="Pesquisar múltiplas guildas",
          tags=["World of Warcraft"])
async def wow_search_guilds(request: WoWSearchGuildsRequest):
    """
    Pesquisa múltiplas guildas de World of Warcraft.
    
    Args:
        guild_names: Lista de nomes de guildas
        realm: Nome do reino (servidor)
        region: Região do servidor (padrão: "us")
        
    Returns:
        dict: Informações básicas das guildas encontradas
    """
    try:
        if not (BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET):
            raise HTTPException(status_code=400, detail="Credenciais da Blizzard não configuradas")
        result = wow.consulta_guilda_wow(
            request.guild_names, 
            request.realm, 
            request.region, 
            limit=200
        )
        return {"success": True, "data": result}
    except Exception as e:
        log.error(f"Erro em wow_search_guilds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wow/auction-data", 
          summary="Obter dados do leilão",
          tags=["World of Warcraft"])
async def wow_auction_data(request: WoWAuctionDataRequest):
    """
    Obtém dados do leilão (mercado) de World of Warcraft.
    
    Args:
        realm: Nome do reino (servidor)
        region: Região do servidor (padrão: "us")
        limit: Número máximo de itens a retornar (padrão: 100)
        
    Returns:
        dict: Dados do leilão, incluindo preços e informações de itens
    """
    try:
        # Esta funcionalidade precisaria ser implementada no wow.py
        # Por enquanto, retornamos uma mensagem informativa
        return {
            "success": False, 
            "message": "Endpoint de dados de leilão ainda não implementado no módulo wow.py"
        }
    except Exception as e:
        log.error(f"Erro em wow_auction_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== MODELS TWITCH =====================
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

# ===================== ENDPOINTS TWITCH =====================

# Função auxiliar para verificar credenciais Twitch
def check_twitch_credentials():
    if not (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET):
        raise HTTPException(status_code=400, detail="Credenciais da Twitch não configuradas")

@app.post("/twitch/search-games", 
          summary="Buscar IDs de jogos na Twitch",
          tags=["Twitch"])
async def twitch_search_games(request: TwitchGameSearchRequest):
    """
    Busca IDs de jogos na Twitch com base em seus nomes.
    
    Args:
        game_names: Lista de nomes de jogos para buscar
        
    Returns:
        dict: Informações dos jogos encontrados
    """
    try:
        check_twitch_credentials()
        result = data_twitch.search_game_ids(request.game_names, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em twitch_search_games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twitch/channels", 
          summary="Obter informações de canais",
          tags=["Twitch"])
async def twitch_get_channels(request: TwitchChannelsRequest):
    """
    Obtém informações de múltiplos canais da Twitch.
    
    Args:
        channel_names: Lista de nomes de canais da Twitch
        
    Returns:
        dict: Informações dos canais
    """
    try:
        check_twitch_credentials()
        result = data_twitch.get_twitch_channel_data_bulk(request.channel_names, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em twitch_get_channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twitch/game-info", 
          summary="Obter informações de jogo",
          tags=["Twitch"])
async def twitch_get_game_info(request: TwitchGameInfoRequest):
    """
    Obtém informações detalhadas de um jogo na Twitch.
    
    Args:
        game_name: Nome do jogo
        
    Returns:
        dict: Informações do jogo
    """
    try:
        check_twitch_credentials()
        result = data_twitch.get_twitch_game_data(request.game_name, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
        return result
    except Exception as e:
        log.error(f"Erro em twitch_get_game_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twitch/live-streams", 
          summary="Obter streams ao vivo",
          tags=["Twitch"])
async def twitch_get_live_streams(request: TwitchLiveStreamsRequest):
    """
    Busca streams ao vivo para uma lista de jogos.
    
    Args:
        game_ids: Lista de IDs dos jogos na Twitch
        language: Código do idioma para filtrar as streams (padrão: 'pt')
        limit: Limite de streams a retornar por jogo (padrão: 100)
        
    Returns:
        dict: Dados das streams ao vivo
    """
    try:
        check_twitch_credentials()
        result = data_twitch.get_live_streams_for_games(request.game_ids, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, request.language, request.limit)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em twitch_get_live_streams: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twitch/top-games", 
          summary="Obter jogos mais populares",
          tags=["Twitch"])
async def twitch_get_top_games(request: TwitchTopGamesRequest):
    """
    Obtém a lista dos jogos mais populares na Twitch.
    
    Args:
        limit: Número de jogos a retornar (padrão: 100)
        
    Returns:
        dict: Lista dos jogos mais populares
    """
    try:
        check_twitch_credentials()
        result = data_twitch.get_top_games(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, request.limit)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        log.error(f"Erro em twitch_get_top_games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== MAIN =====================
if __name__ == "__main__":
    try:
        log.info("Iniciando Gaming API...")
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        log.error(f"Erro ao executar a API: {e}")
        traceback.print_exc(file=sys.stderr)
