#!/usr/bin/env bash
set -euo pipefail

# -- colores --
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

COMPOSE_FILE=".devcontainer/docker-compose.yml"
TIMEOUT=400

echo ""
echo -e "${BLUE}>>> Arrancando stack de Movlog...${NC}"
echo ""


# --- 1. Permisos Docker ---
echo -e "${BLUE}>>> Ajustando permisos del socket Docker...${NC}"
if sudo chmod 666 /var/run/docker.sock 2>/dev/null; then
  echo -e "    ${GREEN}🟢 Permisos ajustados correctamente${NC}"
else
  echo -e "    ${YELLOW}🟡  No se pudieron ajustar permisos del socket Docker${NC}"
  echo    "    Intentando continuar de todas formas..."
fi


# --- 2. Levantar contenedores del tirón ---
echo -e "${BLUE}>>> Levantando contenedores...${NC}"

sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true

docker volume rm devcontainer_redpanda-data 2>/dev/null || true

docker start movlog_redpanda movlog_mongodb movlog_langfuse_db movlog_langfuse movlog_ollama movlog_portainer movlog_redpanda_console 2>/dev/null || true
docker compose -f "${COMPOSE_FILE}" up -d --no-recreate 2>/dev/null || true

sleep 5
docker start movlog_redpanda movlog_mongodb 2>/dev/null || true


# --- 3. Esperar a servicios con healthcheck ---
echo -e "${BLUE}>>> Esperando a que los servicios críticos estén healthy...${NC}"

SERVICES=("redpanda" "mongodb" "langfuse_db" "langfuse" "ollama")

for SERVICE in "${SERVICES[@]}"; do
  echo -n "    Esperando ${SERVICE} "
  ELAPSED=0

  CONTAINER_ID=""
  while [[ -z "${CONTAINER_ID}" && "${ELAPSED}" -lt "${TIMEOUT}" ]]; do
    CONTAINER_ID="$(docker ps -q --filter "label=com.docker.compose.service=${SERVICE}" 2>/dev/null | head -1 || true)"
    if [[ -z "${CONTAINER_ID}" ]]; then
      echo -n "."
      sleep 2
      ELAPSED=$((ELAPSED + 2))
    fi
  done

  if [[ -z "${CONTAINER_ID}" ]]; then
    echo -e "\n${YELLOW}    ⚠️  Contenedor '${SERVICE}' no encontrado tras ${TIMEOUT}s${NC}"
    continue
  fi

  ELAPSED=0
  until [[ "$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "${CONTAINER_ID}" 2>/dev/null)" == "healthy" ]]; do
    HEALTH="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "${CONTAINER_ID}" 2>/dev/null || true)"

    if [[ "${HEALTH}" == "no-healthcheck" ]]; then
      echo -e " ${YELLOW}⚠️  sin healthcheck (asumiendo OK)${NC}"
      break
    fi

    if [[ "${HEALTH}" == "unhealthy" ]]; then
      echo -e "\n${YELLOW}    ⚠️  ${SERVICE} está unhealthy, revisa: docker logs \$(docker ps -qf label=com.docker.compose.service=${SERVICE})${NC}"
      break
    fi

    if [[ "${ELAPSED}" -ge "${TIMEOUT}" ]]; then
      echo -e "\n${YELLOW}    ⚠️  TIMEOUT: ${SERVICE} no alcanzó healthy en ${TIMEOUT}s${NC}"
      break
    fi

    echo -n "."
    sleep 3
    ELAPSED=$((ELAPSED + 3))
  done

  [[ "$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "${CONTAINER_ID}" 2>/dev/null)" == "healthy" ]] \
    && echo -e " ${GREEN}✅ healthy${NC}"
done


# --- 4. Descargar modelo Qwen 3.5:0.8b en Ollama ---
echo -e "${BLUE}>>> Descargando modelo Qwen 3.5:0.8b en Ollama...${NC}"
docker exec movlog_ollama ollama pull qwen3.5:0.8b 2>/dev/null || {
  echo -e "    ${YELLOW}⚠️  No se pudo descargar el modelo Qwen 3.5:0.8b en Ollama${NC}"
  echo    "    Revisa los logs de Ollama para más detalles: docker logs movlog_ollama"
}


# --- 5. creación del archivo .env con las variables de entorno ---
if [ ! -f .env ]; then
    cat > .env <<EOF
# API Keys
ALPACA_API_KEY=tu_key_aqui
ALPACA_SECRET_KEY=tu_secret_aqui
NEWSAPI_KEY=tu_key_aqui
HF_API_TOKEN=tu_token_aqui
# Langfuse
LANGFUSE_PUBLIC_KEY=tu_key_aqui
LANGFUSE_SECRET_KEY=tu_secret_aqui
# modo offline con Mock Data (true/false)
MOCK_MODE=false
EOF
    echo -e "${GREEN}    archivo .env creado${NC}"
fi


# --- 6. Instalación persistente del comando 'start_movlog' (solamente ejecuta source .devcontainer/init_all.sh) ---
BASHRC="$HOME/.bashrc"
MARKER_START="# === MOVLOG HELPER START ==="
MARKER_END="# === MOVLOG HELPER END ==="

echo -e "${BLUE}>>> Configurando comando 'start_movlog' persistente...${NC}"

sed -i "/$MARKER_START/,/$MARKER_END/d" "$BASHRC"

cat >> "$BASHRC" << EOF
$MARKER_START
start_movlog() {
    cd "$PWD"
    source "$PWD/.devcontainer/init_all.sh"
}
$MARKER_END
EOF

source "$BASHRC" 2>/dev/null || true

echo "-------------------------------------------------------------------------------------"
echo ""
echo "+-----------------------+"
echo "|                       |"
echo "|     ✔ TODO OK ✔      |"
echo "|                       |"
echo "+-----------------------+"
echo ""
echo -e "${YELLOW}Accede al documento /docs/api_key_guide.md donde se explica cómo configurar tus API Key de Alpaca Markets y NewsAPI.${NC}"
echo ""
echo -e "${YELLOW}Cuando las tengas correctamente configuradas en el archivo .env, ejecuta por consola el siguiente comando:${NC}"
echo ""
echo -e "${YELLOW}  start_movlog  ${NC}"
echo "-------------------------------------------------------------------------------------"