import requests
import pandas as pd
import logging
import sys
import os
from typing import List, Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger(__name__)

# Obtém credenciais das variáveis de ambiente
TWITCH_CLIENT_ID = os.getenv("TWITCH_API_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_API_CLIENT_SECRET")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN")
TWITCH_TOKEN_URL = os.getenv("TWITCH_TOKEN_URL", "https://id.twitch.tv/oauth2/token")

def get_access_token(client_id: str = None, client_secret: str = None, token_url: str = None) -> str:
    """
    Obtém token de acesso da API da Twitch
    
    Args:
        client_id: ID do cliente (opcional, usa variável de ambiente se não fornecido)
        client_secret: Secret do cliente (opcional, usa variável de ambiente se não fornecido)
        token_url: URL para obter token (opcional, usa variável de ambiente se não fornecido)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    token_url = token_url or TWITCH_TOKEN_URL
    
    if not client_id or not client_secret:
        raise ValueError("Credenciais da Twitch não encontradas. Configure TWITCH_API_CLIENT_ID e TWITCH_API_CLIENT_SECRET")
    
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(token_url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]

def refresh_access_token(refresh_token: str = None, client_id: str = None, 
                        client_secret: str = None, token_url: str = None) -> dict:
    """
    Atualiza o token de acesso usando um refresh token
    
    Args:
        refresh_token: Token de refresh (opcional, usa variável de ambiente se não fornecido)
        client_id: ID do cliente (opcional, usa variável de ambiente se não fornecido)
        client_secret: Secret do cliente (opcional, usa variável de ambiente se não fornecido)
        token_url: URL para refresh (opcional, usa variável de ambiente se não fornecido)
        
    Returns:
        dict: Nova resposta com access_token e refresh_token
    """
    refresh_token = refresh_token or TWITCH_REFRESH_TOKEN
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    token_url = token_url or TWITCH_TOKEN_URL
    
    if not refresh_token:
        raise ValueError("Refresh token não encontrado. Configure TWITCH_REFRESH_TOKEN")
    
    if not client_id or not client_secret:
        raise ValueError("Credenciais da Twitch não encontradas")
    
    params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    response = requests.post(token_url, params=params)
    response.raise_for_status()
    return response.json()

def get_user_access_token(authorization_code: str, redirect_uri: str, 
                         client_id: str = None, client_secret: str = None, 
                         token_url: str = None) -> dict:
    """
    Obtém token de acesso de usuário usando código de autorização
    
    Args:
        authorization_code: Código de autorização recebido da Twitch
        redirect_uri: URI de redirecionamento registrada
        client_id: ID do cliente (opcional, usa variável de ambiente se não fornecido)
        client_secret: Secret do cliente (opcional, usa variável de ambiente se não fornecido)
        token_url: URL para token (opcional, usa variável de ambiente se não fornecido)
        
    Returns:
        dict: Resposta com access_token, refresh_token e outros dados
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    token_url = token_url or TWITCH_TOKEN_URL
    
    if not client_id or not client_secret:
        raise ValueError("Credenciais da Twitch não encontradas")
    
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    response = requests.post(token_url, params=params)
    response.raise_for_status()
    return response.json()

def validate_token(access_token: str) -> dict:
    """
    Valida um token de acesso
    
    Args:
        access_token: Token a ser validado
        
    Returns:
        dict: Informações sobre o token
    """
    headers = {"Authorization": f"OAuth {access_token}"}
    response = requests.get("https://id.twitch.tv/oauth2/validate", headers=headers)
    response.raise_for_status()
    return response.json()

def search_game_ids(game_names: List[str], client_id: str = None, client_secret: str = None, 
                   access_token: str = None) -> pd.DataFrame:
    """
    Busca IDs de jogos na Twitch baseado nos nomes
    
    Args:
        game_names: Lista de nomes de jogos
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    for game_name in game_names:
        url = "https://api.twitch.tv/helix/games"
        params = {"name": game_name}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                for game in data["data"]:
                    results.append({
                        "search_term": game_name,
                        "id": game["id"],
                        "name": game["name"],
                        "box_art_url": game["box_art_url"]
                    })
            else:
                log.warning(f"Jogo não encontrado: {game_name}")
                results.append({
                    "search_term": game_name,
                    "id": None,
                    "name": f"NOT_FOUND: {game_name}",
                    "box_art_url": ""
                })
        except Exception as e:
            log.error(f"Erro ao buscar {game_name}: {e}")
            results.append({
                "search_term": game_name,
                "id": None,
                "name": f"ERROR: {str(e)}",
                "box_art_url": ""
            })
    
    return pd.DataFrame(results)

def get_twitch_channel_data_bulk(channel_names: List[str], client_id: str = None, 
                                client_secret: str = None, access_token: str = None) -> pd.DataFrame:
    """
    Obtém informações de múltiplos canais da Twitch
    
    Args:
        channel_names: Lista de nomes de canais
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # A API aceita até 100 usuários por vez
    results = []
    chunk_size = 100
    
    for i in range(0, len(channel_names), chunk_size):
        chunk = channel_names[i:i + chunk_size]
        url = "https://api.twitch.tv/helix/users"
        params = {"login": chunk}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for user in data.get("data", []):
                results.append({
                    "id": user["id"],
                    "login": user["login"],
                    "display_name": user["display_name"],
                    "type": user["type"],
                    "broadcaster_type": user["broadcaster_type"],
                    "description": user["description"],
                    "profile_image_url": user["profile_image_url"],
                    "offline_image_url": user["offline_image_url"],
                    "view_count": user["view_count"],
                    "created_at": user["created_at"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar canais {chunk}: {e}")
    
    return pd.DataFrame(results)

def get_twitch_game_data(game_name: str, client_id: str = None, client_secret: str = None, 
                        access_token: str = None) -> dict:
    """
    Obtém informações detalhadas de um jogo na Twitch
    
    Args:
        game_name: Nome do jogo
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # Busca o jogo
    url = "https://api.twitch.tv/helix/games"
    params = {"name": game_name}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return {"success": False, "error": f"Jogo '{game_name}' não encontrado"}
        
        game = data["data"][0]
        
        # Busca streams do jogo
        streams_url = "https://api.twitch.tv/helix/streams"
        streams_params = {"game_id": game["id"], "first": 20}
        
        streams_response = requests.get(streams_url, headers=headers, params=streams_params)
        streams_response.raise_for_status()
        streams_data = streams_response.json()
        
        return {
            "success": True,
            "game_info": {
                "id": game["id"],
                "name": game["name"],
                "box_art_url": game["box_art_url"]
            },
            "streams_count": len(streams_data.get("data", [])),
            "total_viewers": sum(stream["viewer_count"] for stream in streams_data.get("data", []))
        }
    except Exception as e:
        log.error(f"Erro ao obter dados do jogo {game_name}: {e}")
        return {"success": False, "error": str(e)}

def get_live_streams_for_games(game_ids: List[str], client_id: str = None, client_secret: str = None, 
                               language: str = "pt", limit: int = 100, access_token: str = None) -> pd.DataFrame:
    """
    Busca streams ao vivo para uma lista de jogos
    
    Args:
        game_ids: Lista de IDs dos jogos
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        language: Idioma das streams
        limit: Limite de streams por jogo
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    
    for game_id in game_ids:
        url = "https://api.twitch.tv/helix/streams"
        params = {
            "game_id": game_id,
            "language": language,
            "first": min(100, limit)  # API limite de 100 por request
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for stream in data.get("data", []):
                results.append({
                    "stream_id": stream["id"],
                    "user_id": stream["user_id"],
                    "user_login": stream["user_login"],
                    "user_name": stream["user_name"],
                    "game_id": stream["game_id"],
                    "game_name": stream["game_name"],
                    "type": stream["type"],
                    "title": stream["title"],
                    "viewer_count": stream["viewer_count"],
                    "started_at": stream["started_at"],
                    "language": stream["language"],
                    "thumbnail_url": stream["thumbnail_url"],
                    "is_mature": stream["is_mature"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar streams para jogo {game_id}: {e}")
    
    return pd.DataFrame(results)

def get_top_games(client_id: str = None, client_secret: str = None, limit: int = 100, 
                  access_token: str = None) -> pd.DataFrame:
    """
    Obtém a lista dos jogos mais populares na Twitch
    
    Args:
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        limit: Número de jogos a retornar
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    url = "https://api.twitch.tv/helix/games/top"
    params = {"first": min(100, limit)}  # API limite de 100
    
    try:
        while len(results) < limit:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for game in data.get("data", []):
                if len(results) >= limit:
                    break
                results.append({
                    "id": game["id"],
                    "name": game["name"],
                    "box_art_url": game["box_art_url"]
                })
            
            # Pagination
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
                
        # Adiciona dados de viewers para cada jogo
        for i, game in enumerate(results):
            try:
                streams_url = "https://api.twitch.tv/helix/streams"
                streams_params = {"game_id": game["id"], "first": 100}
                
                streams_response = requests.get(streams_url, headers=headers, params=streams_params)
                streams_response.raise_for_status()
                streams_data = streams_response.json()
                
                total_viewers = sum(stream["viewer_count"] for stream in streams_data.get("data", []))
                stream_count = len(streams_data.get("data", []))
                
                results[i]["viewer_count"] = total_viewers
                results[i]["stream_count"] = stream_count
            except Exception as e:
                log.error(f"Erro ao obter viewers para {game['name']}: {e}")
                results[i]["viewer_count"] = 0
                results[i]["stream_count"] = 0
                
    except Exception as e:
        log.error(f"Erro ao obter top games: {e}")
        raise
    
    return pd.DataFrame(results)

def get_game_streams_summary(game_id: str, client_id: str = None, client_secret: str = None, 
                           access_token: str = None) -> dict:
    """
    Obtém token de acesso da API da Twitch
    
    Args:
        client_id: ID do cliente (opcional, usa variável de ambiente se não fornecido)
        client_secret: Secret do cliente (opcional, usa variável de ambiente se não fornecido)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    if not client_id or not client_secret:
        raise ValueError("Credenciais da Twitch não encontradas. Configure TWITCH_API_CLIENT_ID e TWITCH_API_CLIENT_SECRET")
    
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]

def search_game_ids(game_names: List[str], client_id: str = None, client_secret: str = None) -> pd.DataFrame:
    """
    Busca IDs de jogos na Twitch baseado nos nomes
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    for game_name in game_names:
        url = "https://api.twitch.tv/helix/games"
        params = {"name": game_name}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                for game in data["data"]:
                    results.append({
                        "search_term": game_name,
                        "id": game["id"],
                        "name": game["name"],
                        "box_art_url": game["box_art_url"]
                    })
            else:
                log.warning(f"Jogo não encontrado: {game_name}")
                results.append({
                    "search_term": game_name,
                    "id": None,
                    "name": f"NOT_FOUND: {game_name}",
                    "box_art_url": ""
                })
        except Exception as e:
            log.error(f"Erro ao buscar {game_name}: {e}")
            results.append({
                "search_term": game_name,
                "id": None,
                "name": f"ERROR: {str(e)}",
                "box_art_url": ""
            })
    
    return pd.DataFrame(results)

def get_twitch_channel_data_bulk(channel_names: List[str], client_id: str = None, client_secret: str = None) -> pd.DataFrame:
    """
    Obtém informações de múltiplos canais da Twitch
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # A API aceita até 100 usuários por vez
    results = []
    chunk_size = 100
    
    for i in range(0, len(channel_names), chunk_size):
        chunk = channel_names[i:i + chunk_size]
        url = "https://api.twitch.tv/helix/users"
        params = {"login": chunk}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for user in data.get("data", []):
                results.append({
                    "id": user["id"],
                    "login": user["login"],
                    "display_name": user["display_name"],
                    "type": user["type"],
                    "broadcaster_type": user["broadcaster_type"],
                    "description": user["description"],
                    "profile_image_url": user["profile_image_url"],
                    "offline_image_url": user["offline_image_url"],
                    "view_count": user["view_count"],
                    "created_at": user["created_at"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar canais {chunk}: {e}")
    
    return pd.DataFrame(results)

def get_twitch_game_data(game_name: str, client_id: str = None, client_secret: str = None) -> dict:
    """
    Obtém informações detalhadas de um jogo na Twitch
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # Busca o jogo
    url = "https://api.twitch.tv/helix/games"
    params = {"name": game_name}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return {"success": False, "error": f"Jogo '{game_name}' não encontrado"}
        
        game = data["data"][0]
        
        # Busca streams do jogo
        streams_url = "https://api.twitch.tv/helix/streams"
        streams_params = {"game_id": game["id"], "first": 20}
        
        streams_response = requests.get(streams_url, headers=headers, params=streams_params)
        streams_response.raise_for_status()
        streams_data = streams_response.json()
        
        return {
            "success": True,
            "game_info": {
                "id": game["id"],
                "name": game["name"],
                "box_art_url": game["box_art_url"]
            },
            "streams_count": len(streams_data.get("data", [])),
            "total_viewers": sum(stream["viewer_count"] for stream in streams_data.get("data", []))
        }
    except Exception as e:
        log.error(f"Erro ao obter dados do jogo {game_name}: {e}")
        return {"success": False, "error": str(e)}

def get_live_streams_for_games(game_ids: List[str], client_id: str = None, client_secret: str = None, 
                               language: str = "pt", limit: int = 100) -> pd.DataFrame:
    """
    Busca streams ao vivo para uma lista de jogos
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    
    for game_id in game_ids:
        url = "https://api.twitch.tv/helix/streams"
        params = {
            "game_id": game_id,
            "language": language,
            "first": min(100, limit)  # API limite de 100 por request
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for stream in data.get("data", []):
                results.append({
                    "stream_id": stream["id"],
                    "user_id": stream["user_id"],
                    "user_login": stream["user_login"],
                    "user_name": stream["user_name"],
                    "game_id": stream["game_id"],
                    "game_name": stream["game_name"],
                    "type": stream["type"],
                    "title": stream["title"],
                    "viewer_count": stream["viewer_count"],
                    "started_at": stream["started_at"],
                    "language": stream["language"],
                    "thumbnail_url": stream["thumbnail_url"],
                    "is_mature": stream["is_mature"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar streams para jogo {game_id}: {e}")
    
    return pd.DataFrame(results)

def get_top_games(client_id: str = None, client_secret: str = None, limit: int = 100) -> pd.DataFrame:
    """
    Obtém a lista dos jogos mais populares na Twitch
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    url = "https://api.twitch.tv/helix/games/top"
    params = {"first": min(100, limit)}  # API limite de 100
    
    try:
        while len(results) < limit:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for game in data.get("data", []):
                if len(results) >= limit:
                    break
                results.append({
                    "id": game["id"],
                    "name": game["name"],
                    "box_art_url": game["box_art_url"]
                })
            
            # Pagination
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
                
        # Adiciona dados de viewers para cada jogo
        for i, game in enumerate(results):
            try:
                streams_url = "https://api.twitch.tv/helix/streams"
                streams_params = {"game_id": game["id"], "first": 100}
                
                streams_response = requests.get(streams_url, headers=headers, params=streams_params)
                streams_response.raise_for_status()
                streams_data = streams_response.json()
                
                total_viewers = sum(stream["viewer_count"] for stream in streams_data.get("data", []))
                stream_count = len(streams_data.get("data", []))
                
                results[i]["viewer_count"] = total_viewers
                results[i]["stream_count"] = stream_count
            except Exception as e:
                log.error(f"Erro ao obter viewers para {game['name']}: {e}")
                results[i]["viewer_count"] = 0
                results[i]["stream_count"] = 0
                
    except Exception as e:
        log.error(f"Erro ao obter top games: {e}")
        raise
    
    return pd.DataFrame(results)

def get_game_streams_summary(game_id: str, client_id: str = None, client_secret: str = None, 
                           access_token: str = None) -> dict:
    """
    Obtém um resumo das streams de um jogo específico
    
    Args:
        game_id: ID do jogo
        client_id: ID do cliente (opcional)
        client_secret: Secret do cliente (opcional)
        access_token: Token de acesso pré-obtido (opcional)
    """
    client_id = client_id or TWITCH_CLIENT_ID
    
    if access_token:
        token = access_token
    else:
        client_secret = client_secret or TWITCH_CLIENT_SECRET
        token = get_access_token(client_id, client_secret)
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    url = "https://api.twitch.tv/helix/streams"
    params = {"game_id": game_id, "first": 100}
    
    try:
        all_streams = []
        
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            all_streams.extend(data.get("data", []))
            
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
        
        total_viewers = sum(stream["viewer_count"] for stream in all_streams)
        languages = {}
        
        for stream in all_streams:
            lang = stream.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "game_id": game_id,
            "total_streams": len(all_streams),
            "total_viewers": total_viewers,
            "average_viewers": total_viewers / len(all_streams) if all_streams else 0,
            "languages": languages,
            "top_streamers": sorted(
                [{"user_name": s["user_name"], "viewer_count": s["viewer_count"]} 
                 for s in all_streams],
                key=lambda x: x["viewer_count"],
                reverse=True
            )[:10]
        }
    except Exception as e:
        log.error(f"Erro ao obter resumo para game_id {game_id}: {e}")
        return {"game_id": game_id, "error": str(e)}
    """
    Obtém um resumo das streams de um jogo específico
    """
    client_id = client_id or TWITCH_CLIENT_ID
    client_secret = client_secret or TWITCH_CLIENT_SECRET
    
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    url = "https://api.twitch.tv/helix/streams"
    params = {"game_id": game_id, "first": 100}
    
    try:
        all_streams = []
        
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            all_streams.extend(data.get("data", []))
            
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
        
        total_viewers = sum(stream["viewer_count"] for stream in all_streams)
        languages = {}
        
        for stream in all_streams:
            lang = stream.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "game_id": game_id,
            "total_streams": len(all_streams),
            "total_viewers": total_viewers,
            "average_viewers": total_viewers / len(all_streams) if all_streams else 0,
            "languages": languages,
            "top_streamers": sorted(
                [{"user_name": s["user_name"], "viewer_count": s["viewer_count"]} 
                 for s in all_streams],
                key=lambda x: x["viewer_count"],
                reverse=True
            )[:10]
        }
    except Exception as e:
        log.error(f"Erro ao obter resumo para game_id {game_id}: {e}")
        return {"game_id": game_id, "error": str(e)}

# Função auxiliar para converter box art URLs
def format_box_art_url(url: str, width: int = 300, height: int = 400) -> str:
    """
    Converte URL de box art da Twitch para tamanho específico
    """
    if url:
        return url.replace("{width}", str(width)).replace("{height}", str(height))
    return url

# Função auxiliar para converter thumbnail URLs
def format_thumbnail_url(url: str, width: int = 640, height: int = 360) -> str:
    """
    Converte URL de thumbnail da Twitch para tamanho específico
    """
    if url:
        return url.replace("{width}", str(width)).replace("{height}", str(height))
    return url
    """
    Obtém token de acesso da API da Twitch
    """
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]

def search_game_ids(game_names: List[str], client_id: str, client_secret: str) -> pd.DataFrame:
    """
    Busca IDs de jogos na Twitch baseado nos nomes
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    for game_name in game_names:
        url = "https://api.twitch.tv/helix/games"
        params = {"name": game_name}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                for game in data["data"]:
                    results.append({
                        "search_term": game_name,
                        "id": game["id"],
                        "name": game["name"],
                        "box_art_url": game["box_art_url"]
                    })
            else:
                log.warning(f"Jogo não encontrado: {game_name}")
                results.append({
                    "search_term": game_name,
                    "id": None,
                    "name": f"NOT_FOUND: {game_name}",
                    "box_art_url": ""
                })
        except Exception as e:
            log.error(f"Erro ao buscar {game_name}: {e}")
            results.append({
                "search_term": game_name,
                "id": None,
                "name": f"ERROR: {str(e)}",
                "box_art_url": ""
            })
    
    return pd.DataFrame(results)

def get_twitch_channel_data_bulk(channel_names: List[str], client_id: str, client_secret: str) -> pd.DataFrame:
    """
    Obtém informações de múltiplos canais da Twitch
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # A API aceita até 100 usuários por vez
    results = []
    chunk_size = 100
    
    for i in range(0, len(channel_names), chunk_size):
        chunk = channel_names[i:i + chunk_size]
        url = "https://api.twitch.tv/helix/users"
        params = {"login": chunk}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for user in data.get("data", []):
                results.append({
                    "id": user["id"],
                    "login": user["login"],
                    "display_name": user["display_name"],
                    "type": user["type"],
                    "broadcaster_type": user["broadcaster_type"],
                    "description": user["description"],
                    "profile_image_url": user["profile_image_url"],
                    "offline_image_url": user["offline_image_url"],
                    "view_count": user["view_count"],
                    "created_at": user["created_at"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar canais {chunk}: {e}")
    
    return pd.DataFrame(results)

def get_twitch_game_data(game_name: str, client_id: str, client_secret: str) -> dict:
    """
    Obtém informações detalhadas de um jogo na Twitch
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    # Busca o jogo
    url = "https://api.twitch.tv/helix/games"
    params = {"name": game_name}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return {"success": False, "error": f"Jogo '{game_name}' não encontrado"}
        
        game = data["data"][0]
        
        # Busca streams do jogo
        streams_url = "https://api.twitch.tv/helix/streams"
        streams_params = {"game_id": game["id"], "first": 20}
        
        streams_response = requests.get(streams_url, headers=headers, params=streams_params)
        streams_response.raise_for_status()
        streams_data = streams_response.json()
        
        return {
            "success": True,
            "game_info": {
                "id": game["id"],
                "name": game["name"],
                "box_art_url": game["box_art_url"]
            },
            "streams_count": len(streams_data.get("data", [])),
            "total_viewers": sum(stream["viewer_count"] for stream in streams_data.get("data", []))
        }
    except Exception as e:
        log.error(f"Erro ao obter dados do jogo {game_name}: {e}")
        return {"success": False, "error": str(e)}

def get_live_streams_for_games(game_ids: List[str], client_id: str, client_secret: str, 
                               language: str = "pt", limit: int = 100) -> pd.DataFrame:
    """
    Busca streams ao vivo para uma lista de jogos
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    
    for game_id in game_ids:
        url = "https://api.twitch.tv/helix/streams"
        params = {
            "game_id": game_id,
            "language": language,
            "first": min(100, limit)  # API limite de 100 por request
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for stream in data.get("data", []):
                results.append({
                    "stream_id": stream["id"],
                    "user_id": stream["user_id"],
                    "user_login": stream["user_login"],
                    "user_name": stream["user_name"],
                    "game_id": stream["game_id"],
                    "game_name": stream["game_name"],
                    "type": stream["type"],
                    "title": stream["title"],
                    "viewer_count": stream["viewer_count"],
                    "started_at": stream["started_at"],
                    "language": stream["language"],
                    "thumbnail_url": stream["thumbnail_url"],
                    "is_mature": stream["is_mature"]
                })
        except Exception as e:
            log.error(f"Erro ao buscar streams para jogo {game_id}: {e}")
    
    return pd.DataFrame(results)

def get_top_games(client_id: str, client_secret: str, limit: int = 100) -> pd.DataFrame:
    """
    Obtém a lista dos jogos mais populares na Twitch
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    results = []
    url = "https://api.twitch.tv/helix/games/top"
    params = {"first": min(100, limit)}  # API limite de 100
    
    try:
        while len(results) < limit:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for game in data.get("data", []):
                if len(results) >= limit:
                    break
                results.append({
                    "id": game["id"],
                    "name": game["name"],
                    "box_art_url": game["box_art_url"]
                })
            
            # Pagination
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
                
        # Adiciona dados de viewers para cada jogo
        for i, game in enumerate(results):
            try:
                streams_url = "https://api.twitch.tv/helix/streams"
                streams_params = {"game_id": game["id"], "first": 100}
                
                streams_response = requests.get(streams_url, headers=headers, params=streams_params)
                streams_response.raise_for_status()
                streams_data = streams_response.json()
                
                total_viewers = sum(stream["viewer_count"] for stream in streams_data.get("data", []))
                stream_count = len(streams_data.get("data", []))
                
                results[i]["viewer_count"] = total_viewers
                results[i]["stream_count"] = stream_count
            except Exception as e:
                log.error(f"Erro ao obter viewers para {game['name']}: {e}")
                results[i]["viewer_count"] = 0
                results[i]["stream_count"] = 0
                
    except Exception as e:
        log.error(f"Erro ao obter top games: {e}")
        raise
    
    return pd.DataFrame(results)

def get_game_streams_summary(game_id: str, client_id: str, client_secret: str) -> dict:
    """
    Obtém um resumo das streams de um jogo específico
    """
    token = get_access_token(client_id, client_secret)
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }
    
    url = "https://api.twitch.tv/helix/streams"
    params = {"game_id": game_id, "first": 100}
    
    try:
        all_streams = []
        
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            all_streams.extend(data.get("data", []))
            
            if "pagination" in data and "cursor" in data["pagination"]:
                params["after"] = data["pagination"]["cursor"]
            else:
                break
        
        total_viewers = sum(stream["viewer_count"] for stream in all_streams)
        languages = {}
        
        for stream in all_streams:
            lang = stream.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "game_id": game_id,
            "total_streams": len(all_streams),
            "total_viewers": total_viewers,
            "average_viewers": total_viewers / len(all_streams) if all_streams else 0,
            "languages": languages,
            "top_streamers": sorted(
                [{"user_name": s["user_name"], "viewer_count": s["viewer_count"]} 
                 for s in all_streams],
                key=lambda x: x["viewer_count"],
                reverse=True
            )[:10]
        }
    except Exception as e:
        log.error(f"Erro ao obter resumo para game_id {game_id}: {e}")
        return {"game_id": game_id, "error": str(e)}

# Função auxiliar para converter box art URLs
def format_box_art_url(url: str, width: int = 300, height: int = 400) -> str:
    """
    Converte URL de box art da Twitch para tamanho específico
    """
    if url:
        return url.replace("{width}", str(width)).replace("{height}", str(height))
    return url

# Função auxiliar para converter thumbnail URLs
def format_thumbnail_url(url: str, width: int = 640, height: int = 360) -> str:
    """
    Converte URL de thumbnail da Twitch para tamanho específico
    """
    if url:
        return url.replace("{width}", str(width)).replace("{height}", str(height))
    return url
