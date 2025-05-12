from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os
import sys
from typing import List, Dict, Any, Optional, Union
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

# ENDPOINTS STEAM
@app.post("/steam/game-data", 
         description="Obtém dados detalhados de jogos da Steam incluindo informações básicas, preço, gêneros, categorias e reviews básicos.",
         summary="Dados detalhados de jogos")
async def steam_game_data(request: Request):
    """
    Obtém dados detalhados de jogos da Steam.
    
    Body Parameters:
    - app_ids (list) ou app_id (int/str): ID(s) de jogos na Steam
    - language (str, optional): Idioma para as descrições e reviews (padrão: portuguese)  
    - max_reviews (int, optional): Número máximo de reviews a serem coletados (padrão: 50)
    
    Returns:
    - Dados detalhados dos jogos incluindo nome, descrição, preço, gêneros, categorias, reviews
    """
    try:
        body = await request.json()
        
        # Aceita tanto app_ids (lista) quanto app_id (único)
        app_ids = body.get("app_ids")
        if not app_ids:
            app_id = body.get("app_id")
            if app_id:
                app_ids = [int(app_id)]
            else:
                raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
        
        # Garantir que sejam inteiros
        app_ids = [int(id) for id in app_ids] if isinstance(app_ids, list) else [int(app_ids)]
        
        language = body.get("language", "portuguese")
        max_reviews = body.get("max_reviews", 50)
        
        result = steam.get_steam_game_data(app_ids, language, max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em steam_game_data: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/current-players",
         description="Obtém o número atual de jogadores online para um jogo específico da Steam.",
         summary="Jogadores atuais online")
async def current_players(request: Request):
    """
    Obtém o número atual de jogadores para um jogo específico.
    
    Body Parameters:
    - app_id (int/str): ID do jogo na Steam
    
    Returns:
    - Número atual de jogadores online no jogo
    """
    try:
        body = await request.json()
        app_id = body.get("app_id")
        
        if not app_id:
            raise HTTPException(status_code=400, detail="app_id é obrigatório")
        
        # Converter para inteiro
        app_id = int(app_id)
        
        result = steam.get_current_players(app_id)
        return {"success": True, "data": {"current_players": result}}
    except Exception as e:
        print(f"Erro em current_players: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/historical-data",
         description="Obtém dados históricos de jogadores para jogos da Steam extraindo informações do SteamCharts.",
         summary="Dados históricos de jogadores")
async def historical_data(request: Request):
    """
    Obtém dados históricos de jogadores para jogos da Steam.
    
    Body Parameters:
    - app_ids (list) ou app_id (int/str): ID(s) de jogos na Steam
    
    Returns:
    - Dados históricos incluindo jogadores médios, pico, alterações mensais
    """
    try:
        body = await request.json()
        
        # Aceita tanto app_ids (lista) quanto app_id (único)
        app_ids = body.get("app_ids")
        if not app_ids:
            app_id = body.get("app_id")
            if app_id:
                app_ids = [int(app_id)]
            else:
                raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
        
        # Garantir que sejam inteiros
        app_ids = [int(id) for id in app_ids] if isinstance(app_ids, list) else [int(app_ids)]
        
        result = steam.get_historical_data_for_games(app_ids)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em historical_data: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/game-reviews",
         description="Coleta reviews detalhados de jogos da Steam incluindo texto, sentimento, ID do usuário e horas jogadas.",
         summary="Reviews de jogos")
async def game_reviews(request: Request):
    """
    Obtém avaliações detalhadas de jogos da Steam.
    
    Body Parameters:
    - app_ids (list) ou app_id (int/str): ID(s) de jogos na Steam
    - language (str, optional): Idioma das avaliações (padrão: portuguese)
    - max_reviews (int, optional): Número máximo de avaliações por jogo (padrão: 50)
    
    Returns:
    - Lista de reviews com texto, sentimento (positivo/negativo), ID do usuário, horas jogadas
    """
    try:
        body = await request.json()
        
        # Aceita tanto app_ids (lista) quanto app_id (único)
        app_ids = body.get("app_ids")
        if not app_ids:
            app_id = body.get("app_id")
            if app_id:
                app_ids = [int(app_id)]
            else:
                raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
        
        # Garantir que sejam inteiros
        app_ids = [int(id) for id in app_ids] if isinstance(app_ids, list) else [int(app_ids)]
        
        language = body.get("language", "portuguese")
        max_reviews = body.get("max_reviews", 50)
        
        result = steam.get_steam_game_reviews(app_ids, language, max_reviews)
        return {"success": True, "data": result.to_dict("records")}
    except Exception as e:
        print(f"Erro em game_reviews: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/steam/recent-games",
         description="Obtém jogos recentes mais populares jogados por usuários que avaliaram um jogo específico. Requer STEAM_API_KEY.",
         summary="Jogos recentes de avaliadores")
async def recent_games(request: Request):
    """
    Obtém jogos recentes jogados por usuários que avaliaram jogos específicos.
    
    Body Parameters:
    - app_ids (list) ou app_id (int/str): ID(s) de jogos na Steam
    - num_players (int, optional): Número de jogadores a analisar (padrão: 10)
    
    Returns:
    - Lista de jogos populares com nome, ID e contagem de jogadores que os jogaram recentemente
    """
    try:
        body = await request.json()
        
        # Aceita tanto app_ids (lista) quanto app_id (único)
        app_ids = body.get("app_ids")
        if not app_ids:
            app_id = body.get("app_id")
            if app_id:
                app_ids = [int(app_id)]
            else:
                raise HTTPException(status_code=400, detail="app_ids ou app_id é obrigatório")
        
        # Garantir que sejam inteiros
        app_ids = [int(id) for id in app_ids] if isinstance(app_ids, list) else [int(app_ids)]
        
        num_players = body.get("num_players", 10)
        
        if not STEAM_API_KEY:
            raise HTTPException(status_code=500, detail="STEAM_API_KEY não configurada")
        
        result = steam.get_recent_games_for_multiple_apps(app_ids, STEAM_API_KEY, num_players)
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
