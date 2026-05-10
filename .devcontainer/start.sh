#!/bin/bash

# -- colores --
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}>>> Iniciando chequeo completo de salud del stack de Movlog...${NC}"

wait_for_port() {
    local name=$1
    local port=$2
    echo -n "Esperando a $name ($port)... "
    while ! nc -z localhost $port; do
      sleep 2
    done
    echo -e "${GREEN}¡LISTO!${NC}"
}

# 1. chequeo de puertos clave
wait_for_port "MongoDB" 27017
wait_for_port "Redpanda" 19092
wait_for_port "Redpanda Console" 8080
wait_for_port "Langfuse" 3000
wait_for_port "Ollama" 11434
wait_for_port "Portainer" 9000


# 2. descarga inicial del modelo Qwen 3.5 4B en Ollama
echo -e "${YELLOW}>>> Sincronizando modelo Qwen 3.5 4B (esto puede tardar si no existe)...${NC}"
curl -s http://localhost:11434/api/pull -d '{"name": "qwen3.5:4b"}' | jq -r '.status'
echo -e "${GREEN}>>> Modelo Qwen 3.5 4B descargado o ya presente.${NC}"

echo -e "${GREEN}   EL STACK DE MOVLOG ESTÁ EN PERFECTO FUNCIONAMIENTO  ${NC}"
# echo -e "Redpanda Console: http://localhost:8080"
# echo -e "Langfuse UI:      http://localhost:3000"
# echo -e "Portainer:        http://localhost:9000"
# echo -e "Ollama API:       http://localhost:11434"


# 3. creación del archivo .env con las variables de entorno
echo "# infraestructura" > .env
echo "MONGODB_URL=mongodb://localhost:27017" >> .env
echo "REDPANDA_BROKERS=localhost:19092" >> .env
echo "LANGFUSE_HOST=http://localhost:3000" >> .env
echo "" >> .env
echo "# API Keys" >> .env
echo "ALPACA_API_KEY=tu_key_aqui" >> .env
echo "ALPACA_SECRET_KEY=tu_secret_aqui" >> .env
echo "NEWSAPI_KEY=tu_key_aqui" >> .env

# configurar API Keys de las APIs externas (Alpaca Markets y NewsAPI)
echo -e ""
echo -e "${BLUE}>>> Configuración de las API Keys necesarias${NC}"

# --- ALPACA MARKETS ---
echo -e ""
echo -e "${BLUE}>>> INDICACIONES (Alpaca Markets):${NC}"
echo -e "${YELLOW}>>> - Accede a https://alpaca.markets/${NC}"
echo -e "${YELLOW}>>> - Inicia sesión o regístrate con tu cuenta "Trading API"${NC}"
echo -e "${YELLOW}>>> - (obligatorio) Activa la multi-factor authentication de tu cuenta usando${NC}"
echo -e "${YELLOW}>>>   la app de Google Authenticator en tu móvil${NC}"
echo -e "${YELLOW}>>> - Accede al Home y abajo a la derecha encontrarás tu sección de API Keys${NC}"
echo -e ""
echo -e "${YELLOW}>>> Copia aquí tu API Key de Alpaca Markets:${NC}"
read -p "ALPACA_API_KEY: " alpaca_key
echo -e ""
echo -e "${YELLOW}>>> Copia aquí tu Secret Key de Alpaca Markets:${NC}"
read -p "ALPACA_SECRET_KEY: " alpaca_secret

until curl -s -X GET "https://paper-api.alpaca.markets/v2/account" \
    -H "APCA-API-KEY-ID: $alpaca_key" \
    -H "APCA-API-SECRET-KEY: $alpaca_secret" | grep -q '"status":"ACTIVE"'; do
    
    echo -e "${YELLOW}>>> Las claves no son válidas. Inténtalo de nuevo.${NC}"
    read -p "ALPACA_API_KEY: " alpaca_key
    read -p "ALPACA_SECRET_KEY: " alpaca_secret
done

sed -i "s/^ALPACA_API_KEY=.*/ALPACA_API_KEY=$alpaca_key/" .env
sed -i "s/^ALPACA_SECRET_KEY=.*/ALPACA_SECRET_KEY=$alpaca_secret/" .env
echo -e "${GREEN}>>> Alpaca OK.${NC}"

# --- NEWSAPI ---
echo -e "${BLUE}>>> INDICACIONES (NewsAPI):${NC}"
echo -e "${YELLOW}>>> - Accede a https://newsapi.org/${NC}"
echo -e "${YELLOW}>>> - Arriba a la derecha dale a Login o regístrate en Get API Key${NC}"
echo -e "${YELLOW}>>> Copia tu API Key y pégala aquí:${NC}"
read -p "NEWSAPI_KEY: " newsapi_key

until curl -s "https://newsapi.org/v2/top-headlines?country=us&apiKey=$newsapi_key" | grep -q '"status":"ok"'; do
    echo -e "${YELLOW}>>> Clave NewsAPI no válida. Inténtalo de nuevo.${NC}"
    read -p "NEWSAPI_KEY: " newsapi_key
done

sed -i "s/^NEWSAPI_KEY=.*/NEWSAPI_KEY=$newsapi_key/" .env
echo -e "${GREEN}>>> NewsAPI OK.${NC}"