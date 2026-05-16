#!/usr/bin/env bash
# inicialización de colecciones MongoDB con índices y datos default

MONGO_HOST="${MONGODB_URL:-mongodb://localhost:27017}"

echo "    Inicializando MongoDB..."

mongosh "$MONGO_HOST/movlog" --quiet << 'EOF'


// ++++ COLECCIONES ++++

// --- activos_elegidos ---
db.createCollection("activos_elegidos")
db.activos_elegidos.createIndex({ ticker: 1 }, { unique: true })

// --- alertas ---
db.createCollection("alertas")
db.alertas.createIndex({ alerta_id: 1 }, { unique: true })
db.alertas.insertMany([
    {
        alerta_id: "fluctuacion_brusca",
        nombre: "Fluctuación brusca",
        descripcion: "Variación relativa superior al umbral en la ventana temporal activa",
        umbral: [0.50, 10],
        tipo: "warning",
        estado: "ON"
    },
    {
        alerta_id: "ram_alta",
        nombre: "RAM alta",
        descripcion: "Uso de RAM del host superior al umbral",
        umbral: [80, 95],
        tipo: "warning",
        estado: "ON"
    },
    {
        alerta_id: "ram_critica",
        nombre: "RAM crítica",
        descripcion: "Uso de RAM del host en nivel crítico",
        umbral: 95,
        tipo: "critico",
        estado: "ON"
    },
    {
        alerta_id: "llm_fallo",
        nombre: "Fallo LLM",
        descripcion: "El modelo de IA no ha respondido correctamente",
        tipo: "critico",
        estado: "ON"
    }
])

print("MongoDB inicializado correctamente")
EOF

if [ $? -eq 0 ]; then
    echo -e "    \033[0;32m✅ MongoDB OK\033[0m"
else
    echo -e "    \033[0;31m❌ MongoDB: error en la inicialización\033[0m"
    exit 1
fi