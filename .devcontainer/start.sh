#!/bin/bash
set -euo pipefail

# -- colores --
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}>>> Iniciando chequeo completo de salud del stack de Movlog...${NC}"

MAX_RETRIES=30
wait_for_port() {
    local name=$1
    local port=$2
    local count=0
    echo -n "Esperando a $name ($port)... "
    while ! nc -z localhost $port; do
      sleep 2
      ((count++))
      if [ $count -ge $MAX_RETRIES ]; then
        echo -e "${YELLOW}⚠️ Saltando (timeout)${NC}"
        return
      fi
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
echo -e "${YELLOW}>>> Es estrictamente necesario acceder al archivo .env y cambiar las siguientes claves:${NC}"
echo -e "${YELLOW}>>> - ALPACA_API_KEY${NC}"
echo -e "${YELLOW}>>> - ALPACA_SECRET_KEY${NC}"
echo -e "${YELLOW}>>> - NEWSAPI_KEY${NC}"
echo -e "${YELLOW}>>> Sin estas claves, el proyecto no podrá funcionar correctamente.${NC}"
echo -e ""

# --- ALPACA MARKETS ---
echo -e ""
echo -e "${BLUE}>>> Indicaciones para rellenar ALPACA_API_KEY y ALPACA_SECRET_KEY:${NC}"
echo -e "${YELLOW}>>> - Accede a https://alpaca.markets/${NC}"
echo -e "${YELLOW}>>> - Inicia sesión o regístrate con tu cuenta "Trading API"${NC}"
echo -e "${YELLOW}>>> - (obligatorio) Activa la multi-factor authentication de tu cuenta usando${NC}"
echo -e "${YELLOW}>>>   la app de Google Authenticator en tu móvil${NC}"
echo -e "${YELLOW}>>> - Accede al Home y abajo a la derecha encontrarás tu sección de API Keys${NC}"
echo -e ""

# --- NEWSAPI ---
echo -e "${BLUE}>>> Indicaciones para rellenar NEWSAPI_KEY:${NC}"
echo -e "${YELLOW}>>> - Accede a https://newsapi.org/${NC}"
echo -e "${YELLOW}>>> - Arriba a la derecha dale a Login o regístrate en Get API Key${NC}"
echo -e ""
echo -e "${Blue}>>> Una vez tengas el archivo .env correctamente configurado, escribe en el terminal 'start_movlog'${NC}"