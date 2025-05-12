import os
import re
import sys
import requests
import logging
from dotenv import load_dotenv
from unidecode import unidecode

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv()

def get_access_token(client_id, client_secret, region="us") -> str:
    auth_url = f"https://{region}.battle.net/oauth/token"
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post(auth_url, data=data, auth=(client_id, client_secret))
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise Exception("Token de acesso não encontrado.")
        return token
    except requests.exceptions.RequestException as e:
        raise Exception(f"[ERRO] Falha ao obter token: {e}")

def clean_guild_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", unidecode(name).lower()).strip("-")

def clean_realm_slug(realm: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", unidecode(realm).lower()).strip("-")

def get_guild_roster(region: str, realm_slug: str, guild_slug: str, token: str):
    url = f"https://{region}.api.blizzard.com/data/wow/guild/{realm_slug}/{guild_slug}/roster"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"profile-{region}", "locale": "en_US"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 401:
        raise Exception("Token inválido ou expirado (401).")
    elif response.status_code == 404:
        log.warning(f"Guilda '{guild_slug}' não encontrada no realm '{realm_slug}'.")
        return []
    response.raise_for_status()
    return response.json().get("members", [])

def consulta_guilda_wow(guild_names: list[str], realm_slug: str = "azralon", region: str = "us", offset: int = 0, limit: int = 50, basic_only: bool = True) -> dict:
    client_id = os.getenv("WOW_CLIENT_ID")
    client_secret = os.getenv("WOW_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {"erro": "Credenciais não encontradas no arquivo .env"}
    try:
        token = get_access_token(client_id, client_secret, region)
    except Exception as e:
        return {"erro": str(e)}
    results = []
    count = 0
    for guild_name in guild_names:
        guild_slug = clean_guild_name(guild_name)
        try:
            members = get_guild_roster(region, realm_slug.lower(), guild_slug, token)
        except Exception as e:
            log.error(f"[ERRO] {e}")
            continue
        for member in members:
            if count >= offset + limit:
                break
            character = member.get("character")
            if character:
                if count >= offset:
                    results.append({"name": character.get("name"), "level": character.get("level", "?")})
                count += 1
    return {
        "total": count,
        "offset": offset,
        "limit": limit,
        "results": results
    }

def get_guild_info(client_id, client_secret, region, realm, guild_name):
    os.environ["WOW_CLIENT_ID"] = client_id
    os.environ["WOW_CLIENT_SECRET"] = client_secret
    return consulta_guilda_wow([guild_name], realm_slug=realm, region=region, limit=50)

# ===================== CHARACTER DETAILS =====================
def get_character_data(region, realm_slug, character_name, token):
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm_slug}/{character_name.lower()}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"profile-{region}", "locale": "en_US"}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "Character Name": data.get("name"),
            "Realm": data.get("realm", {}).get("name"),
            "Level": data.get("level"),
            "Gender": data.get("gender", {}).get("name"),
            "Faction": data.get("faction", {}).get("name"),
            "Race": data.get("race", {}).get("name"),
            "Class": data.get("character_class", {}).get("name"),
            "Specialization": data.get("active_spec", {}).get("name"),
            "Title": data.get("active_title", {}).get("name", ""),
            "Achievement Points": data.get("achievement_points", 0),
            "Average Item Level": data.get("average_item_level", 0),
            "Equipped Item Level": data.get("equipped_item_level", 0),
            "Last Login": data.get("last_login_timestamp"),
            "Guild Name": data.get("guild", {}).get("name", "N/A"),
            "Realm Slug": realm_slug
        }
    except Exception as e:
        print(f"Erro ao obter dados do personagem {character_name}: {e}")
        return None

def get_character_statistics(region, realm_slug, character_name, token):
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm_slug}/{character_name.lower()}/statistics"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"profile-{region}", "locale": "en_US"}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "Health": data.get("health", 0),
            "Power": data.get("power", 0),
            "Power Type": data.get("power_type", {}).get("name", "N/A"),
            "Strength": data.get("strength", {}).get("effective", 0),
            "Agility": data.get("agility", {}).get("effective", 0),
            "Intellect": data.get("intellect", {}).get("effective", 0),
            "Stamina": data.get("stamina", {}).get("effective", 0),
            "Armor": data.get("armor", {}).get("effective", 0),
            "Versatility": data.get("versatility", 0),
            "Melee Crit": data.get("melee_crit", {}).get("value", 0),
            "Melee Haste": data.get("melee_haste", {}).get("value", 0),
            "Mastery": data.get("mastery", {}).get("value", 0),
            "Spell Power": data.get("spell_power", 0),
            "Spell Crit": data.get("spell_crit", {}).get("value", 0),
            "Dodge": data.get("dodge", {}).get("value", 0),
            "Parry": data.get("parry", {}).get("value", 0),
            "Block": data.get("block", {}).get("value", 0)
        }
    except Exception as e:
        print(f"Erro ao obter estatísticas do personagem {character_name}: {e}")
        return {}

def get_character_equipment(region, realm_slug, character_name, token):
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm_slug}/{character_name.lower()}/equipment"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"profile-{region}", "locale": "en_US"}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        equipment_list = []
        for item in data.get("equipped_items", []):
            equipment_list.append({
                "Name": item.get("name"),
                "Slot": item.get("slot", {}).get("name"),
                "Item Level": item.get("level", {}).get("value"),
                "Quality": item.get("quality", {}).get("name"),
                "Item ID": item.get("item", {}).get("id")
            })
        return equipment_list
    except Exception as e:
        print(f"Erro ao obter equipamentos do personagem {character_name}: {e}")
        return []

def get_character_achievements(region, realm_slug, character_name, token, max_achievements=50):
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm_slug}/{character_name.lower()}/achievements"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"profile-{region}", "locale": "en_US"}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        achievements_list = []
        for achievement in data.get("achievements", [])[:max_achievements]:
            achievements_list.append({
                "ID": achievement.get("id"),
                "Name": achievement.get("achievement", {}).get("name"),
                "Description": achievement.get("achievement", {}).get("description"),
                "Completed Timestamp": achievement.get("completed_timestamp"),
                "Points": achievement.get("achievement", {}).get("points", 0)
            })
        return achievements_list
    except Exception as e:
        print(f"Erro ao obter conquistas do personagem {character_name}: {e}")
        return []

def get_complete_character_info(client_id, client_secret, region, realm_slug, character_name):
    realm_slug = clean_realm_slug(realm_slug)
    token = get_access_token(client_id, client_secret, region)
    info = get_character_data(region, realm_slug, character_name, token)
    stats = get_character_statistics(region, realm_slug, character_name, token)
    gear = get_character_equipment(region, realm_slug, character_name, token)
    achievements = get_character_achievements(region, realm_slug, character_name, token)
    return {
        "info": info,
        "stats": stats,
        "gear": gear,
        "achievements": achievements
    }