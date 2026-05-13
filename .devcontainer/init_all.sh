#!/usr/bin/env bash

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

WORKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- 1. CURL a Alpaca Markets, NewsAPI y Hugging Face para validar las claves API (no se avanza hasta que den OK las peticiones) ---
echo -e "${CYAN}>>> Validando claves API...${NC}"

source .env 2>/dev/null || true

while true; do
    ALPACA_OK=false
    NEWSAPI_OK=false
    HF_OK=false

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

    # Hugging Face
    HF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${HF_API_TOKEN}" \
        "https://huggingface.co/api/models/ProsusAI/finbert")

    if [ "${HF_STATUS}" = "200" ]; then
        echo -e "    ${GREEN}✅ Hugging Face OK${NC}"
        HF_OK=true
    else
        echo -e "    ${RED}❌ Hugging Face falló (HTTP ${HF_STATUS}) — revisa HF_API_TOKEN en .env${NC}"
    fi

    if [ "${ALPACA_OK}" = true ] && [ "${NEWSAPI_OK}" = true ] && [ "${HF_OK}" = true ]; then
        break
    fi

    echo -e "    ${YELLOW}⏳ Reintentando en 10s... (edita .env y guarda para que el próximo intento use los nuevos valores)${NC}"
    sleep 10
    source .env 2>/dev/null || true
done

echo ""


# --- 2. arrancar los esquemas de las bases de datos (PostgreSQL y MongoDB) + sus insert defaults ---
    # están en: 
        # db_data/duckdb_init.sql
        # db_data/mongodb_init.sh
echo -e "${CYAN}>>> Inicializando bases de datos...${NC}"

# DuckDB
if [ -f "$WORKDIR/db_data/duckdb_init.sql" ] && [ -s "$WORKDIR/db_data/duckdb_init.sql" ]; then
    python3 -c "
import duckdb
con = duckdb.connect('$WORKDIR/db_data/movlog.duckdb')
with open('$WORKDIR/db_data/duckdb_init.sql', 'r') as f:
    sql = f.read()
for statement in sql.split(';'):
    if statement.strip():
        con.execute(statement)
con.close()
" && echo -e "    ${GREEN}✅ DuckDB OK${NC}" \
  || echo -e "    ${YELLOW}⚠️  DuckDB: error al ejecutar duckdb_init.sql${NC}"
else
    echo -e "    ${YELLOW}⚠️  duckdb_init.sql vacío — saltando${NC}"
fi

# MongoDB
if [ -f "$WORKDIR/db_data/mongodb_init.sh" ]; then
    docker cp "$WORKDIR/db_data/mongodb_init.sh" movlog_mongodb:/tmp/mongodb_init.sh
    docker exec movlog_mongodb bash /tmp/mongodb_init.sh > /dev/null \
        && echo -e "    ${GREEN}✅ MongoDB OK${NC}" \
        || echo -e "    ${YELLOW}⚠️  MongoDB: error en mongodb_init.sh${NC}"
else
    echo -e "    ${YELLOW}⚠️  db_data/mongodb_init.sh no encontrado — saltando${NC}"
fi
 
echo ""


# --- 3. crear topics de Redpanda ---
echo -e "${CYAN}>>> Creando topics de Redpanda...${NC}"
 
TOPICS=("activos.precios" "activos.detalles" "noticias.raw" "noticias.sentimientos" "ia.metricas")
for TOPIC in "${TOPICS[@]}"; do
    docker exec movlog_redpanda rpk topic create "${TOPIC}" --partitions 3 --replicas 1 2>/dev/null || true
    echo -e "    ${GREEN}✅ ${TOPIC}${NC}"
done
 
echo ""


# --- 4. crear los alias de scripts ---
echo -e "${CYAN}>>> Registrando alias...${NC}"
 
BASHRC="$HOME/.bashrc"
MARKER_START="# === MOVLOG ALIASES START ==="
MARKER_END="# === MOVLOG ALIASES END ==="
sed -i "/$MARKER_START/,/$MARKER_END/d" "$BASHRC"
 
cat >> "$BASHRC" << 'ALIASES'
# === MOVLOG ALIASES START ===
 
menu() {
    echo ""
    echo "  Movlog — alias disponibles"
    echo "  ─────────────────────────────────────────"
    echo "  start_movlog       → arranca el entorno completo"
    echo "  menu               → muestra este menú"
    echo "  services_show      → servicios activos y su URL de acceso"
    echo "  reset_all          → seinicia todos los servicios, sin tocar los datos"
    echo "  services_health    → chequea salud de servicios"
    echo "  databases_check    → verifica el estado de las bases de datos"
    echo "  seguimientos_check → test del pipeline completo"
    echo "  stress_check       → prueba de estrés (aviso previo)"
    echo ""
}
 
services_show() {
    echo ""
    echo "  Movlog — servicios activos"
    echo "  ─────────────────────────────────────────"
    if [ -n "${CODESPACE_NAME}" ]; then
        echo "  Streamlit (UI)   → https://${CODESPACE_NAME}-18501.app.github.dev"
        echo "  FastAPI docs     → https://${CODESPACE_NAME}-18000.app.github.dev/docs"
        echo "  Redpanda Console → https://${CODESPACE_NAME}-18080.app.github.dev"
        echo "  Langfuse         → https://${CODESPACE_NAME}-13000.app.github.dev"
        echo "  Portainer        → https://${CODESPACE_NAME}-19000.app.github.dev"
        echo "  Ollama API       → https://${CODESPACE_NAME}-11434.app.github.dev"
    else
        echo "  Streamlit (UI)   → http://localhost:18501"
        echo "  FastAPI docs     → http://localhost:18000/docs"
        echo "  Redpanda Console → http://localhost:18080"
        echo "  Langfuse         → http://localhost:13000"
        echo "  Portainer        → http://localhost:19000"
        echo "  Ollama API       → http://localhost:11434"
    fi
    echo "  MongoDB          → Panel lateral de VS Code (Database Client)"
    echo ""
}

reset_all() {
    echo "⚠️  Esto reiniciará todos los servicios de Movlog (los datos no se tocan)."
    read -p "   ¿Continuar? [s/N] " confirm
    if [[ ! "$confirm" =~ ^[sS]$ ]]; then
        echo "Cancelado."
        return
    fi

    echo ""
    echo "  Deteniendo FastAPI y Streamlit..."
    pkill -f "uvicorn app:app" 2>/dev/null || true
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 1

    echo "  Reiniciando contenedores Docker..."
    docker compose -f /workspaces/movlog/.devcontainer/docker-compose.yml restart
    sleep 5

    echo "  Relanzando Movlog..."
    source /workspaces/movlog/.devcontainer/init_all.sh
}
 
services_health()    { bash "$HOME/tests/services_health_test.sh"; }
databases_check()    { python3 "$HOME/tests/databases_test.py"; }
seguimientos_check() { python3 "$HOME/tests/seguimientos_pipeline_test.py"; }
 
stress_check() {
    echo "⚠️  Esta prueba detendrá el sistema temporalmente."
    read -p "   ¿Continuar? [s/N] " confirm
    if [[ "$confirm" =~ ^[sS]$ ]]; then
        python3 "$HOME/tests/stress_test.py"
    else
        echo "Cancelado."
    fi
}
 
# === MOVLOG ALIASES END ===
ALIASES
 
source "$BASHRC" 2>/dev/null || true
echo -e "    ${GREEN}✅ Alias registrados${NC}"
echo ""


# --- 5. inicializar todo el pipeline de Movlog ---
    # inicializar API + schedules (están declarados en el arranque de app.py)
    # inicial UI del frontend con main_ui.py
    # esperar a que ambos estén activos antes de mostrar el menú (check de endpoints /health y /docs)
    # mostrar enlace a la UI y API de Movlog
    # revisar logs en /tmp/movlog_fastapi.log y /tmp/movlog_streamlit.log si alguno tarda mucho en arrancar o da error
echo -e "${CYAN}>>> Inicializando Movlog...${NC}"
 
pkill -f "uvicorn app:app" 2>/dev/null || true
sleep 1
 
nohup env PYTHONPATH="$WORKDIR/src/backend" python3 -m uvicorn app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --app-dir "$WORKDIR/src/backend" \
    > /tmp/movlog_fastapi.log 2>&1 &
 
echo -n "    Esperando FastAPI "
ELAPSED=0
until curl -s http://localhost:8000/health | grep -q "ok" 2>/dev/null; do
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge 30 ]; then
        echo -e "\n    ${YELLOW}⚠️  FastAPI tardó más de 30s — revisa /tmp/movlog_fastapi.log${NC}"
        break
    fi
done
echo -e " ${GREEN}✅ FastAPI lista${NC}"
 
pkill -f "streamlit run" 2>/dev/null || true
sleep 1
 
nohup env PYTHONPATH="$WORKDIR/src" python3 -m streamlit run \
    "$WORKDIR/src/frontend/main_ui.py" \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.fileWatcherType watchdog \
    > /tmp/movlog_streamlit.log 2>&1 &
 
echo -n "    Esperando UI "
ELAPSED=0
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200" 2>/dev/null; do
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge 30 ]; then
        echo -e "\n    ${YELLOW}⚠️  Streamlit tardó más de 30s — revisa /tmp/movlog_streamlit.log${NC}"
        break
    fi
done
echo -e " ${GREEN}✅ UI lista${NC}"


# --- 6. mostrar enlace a la UI y API de Movlog ---
echo ""
echo "────────────────────────────────────────────────────────"
echo ""
echo -e "  ${GREEN}✔ Movlog arrancado correctamente${NC}"
echo ""

if [ -n "${CODESPACE_NAME}" ]; then
    echo "  UI disponible en:"
    echo -e "  ${CYAN}  https://${CODESPACE_NAME}-18501.app.github.dev${NC}"
    echo ""
    echo "  API docs disponible en:"
    echo -e "  ${CYAN}  https://${CODESPACE_NAME}-18000.app.github.dev/docs${NC}"
else
    echo "  UI disponible en:"
    echo -e "  ${CYAN}  http://localhost:18501${NC}"
    echo ""
    echo "  API docs disponible en:"
    echo -e "  ${CYAN}  http://localhost:18000/docs${NC}"
fi

echo ""
echo -e "  Ejecuta ${YELLOW}menu${NC} para ver todos los comandos disponibles"
echo ""
echo "────────────────────────────────────────────────────────"