#!/usr/bin/env bash

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# --- 1. CURL a Alpaca Markets y NewsAPI para validar las claves API (no se avanza hasta que den OK las peticiones) ---
echo -e "${CYAN}>>> Validando claves API...${NC}"

source .env 2>/dev/null || true

while true; do
    ALPACA_OK=false
    NEWSAPI_OK=false

    # Alpaca Markets
    ALPACA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
        -H "APCA-API-SECRET-KEY: ${ALPACA_SECRET_KEY}" \
        "https://paper-api.alpaca.markets/v2/account")

    if [ "${ALPACA_STATUS}" = "200" ]; then
        echo -e "    ${GREEN}✅ Alpaca Markets OK${NC}"
        ALPACA_OK=true
    else
        echo -e "    ${RED}❌ Alpaca Markets falló (HTTP ${ALPACA_STATUS}) — revisa ALPACA_API_KEY y ALPACA_SECRET_KEY en .env${NC}"
    fi

    # NewsAPI
    NEWSAPI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        "https://newsapi.org/v2/top-headlines?country=us&apiKey=${NEWSAPI_KEY}&pageSize=1")

    if [ "${NEWSAPI_STATUS}" = "200" ]; then
        echo -e "    ${GREEN}✅ NewsAPI OK${NC}"
        NEWSAPI_OK=true
    else
        echo -e "    ${RED}❌ NewsAPI falló (HTTP ${NEWSAPI_STATUS}) — revisa NEWSAPI_KEY en .env${NC}"
    fi

    if [ "${ALPACA_OK}" = true ] && [ "${NEWSAPI_OK}" = true ]; then
        break
    fi

    echo -e "    ${YELLOW}⏳ Reintentando en 10s... (edita .env y guarda para que el próximo intento use los nuevos valores)${NC}"
    sleep 10
    source .env 2>/dev/null || true  # recarga .env en cada intento por si el usuario ha editado las keys
done

echo ""


# 2. arrancar los esquemas de las bases de datos (PostgreSQL y MongoDB) + sus insert defaults. Están en:
    # db_data/duckdb_init.sql
    # db_data/mongodb_init.sh


# 3. crear topics de Redpanda


# 4. crear los alias de scripts


# 5. inicializar todo el pipeline de Movlog
    # inicializar schedules
    # inicial main_ui.py
    # ...
echo -e "${CYAN}>>> Inicializando Movlog...${NC}"
 
# matar instancias previas de Streamlit si las hay
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

WORKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 
# start Streamlit en background con log
nohup python3 -m streamlit run \
    "$WORKDIR/src/frontend/main_ui.py" \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.fileWatcherType watchdog \
    > /tmp/movlog_streamlit.log 2>&1 &
 
# esperar a que Streamlit responda
echo -n "    Esperando a la UI "
ELAPSED=0
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; do
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge 30 ]; then
        echo -e "\n    ${YELLOW}⚠️  Streamlit tardó más de 30s — revisa /tmp/movlog_streamlit.log${NC}"
        break
    fi
done


# 6. mostrar enlace de la UI de Movlog en streamlit
echo ""
echo "────────────────────────────────────────────────────────"
echo ""
echo -e "  ${GREEN}✔ Movlog arrancado correctamente${NC}"
echo ""
echo "  UI disponible en:"
echo -e "  ${CYAN}  http://localhost:18501${NC}"
echo ""
echo "  Ejecuta ${YELLOW}menu${NC} para ver todos los comandos disponibles."
echo ""
echo "────────────────────────────────────────────────────────"