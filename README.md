# Steam Games API

API para consultas de dados de jogos via Steam, compatível com OpenAI Actions/ChatGPT.

## 🚀 Deploy no Render

Esta API está configurada para deploy automático no Render. Após fazer push para o GitHub, a API será automaticamente disponibilizada em: `https://agent-vgames.onrender.com`

## 📋 Funcionalidades

### Endpoints Disponíveis

1. **POST /steam/game-data** - Dados detalhados de jogos
   - Obtém informações básicas, preço, gêneros, categorias e reviews
   
2. **POST /steam/current-players** - Jogadores atuais online
   - Número atual de jogadores online em um jogo
   
3. **POST /steam/historical-data** - Dados históricos
   - Dados históricos de jogadores extraídos do SteamCharts
   
4. **POST /steam/game-reviews** - Reviews detalhados
   - Reviews com texto, sentimento, ID do usuário e horas jogadas
   
5. **POST /steam/recent-games** - Jogos recentes de avaliadores
   - Jogos populares jogados por usuários que avaliaram um jogo específico

## 🔧 Configuração Local

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente
Copie `.env.example` para `.env` e configure:
```
STEAM_API_KEY=sua_steam_api_key_aqui
```

### 3. Executar localmente
```bash
python main.py
```

## 📖 Uso da API

### Exemplo de uso com curl:

```bash
# Obter dados de um jogo
curl -X POST https://agent-vgames.onrender.com/steam/game-data \
  -H "Content-Type: application/json" \
  -d '{"app_ids": [730]}'

# Obter jogadores atuais de um jogo
curl -X POST https://agent-vgames.onrender.com/steam/current-players \
  -H "Content-Type: application/json" \
  -d '{"app_id": 730}'
```

### Exemplo para ChatGPT/OpenAI Actions:

URL do servidor: `https://agent-vgames.onrender.com`
OpenAPI JSON: `https://agent-vgames.onrender.com/openapi.json`

## 🔑 Steam API Key

Para usar todas as funcionalidades (especialmente `/steam/recent-games`), você precisa de uma Steam API Key:

1. Visite: https://steamcommunity.com/dev/apikey
2. Faça login com sua conta Steam
3. Crie uma nova chave API
4. Configure a chave como variável de ambiente `STEAM_API_KEY`

## 📊 Estrutura de Resposta

Todas as respostas seguem o padrão:
```json
{
  "success": true,
  "data": [...]
}
```

Em caso de erro:
```json
{
  "detail": "Mensagem de erro"
}
```

## 🔄 Endpoints de Monitoramento

- **GET /** - Status da API
- **GET /health** - Health check
- **GET /openapi.json** - Documentação OpenAPI
- **GET /.well-known/openapi.json** - OpenAPI para MCP

## 🛠️ Tecnologias Utilizadas

- **FastAPI** - Framework web moderno e rápido
- **Pandas** - Manipulação de dados
- **BeautifulSoup** - Web scraping
- **Requests** - Requisições HTTP
- **Uvicorn** - Servidor ASGI
