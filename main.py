from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional, Union
import os
import sys
from dotenv import load_dotenv
import traceback

# Importando módulo local
try:
    import steam
    print("Módulo steam importado com sucesso", file=sys.stderr)
except ImportError as e:
    print(f"Erro ao importar steam: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# Carregar variáveis de ambiente
load_dotenv()

# Credenciais
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
if not STEAM_API_KEY:
    print("AVISO: STEAM_API_KEY não encontrada nas variáveis de ambiente!", file=sys.stderr)

# Inicializar FastAPI
app = FastAPI(
    title="Steam Games API",
    description="API para consultas de dados de jogos via Steam",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para requests
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

def get_custom_openapi():
    """Personaliza a descrição OpenAPI."""
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="Steam Games API",
        version="1.0.0",
        description="API para consultas de dados de jogos via Steam",
        routes=app.routes,
    )
    
    # Adiciona informações sobre o servidor
    openapi_schema["servers"] = [
        {"url": "https://agent-vgames.onrender.com", "description": "Servidor Render"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

@app.get("/openapi.json")
def custom_openapi_route():
    """Rota para a especificação OpenAPI personalizada."""
    return get_custom_openapi()

@app.get("/.well-known/openapi.json")
def mcp_openapi():
    """Rota para a especificação OpenAPI no formato exigido pelo MCP."""
    return get_custom_openapi()

# Sobrescreve a função openapi padrão do FastAPI
app.openapi = get_custom_openapi

# Helper function para processar app_ids
def process_app_ids(request_data) -> List[int]:
    """Processa app_ids ou app_id e retorna uma lista de inteiros."""
    app_ids = request_data.app_ids
    if not app_ids:
        if request_data.app_id:
            app_ids = [request_data.app_id]
        else:
            raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
    
    # Converter para lista de inteiros
    try:
        return [int(id) for id in app_ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="app_ids devem ser números válidos")

# ENDPOINTS STEAM
@app.post("/steam/game-data", 
         description="Obtém dados detalhados de jogos da Steam incluindo informações básicas, preço, gêneros, categorias e reviews básicos.",
         summary="Dados detalhados de jogos")
async def steam_game_data(request: GameDataRequest):
    """
    Obtém dados detalhados de jogos da Steam.
    """
    try:
        app_ids = process_app_ids(request)
        
        result = steam.get_steam_game_data(app_ids, request.language, request.max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em steam_game_data: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/current-players",
         description="Obtém o número atual de jogadores online para um jogo específico da Steam.",
         summary="Jogadores atuais online")
async def current_players(request: CurrentPlayersRequest):
    """
    Obtém o número atual de jogadores para um jogo específico.
    """
    try:
        # Converter para inteiro
        app_id = int(request.app_id)
        
        result = steam.get_current_players(app_id)
        return {"success": True, "data": {"current_players": result}}
    except Exception as e:
        print(f"Erro em current_players: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/historical-data",
         description="Obtém dados históricos de jogadores para jogos da Steam extraindo informações do SteamCharts.",
         summary="Dados históricos de jogadores")
async def historical_data(request: HistoricalDataRequest):
    """
    Obtém dados históricos de jogadores para jogos da Steam.
    """
    try:
        app_ids = process_app_ids(request)
        
        result = steam.get_historical_data_for_games(app_ids)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em historical_data: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/game-reviews",
         description="Coleta reviews detalhados de jogos da Steam incluindo texto, sentimento, ID do usuário e horas jogadas.",
         summary="Reviews de jogos")
async def game_reviews(request: GameReviewsRequest):
    """
    Obtém avaliações detalhadas de jogos da Steam.
    """
    try:
        app_ids = process_app_ids(request)
        
        result = steam.get_steam_game_reviews(app_ids, request.language, request.max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em game_reviews: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/recent-games",
         description="Obtém jogos recentes mais populares jogados por usuários que avaliaram um jogo específico. Requer STEAM_API_KEY.",
         summary="Jogos recentes de avaliadores")
async def recent_games(request: RecentGamesRequest):
    """
    Obtém jogos recentes jogados por usuários que avaliaram jogos específicos.
    """
    try:
        app_ids = process_app_ids(request)
        
        if not STEAM_API_KEY:
            raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada")
        
        result = steam.get_recent_games_for_multiple_apps(app_ids, STEAM_API_KEY, request.num_players)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em recent_games: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", 
        description="Endpoint raiz para verificar se a API está funcionando.",
        summary="Status da API")
async def root():
    """Endpoint raiz para verificar se a API está funcionando."""
    return {
        "message": "Steam Games API",
        "version": "1.0.0",
        "status": "running",
        "available_endpoints": {
            "POST /steam/game-data": "Dados detalhados de jogos",
            "POST /steam/current-players": "Jogadores atuais online",
            "POST /steam/historical-data": "Dados históricos de jogadores",
            "POST /steam/game-reviews": "Reviews de jogos",
            "POST /steam/recent-games": "Jogos recentes de avaliadores"
        }
    }

@app.get("/health",
        description="Endpoint de health check para monitoramento.",
        summary="Health Check")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "steam_api_configured": bool(STEAM_API_KEY)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"Iniciando servidor na porta {port}", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=port)
