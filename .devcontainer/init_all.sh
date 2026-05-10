#!/bin/bash

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# 1. CURL a Alpaca Markets y NewsAPI para validar las claves API (si no son válidas, pedir al usuario que las introduzca de nuevo)
echo -e "${CYAN}>>> Validando claves API...${NC}"
