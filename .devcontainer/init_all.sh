#!/usr/bin/env bash

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# 1. CURL a Alpaca Markets y NewsAPI para validar las claves API (no avanzar de este paso hasta que den OK las peticiones)
echo -e "${CYAN}>>> Validando claves API...${NC}"

# 2. arrancar los esquemas de las bases de datos (PostgreSQL y MongoDB) + sus insert defaults. Están en:
    # db_data/duckdb_init.sql
    # db_data/mongodb_init.sh

# 3. crear topics de Redpanda

# 4. crear los alias de scripts

# 5. mostrar enlace de la UI de Movlog en streamlit