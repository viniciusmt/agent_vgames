import requests
import pandas as pd
from bs4 import BeautifulSoup
from collections import Counter

import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
from collections import Counter
import json
import re

# ... código existente ...

def search_game_ids(game_names, max_results=10):
    """
    Busca os IDs de jogos na Steam baseado nos nomes.
    
    Args:
        game_names (list): Lista de nomes de jogos para buscar
        max_results (int): Número máximo de resultados por jogo
        
    Returns:
        pandas.DataFrame: DataFrame com nome do jogo, app_id e informações adicionais
    """
    all_results = []
    
    for game_name in game_names:
        try:
            # API de busca da Steam
            search_url = "https://store.steampowered.com/api/storesearch/"
            params = {
                "term": game_name,
                "l": "english",
                "cc": "US"
            }
            
            response = requests.get(search_url, params=params)
            data = response.json()
            
            if "items" in data:
                for item in data["items"][:max_results]:
                    all_results.append({
                        "search_term": game_name,
                        "app_id": item.get("id"),
                        "name": item.get("name"),
                        "price": item.get("price", {}).get("final", 0) / 100 if item.get("price") else 0,
                        "discount_percent": item.get("price", {}).get("discount_percent", 0),
                        "type": item.get("type", ""),
                        "platforms": {
                            "windows": item.get("platforms", {}).get("windows", False),
                            "mac": item.get("platforms", {}).get("mac", False),
                            "linux": item.get("platforms", {}).get("linux", False)
                        },
                        "release_date": item.get("release_date", {}).get("date") if item.get("release_date") else None,
                        "capsule_image": item.get("tiny_image", "")
                    })
            
        except Exception as e:
            print(f"Erro ao buscar '{game_name}': {e}")
            # Adiciona um registro de erro para não perder a busca
            all_results.append({
                "search_term": game_name,
                "app_id": None,
                "name": f"ERROR: {str(e)}",
                "price": 0,
                "discount_percent": 0,
                "type": "error",
                "platforms": {"windows": False, "mac": False, "linux": False},
                "release_date": None,
                "capsule_image": ""
            })
    
    return pd.DataFrame(all_results)

def get_game_details_by_name(game_name):
    """
    Busca detalhes de um jogo específico pelo nome.
    
    Args:
        game_name (str): Nome do jogo
        
    Returns:
        dict: Informações detalhadas do primeiro resultado encontrado
    """
    try:
        # Busca o ID primeiro
        search_results = search_game_ids([game_name], max_results=1)
        
        if search_results.empty or search_results.iloc[0]["app_id"] is None:
            return {
                "success": False,
                "error": f"Jogo '{game_name}' não encontrado"
            }
        
        app_id = search_results.iloc[0]["app_id"]
        
        # Busca detalhes completos usando o ID
        game_data = get_steam_game_data([app_id])
        
        if not game_data.empty:
            return {
                "success": True,
                "data": game_data.iloc[0].to_dict()
            }
        else:
            return {
                "success": False,
                "error": f"Não foi possível obter detalhes para '{game_name}'"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def search_games_advanced(query, filters=None):
    """
    Busca avançada de jogos com filtros opcionais.
    
    Args:
        query (str): Termo de busca
        filters (dict): Filtros opcionais como:
            - price_range: (min, max) - faixa de preço em USD
            - platforms: ['windows', 'mac', 'linux'] - plataformas
            - type: 'game' | 'dlc' | 'music' - tipo de item
            
    Returns:
        pandas.DataFrame: DataFrame com resultados filtrados
    """
    try:
        # Busca inicial
        results = search_game_ids([query], max_results=50)
        
        if filters and not results.empty:
            # Filtro por preço
            if "price_range" in filters:
                min_price, max_price = filters["price_range"]
                results = results[
                    (results["price"] >= min_price) & 
                    (results["price"] <= max_price)
                ]
            
            # Filtro por plataformas
            if "platforms" in filters:
                platform_filters = []
                for platform in filters["platforms"]:
                    if platform in ["windows", "mac", "linux"]:
                        platform_column = f"platforms_{platform}"
                        platform_filters.append(results["platforms"].str[platform] == True)
                
                if platform_filters:
                    # Aplicar OR para plataformas (jogo disponível em qualquer uma das plataformas)
                    platform_filter = platform_filters[0]
                    for pf in platform_filters[1:]:
                        platform_filter = platform_filter | pf
                    results = results[platform_filter]
            
            # Filtro por tipo
            if "type" in filters:
                results = results[results["type"] == filters["type"]]
        
        return results
        
    except Exception as e:
        print(f"Erro na busca avançada: {e}")
        return pd.DataFrame()

# ... resto do código existente ...
def get_current_players(app_id):
    url = f"http://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}"
    response = requests.get(url).json()
    return response.get('response', {}).get('player_count', 0)


def get_historical_data(game_id):
    base_url = f"https://steamcharts.com/app/{game_id}"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'common-table'})

    data = []
    if table:
        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            data.append([col.text.strip() for col in cols])

    headers = ['Mês', 'Jogadores Médios', 'Jogadores Pico', 'Alteração', 'Jogadores Delta']
    return pd.DataFrame(data, columns=headers)


def get_historical_data_for_games(app_ids):
    frames = []
    for app_id in app_ids:
        df = get_historical_data(app_id)
        df['AppID'] = app_id
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_steam_game_reviews(app_ids, language="portuguese", max_reviews=50):
    all_reviews = []
    for app_id in app_ids:
        try:
            cursor = "*"
            collected = 0
            while collected < max_reviews:
                params = {
                    "filter": "recent",
                    "language": language,
                    "review_type": "all",
                    "purchase_type": "all",
                    "num_per_page": 10,
                    "cursor": cursor
                }
                res = requests.get(f"https://store.steampowered.com/appreviews/{app_id}?json=1", params=params).json()
                for r in res.get("reviews", []):
                    author = r.get("author", {})
                    all_reviews.append({
                        "app_id": app_id,
                        "review": r.get("review"),
                        "user_id": author.get("steamid"),
                        "hours_played": author.get("playtime_forever", 0) / 60,
                        "sentiment": "positivo" if r.get("voted_up") else "negativo"
                    })
                    collected += 1
                    if collected >= max_reviews:
                        break
                if "cursor" not in res:
                    break
                cursor = res["cursor"]
        except Exception as e:
            print(f"Erro ao obter reviews de {app_id}: {e}")
    return pd.DataFrame(all_reviews)


def get_steam_game_data(app_ids, language="portuguese", max_reviews=50):
    all_data = []
    for app_id in app_ids:
        try:
            game_info = {
                "app_id": app_id,
                "name": "Desconhecido",
                "description": "",
                "release_date": "",
                "genres": [],
                "categories": [],
                "price": "",
                "current_players": 0,
                "total_reviews": 0,
                "review_score": "",
                "reviews": [],
                "pc_requirements_minimum": "",
                "pc_requirements_recommended": ""
            }
            details_res = requests.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}").json()
            if not details_res.get(str(app_id), {}).get("success"):
                raise ValueError(f"App ID inválido: {app_id}")
            data = details_res[str(app_id)]["data"]
            game_info.update({
                "name": data.get("name", "Desconhecido"),
                "description": data.get("short_description", ""),
                "release_date": data.get("release_date", {}).get("date", ""),
                "genres": [g["description"] for g in data.get("genres", [])],
                "categories": [c["description"] for c in data.get("categories", [])],
                "pc_requirements_minimum": data.get("pc_requirements", {}).get("minimum", ""),
                "pc_requirements_recommended": data.get("pc_requirements", {}).get("recommended", "")
            })
            if "price_overview" in data:
                game_info["price"] = data["price_overview"].get("final_formatted", "")
            game_info["current_players"] = get_current_players(app_id)
            reviews_res = requests.get(f"https://store.steampowered.com/appreviews/{app_id}?json=1", params={
                "filter": "recent",
                "language": language,
                "review_type": "all",
                "purchase_type": "all",
                "num_per_page": min(50, max_reviews)
            }).json()
            game_info["total_reviews"] = reviews_res.get("query_summary", {}).get("total_reviews", 0)
            game_info["review_score"] = reviews_res.get("query_summary", {}).get("review_score_desc", "")
            game_info["reviews"] = [r['review'] for r in reviews_res.get("reviews", [])]
            all_data.append(game_info)
        except Exception as e:
            print(f"Erro no app {app_id}: {e}")
    return pd.DataFrame(all_data)


def get_recent_games_from_reviewers(app_id, api_key, num_players=10):
    reviewers = []
    try:
        data = requests.get(f"https://store.steampowered.com/appreviews/{app_id}?json=1", params={"filter": "recent", "num_per_page": num_players}).json()
        reviewers = [r.get("author", {}).get("steamid") for r in data.get("reviews", []) if r.get("author", {}).get("steamid")]
    except Exception as e:
        print("Erro ao buscar revisores:", e)
        return pd.DataFrame(columns=["Nome do jogo", "ID_steam do jogo", "Contagem de jogadores"])
    games = []
    for sid in reviewers:
        try:
            res = requests.get("https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/", params={"key": api_key, "steamid": sid}).json()
            games += [{"name": g["name"], "appid": g["appid"]} for g in res.get("response", {}).get("games", [])]
        except Exception as e:
            print(f"Erro com usuário {sid}:", e)
    counter = Counter((g["name"], g["appid"]) for g in games)
    return pd.DataFrame([{"Nome do jogo": n, "ID_steam do jogo": a, "Contagem de jogadores": c} for (n, a), c in counter.items()])


def get_recent_games_for_multiple_apps(app_ids, api_key, num_players=10):
    results = []
    for app_id in app_ids:
        df = get_recent_games_from_reviewers(app_id, api_key, num_players)
        if not df.empty:
            df["Origem do App"] = app_id
            results.append(df)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["Nome do jogo", "ID_steam do jogo", "Contagem de jogadores", "Origem do App"])
