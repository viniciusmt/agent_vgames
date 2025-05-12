import requests
import pandas as pd
from bs4 import BeautifulSoup
from collections import Counter


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