import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
from collections import Counter

def get_current_players(app_id):
    """
    Obtém o número atual de jogadores para um jogo específico da Steam.
    
    Args:
        app_id (int): ID do aplicativo na Steam
    
    Returns:
        int: Número atual de jogadores
    """
    url = f"http://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}"
    response = requests.get(url).json()
    if response and 'response' in response:
        return response['response'].get('player_count', 0)
    return 0

def get_historical_data(game_id):
    """
    Obtém dados históricos de jogadores para um jogo específico da Steam.
    
    Args:
        game_id (int): ID do jogo na Steam
    
    Returns:
        DataFrame: Dados históricos formatados
    """
    base_url = f"https://steamcharts.com/app/{game_id}"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'class': 'common-table'})
    data = []

    if table:
        rows = table.find_all('tr')[1:]  # Ignorar o cabeçalho
        for row in rows:
            cols = row.find_all('td')
            data.append([col.text.strip() for col in cols])

    headers = ['Mês', 'Jogadores Médios', 'Jogadores Pico', 'Alteração', 'Jogadores Delta']
    return pd.DataFrame(data, columns=headers)

def get_historical_data_for_games(app_ids):
    """
    Obtém dados históricos para múltiplos jogos da Steam.
    
    Args:
        app_ids (list): Lista de IDs de jogos na Steam
    
    Returns:
        DataFrame: Dados históricos consolidados
    """
    aggregated_data = pd.DataFrame()

    for app_id in app_ids:
        print(f"Coletando dados para o AppID: {app_id}...")
        game_data = get_historical_data(app_id)
        game_data['AppID'] = app_id  # Adiciona o AppID como uma coluna para identificar o jogo
        aggregated_data = pd.concat([aggregated_data, game_data], ignore_index=True)

    return aggregated_data

def get_steam_game_reviews(app_ids, language="portuguese", max_reviews=50):
    """
    Coleta reviews, ID do usuário, horas jogadas e classificação (positiva ou negativa)
    para uma lista de jogos na Steam.
    
    Args:
        app_ids (list): Lista de IDs de jogos na Steam
        language (str): Idioma dos reviews a serem coletados (padrão: portuguese)
        max_reviews (int): Número máximo de reviews a coletar por jogo
    
    Returns:
        DataFrame: DataFrame com colunas: app_id, review, user_id, hours_played, sentiment
    """
    reviews_data = []

    for app_id in app_ids:
        try:
            # Obter reviews
            reviews_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1"
            cursor = "*"
            reviews_collected = 0

            while reviews_collected < max_reviews:
                params = {
                    "filter": "recent",
                    "language": language,
                    "review_type": "all",
                    "purchase_type": "all",
                    "num_per_page": 10,
                    "cursor": cursor,
                }
                reviews_response = requests.get(reviews_url, params=params).json()

                if "reviews" in reviews_response:
                    for review in reviews_response.get("reviews", []):
                        author = review.get("author", {})
                        voted_up = review.get("voted_up")

                        sentiment = "positivo" if voted_up else "negativo"

                        reviews_data.append({
                            "app_id": app_id,
                            "review": review.get("review"),
                            "user_id": author.get("steamid"),
                            "hours_played": author.get("playtime_forever", 0) / 60.0,  # Convertendo minutos para horas
                            "sentiment": sentiment,
                        })
                        reviews_collected += 1
                        if reviews_collected >= max_reviews:
                            break

                if "cursor" in reviews_response:
                    cursor = reviews_response["cursor"]
                else:
                    break

        except Exception as e:
            print(f"Erro ao processar os reviews do jogo {app_id}: {e}")

    # Converter para DataFrame
    reviews_detail_df = pd.DataFrame(reviews_data)
    return reviews_detail_df

def get_steam_game_data(app_ids, language="portuguese", max_reviews=100):
    """
    Obtém dados detalhados de jogos da Steam.
    
    Args:
        app_ids (list): Lista de IDs de jogos na Steam
        language (str): Idioma para as descrições e reviews (padrão: portuguese)
        max_reviews (int): Número máximo de reviews a serem coletados
    
    Returns:
        DataFrame: DataFrame com informações detalhadas dos jogos
    """
    game_data = []

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

            details_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
            details_response = requests.get(details_url).json()

            if str(app_id) in details_response and details_response[str(app_id)]['success']:
                data = details_response[str(app_id)]['data']

                game_info["name"] = data.get("name", "Desconhecido")
                game_info["description"] = data.get("short_description", "")
                game_info["release_date"] = data.get("release_date", {}).get("date", "")
                game_info["genres"] = [genre["description"] for genre in data.get("genres", [])]
                game_info["categories"] = [category["description"] for category in data.get("categories", [])]

                if "price_overview" in data:
                    game_info["price"] = data["price_overview"].get("final_formatted", "")

                # Obtendo os requisitos de sistema
                if "pc_requirements" in data:
                    game_info["pc_requirements_minimum"] = data["pc_requirements"].get("minimum", "")
                    game_info["pc_requirements_recommended"] = data["pc_requirements"].get("recommended", "")

            players_url = f"http://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}"
            players_response = requests.get(players_url).json()
            if players_response and "response" in players_response:
                game_info["current_players"] = players_response["response"].get("player_count", 0)

            reviews_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1"
            params = {
                "filter": "recent",
                "language": language,
                "review_type": "all",
                "purchase_type": "all",
                "num_per_page": min(50, max_reviews),
            }
            reviews_response = requests.get(reviews_url, params=params).json()

            if "query_summary" in reviews_response:
                game_info["total_reviews"] = reviews_response["query_summary"].get("total_reviews", 0)
                game_info["review_score"] = reviews_response["query_summary"].get("review_score_desc", "")

            if "reviews" in reviews_response:
                game_info["reviews"] = [review['review'] for review in reviews_response.get("reviews", [])]

            game_data.append(game_info)

        except Exception as e:
            print(f"Erro ao processar o jogo {app_id}: {e}")

    df = pd.DataFrame(game_data)
    return df

def get_recent_games_from_reviewers(app_id, api_key, num_players=10):
    """
    Busca os jogos recentes mais jogados por usuários que comentaram no jogo especificado.
    
    Args:
        app_id (str): ID do jogo na Steam
        api_key (str): Chave da API da Steam
        num_players (int): Número de usuários a analisar
    
    Returns:
        DataFrame: DataFrame com jogos recentes
    """
    # Obter lista de revisores (comentários) para o jogo
    reviewers = []
    try:
        response = requests.get(
            f"https://store.steampowered.com/appreviews/{app_id}",
            params={"json": 1, "filter": "recent", "num_per_page": num_players},
        )
        data = response.json()
        for review in data.get("reviews", []):
            steam_id = review.get("author", {}).get("steamid")
            if steam_id:
                reviewers.append(steam_id)
    except Exception as e:
        print("Erro ao buscar revisores:", e)
        return pd.DataFrame(columns=["Nome do jogo", "ID_steam do jogo", "Contagem de jogadores"])

    # Obter os jogos recentes para cada revisor
    recent_games = []
    for steam_id in reviewers:
        try:
            response = requests.get(
                f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/",
                params={"key": api_key, "steamid": steam_id},
            )
            data = response.json()
            for game in data.get("response", {}).get("games", []):
                recent_games.append({"name": game["name"], "appid": game["appid"]})
        except Exception as e:
            print(f"Erro ao buscar jogos recentes para o usuário {steam_id}:", e)

    # Contar frequência de jogos
    game_counts = Counter((game["name"], game["appid"]) for game in recent_games)

    # Preparar dados para o DataFrame
    data = [
        {"Nome do jogo": name, "ID_steam do jogo": appid, "Contagem de jogadores": count}
        for (name, appid), count in game_counts.items()
    ]

    return pd.DataFrame(data, columns=["Nome do jogo", "ID_steam do jogo", "Contagem de jogadores"])

def get_recent_games_for_multiple_apps(app_ids, api_key, num_players=10):
    """
    Executa a coleta de jogos recentes para uma lista de app_ids.
    
    Args:
        app_ids (list): Lista de IDs de jogos na Steam
        api_key (str): Chave da API da Steam
        num_players (int): Número de usuários a analisar por app
    
    Returns:
        DataFrame: DataFrame consolidado com jogos recentes para todos os apps
    """
    all_data = []
    for app_id in app_ids:
        print(f"Processando app_id: {app_id}")
        df = get_recent_games_from_reviewers(app_id, api_key, num_players)
        if not df.empty:
            df["Origem do App"] = app_id
            all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame(
        columns=["Nome do jogo", "ID_steam do jogo", "Contagem de jogadores", "Origem do App"])
