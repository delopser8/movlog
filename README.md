# movlog
 
Sistema de monitorización financiera en tiempo real que combina ingesta de datos de mercado con análisis de sentimiento mediante IA.
 
Permite seguir activos financieros (acciones, crypto) con datos de precio en tiempo real desde Alpaca Markets, y correlaciona automáticamente los movimientos bruscos de precio con noticias financieras analizadas por IA — traduciendo, clasificando el sentimiento con FinBERT y generando una explicación en español con Qwen.
 
---

## Inicio rápido

1. Abre el repositorio en un Codespace y espera ~8 minutos a que se construya el entorno
2. Cuando estés en el terminal limpio de `/workspaces/movlog(main)` ejecuta:
```bash
bash .devcontainer/start.sh
```
3. Espera hasta que veas un mensaje que indique `✔ TODO OK ✔`
4. Ejecuta `start_movlog` y ve configurando las API Key del `.env` en el orden que se van pidiendo (indicaciones para conseguirlas en `/docs/api_key_guide.md`)
5. Revisa que todo haya ido `✅ OK` y accede a la URL de la UI indicada por consola

---

## Soluciones de errores

- **`start_movlog` da problemas:** Escribe `source ~/.bashrc && start_movlog` en el terminal.

- **Entorno roto tras `start_movlog`:** Borra el Codespace actual y crea uno nuevo.

- **Fallos puntuales o servicios caídos:** Ejecuta `reset_all` para reiniciar todos los servicios sin tocar los datos. Si el problema persiste, borra el Codespace y crea uno nuevo.

- **API /docs (Swagger) no carga:** Comprueba que la URL termine en `/docs`.

- **La UI de Langfuse me da problemas** Comprueba que la URL sea correcta (`https://{CODESPACE_NAME}-13000.app.github.dev`).

---

## Estructura de carpetas
 
```
movlog/
├── .devcontainer/
│   ├── devcontainer.json        # configuración del devcontainer y variables de entorno
│   ├── Dockerfile               # imagen del workspace
│   ├── docker-compose.yml       # stack completo de servicios Docker
│   ├── start.sh                 # arranque de contenedores + registro de alias
│   └── init_all.sh              # inicialización completa (APIs, DBs, FastAPI, Streamlit)
├── config/
│   └── requirements.txt
├── src/
│   ├── frontend/
│   │   ├── main_ui.py                        # entrada principal de Streamlit
│   │   ├── seguimientos_ui/
│   │   │   ├── seguimientos_ui.py            # gráfico OHLC, detalles, buscador
│   │   │   └── noticias_ui.py                # gráfico 5Min + fluctuaciones + noticias
│   │   ├── infraestructura_ui/
│   │   │   └── infraestructura_ui.py         # host, servicios, pipeline, bases de datos
│   │   ├── ai_models_ui/
│   │   │   └── ai_models_ui.py               # distribución sentimiento, modelos activos, inferencias
│   │   ├── alertas_ui/
│   │   │   └── alertas_ui.py                 # alertas configuradas + banners activos
│   │   └── configuracion_ui/
│   │       └── configuracion_ui.py           # pendiente próximo split
│   └── backend/
│       ├── app.py                            # FastAPI lifespan + arranque de threads
│       ├── api/
│       │   ├── routes/routers.py             # endpoints REST
│       │   └── controllers/controllers.py    # lógica de cada endpoint
│       └── services/
│           ├── main_noticias_pipeline.py     # orquestador del flujo de noticias
│           ├── infra_service.py              # métricas del sistema
│           ├── ui/user_service.py            # llamadas HTTP frontend → backend
│           ├── preprocesamiento/
│           │   └── analytics_service.py      # cálculos de series temporales
│           ├── db/
│           │   ├── duckdb_client.py          # CRUD DuckDB + exportación parquet
│           │   └── mongodb_client.py         # CRUD MongoDB
│           ├── ingesta/
│           │   ├── alpaca_client.py          # velas en tiempo real + catálogo assets
│           │   ├── yfinance_client.py        # detalles y fundamentales del activo
│           │   ├── news_api.py               # polling de noticias NewsAPI
│           │   └── rss_scraper.py            # scraping Yahoo Finance RSS
│           └── ai_models/
│               ├── translation.py            # traducción al inglés con Qwen
│               ├── sentiment.py              # análisis de sentimiento con FinBERT
│               ├── explicabilidad.py         # explicación de fluctuaciones con Qwen
│               └── observabilidad.py         # trazabilidad con Langfuse
├── db_data/
│   ├── duckdb_init.sql          # schema de DuckDB
│   ├── mongodb_init.sh          # colecciones e índices de MongoDB
│   ├── alpaca_assets.json       # catálogo de símbolos negociables
│   ├── mock_data/
│   │   └── pipeline_data.py     # datos mock de AAPL y TSLA (MOCK_MODE=true)
│   └── db_historicos/           # archivos .parquet exportados
├── docs/
│   ├── api_key_guide.md         # guía para obtener y configurar las API Keys
│   └── db.md                    # schema completo de las bases de datos
├── .env                         # variables de entorno (no se sube al repo)
└── README.md
```
 
---

## Arquitectura del pipeline
 
### Arranque (app.py lifespan)
 
Al arrancar FastAPI se lanzan en paralelo 4 threads daemon:
 
```
FastAPI lifespan
├── iniciar_schedule()           → Alpaca: carga catálogo assets diariamente a las 06:00 UTC
├── iniciar_schedule_yfinance()  → yfinance: actualiza detalles de activos diariamente a las 07:00 UTC
├── iniciar_polling()            → Alpaca: polling de velas 1Min cada 15s
└── iniciar_pipeline_noticias()
    ├── iniciar_newsapi()        → polling NewsAPI cada 5min
    ├── iniciar_rss()            → polling RSS Yahoo Finance cada 5min
    └── _detection_loop()        → detección de fluctuaciones cada 15s
```
 
### Al añadir un activo nuevo
 
```
ctrl_añadir_seguimiento(ticker)
└── _cargar() [thread daemon]
    ├── cargar_detalles_activo()     → yfinance → DuckDB activos_detalles
    ├── cargar_velas_iniciales(1Min) → Alpaca → DuckDB activos_precios (2 semanas)
    ├── cargar_velas_iniciales(5Min) → Alpaca → DuckDB activos_precios (2 meses)
    └── backfill_activo()
        ├── NewsAPI 48h → DuckDB noticias_historial
        ├── get_noticias_por_activo() → noticias de DuckDB para matching
        └── para cada vela con variación >= umbral en ventana ±6h de noticias:
            ├── traducir_si_necesario()  → Qwen (Ollama)
            ├── analizar_sentimiento()   → FinBERT (HuggingFace API)
            └── generar_explicacion()    → Qwen (Ollama) → DuckDB noticias_sentimientos
```
 
### Pipeline de noticias en tiempo real
 
```
_detection_loop() [cada 15s]
├── _procesar_noticias_nuevas(ticker)
│   ├── get_noticias_recientes() → noticias sin score en DuckDB
│   ├── traducir_si_necesario()  → Qwen (Ollama)
│   └── analizar_sentimiento()   → FinBERT → DuckDB noticias_sentimientos
└── procesar_ticker(ticker)
    ├── _calcular_var_pct()      → compara últimas 2 velas 5Min
    ├── si |var_pct| >= umbral:
    │   ├── get_noticias_recientes(30min)
    │   ├── traducir + FinBERT   → DuckDB noticias_sentimientos
    │   └── generar_explicacion() → Qwen → DuckDB noticias_sentimientos
    └── Langfuse traza latencia de cada inferencia
```
 
### Polling de precios
 
```
_polling_loop() [cada 15s]
└── para cada ticker en seguimiento:
    └── actualizar_velas(1Min)
        ├── get_ultima_vela()    → DuckDB
        ├── _fetch_bars()        → Alpaca REST (IEX para equity, crypto para crypto)
        └── insertar_velas()     → DuckDB activos_precios
```
 
### Umbral de fluctuación
 
El umbral que dispara el pipeline de IA se lee de MongoDB (`alertas.fluctuacion_brusca.umbral[0]`). El valor por defecto es `0.30%`. Se puede modificar desde MongoDB.
 
---
 
## Servicios y puertos
 
| Servicio         | Puerto externo | Descripción                        |
|------------------|----------------|------------------------------------|
| Streamlit UI     | 18501          | Interfaz principal de Movlog       |
| FastAPI          | 18000          | API REST + Swagger docs (`/docs`)  |
| Langfuse         | 13000          | Observabilidad de modelos IA       |
| Ollama API       | 11434          | Servidor de modelos LLM locales    |
| MongoDB          | 27017          | Base de datos de configuración     |
 
En Codespaces las URLs tienen el formato:
```
https://{CODESPACE_NAME}-{PUERTO}.app.github.dev
```
 
### Credenciales de acceso
 
**Langfuse** — crear usuario desde la UI en el primer arranque (`/docs/api_key_guide.md`).
 
**PostgreSQL** (uso interno de Langfuse) — `postgres / postgres`.
 
---
 
## Comandos disponibles
 
```bash
start_movlog      # arranca el entorno completo
menu              # muestra todos los comandos disponibles
services_show     # muestra URLs de todos los servicios
reset_all         # reinicia todos los servicios sin tocar los datos
```
 
---

# Variables de entorno

El contenido de las variables de entorno que se usan del arhivo `.env` es el siguiente:

```env

# Alpaca Markets
ALPACA_API_KEY=tu_key_aqui
ALPACA_SECRET_KEY=tu_secret_aqui

# NewsAPI
NEWSAPI_KEY=tu_key_aqui

# Hugging Face
HF_API_TOKEN=tu_token_aqui

# Langfuse (generar desde la UI de Langfuse al arrancar por primera vez)
LANGFUSE_PUBLIC_KEY=tu_key_aqui
LANGFUSE_SECRET_KEY=tu_secret_aqui
```

Ver `/docs/api_key_guide.md` para instrucciones de cómo obtener cada key.

---

## Stack tecnológico
 
| Categoría | Tecnología | Uso |
|-----------|-----------|-----|
| UI | Streamlit + Plotly | Interfaz completa y gráficos bursátiles |
| API | FastAPI + uvicorn | API REST con Swagger |
| Datos de mercado | Alpaca Markets SDK | Velas OHLC en tiempo real (IEX + Crypto) |
| Datos fundamentales | yfinance | Detalles del activo al añadirlo |
| Noticias | NewsAPI SDK | Polling de noticias financieras cada 5min |
| Noticias | feedparser + Yahoo Finance RSS | Scraping de noticias adicionales cada 5min |
| Sentimiento | ProsusAI/FinBERT | Clasificación positivo/neutral/negativo |
| Traducción | Qwen 3.5:0.8b (Ollama) | Traducción de noticias al inglés |
| Explicabilidad | Qwen 3.5:0.8b (Ollama) | Resumen explicativo de fluctuaciones |
| Observabilidad IA | Langfuse OSS v2 | Trazabilidad de inferencias y latencia |
| Base de datos OLAP | DuckDB | Series temporales OHLC + noticias |
| Base de datos config | MongoDB | Activos en seguimiento + alertas |
| Mensajería | Redpanda (Kafka) | En el stack, pendiente de integración |
| Contenerización | Docker + docker-compose | Stack completo de servicios |
| Monitorización host | psutil | Métricas de RAM y CPU |
| Logging | loguru | Logs estructurados |
| Reintentos | tenacity | Reintentos con backoff en APIs externas |
 
---

## Bases de datos
 
### DuckDB (`db_data/movlog.duckdb`)
 
**activos_precios** — velas OHLC en tiempo real
- PK compuesta: `(activo_id, timestamp, timeframe)`
- Timeframes: `1Min | 5Min | 1Day | 1Week | 1Month`

**activos_detalles** — información fundamental del activo
- PK: `activo_id`
- Incluye: sector, industria, market cap, ratio P/E, EPS, dividend yield, ESG score, recomendación de analistas, target price

**noticias_historial** — noticias financieras crudas
- PK: `noticia_id` (hash MD5 del título)

**noticias_sentimientos** — análisis de IA por noticia y activo
- PK compuesta: `(noticia_id, activo_id)`
- `score`: de -1 (muy negativo) a +1 (muy positivo)
- `explicacion`: resumen de Qwen (solo en fluctuaciones detectadas)
- `var_pct`: variación del activo en la fluctuación asociada
### MongoDB (`movlog`)
 
**activos_elegidos** — activos en seguimiento (`ticker`, `nombre`)
 
**alertas** — configuración de alertas del sistema
- `fluctuacion_brusca`: umbral `[0.30, 10]` — dispara el pipeline de IA
- `ram_alta`: umbral `[80, 95]` — banner warning en la UI
- `ram_critica`: umbral `95` — banner error en la UI
- `llm_fallo`: sin umbral — disparo manual (pendiente)
Ver `/docs/db.md` para el schema completo.
 
---
 
## API REST
 
Base URL: `http://localhost:8000/api` (Swagger en `/docs`)
 
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/seguimientos` | Lista activos en seguimiento |
| POST | `/seguimientos` | Añade activo (lanza backfill automático) |
| DELETE | `/seguimientos/{ticker}` | Elimina activo |
| GET | `/activos/{ticker}/detalles` | Detalles fundamentales del activo |
| GET | `/activos/{ticker}/velas` | Velas OHLC (params: timeframe, limite) |
| GET | `/activos/{ticker}/noticias` | Noticias con sentimiento FinBERT |
| GET | `/activos/{ticker}/fluctuaciones` | Fluctuaciones explicadas por Qwen |
| GET | `/alertas` | Lista alertas configuradas |
| GET | `/infra/stats` | Métricas del sistema |
| GET | `/health` | Estado del backend |
 
---
 
## Limitaciones conocidas
 
- **NewsAPI free tier**: máximo 35 noticias por request, solo últimos 30 días
- **Qwen 3.5:0.8b en CPU**: ~15s por inferencia sin GPU
- **Marcador de fluctuación en gráfico**: se posiciona en la noticia más relevante del periodo (±6h), no en el instante exacto de la variación de precio. El schema no persiste el timestamp exacto de la fluctuación — pendiente para el siguiente split
- **Filtrado de noticias por LIKE**: puede incluir ruido semántico (ej: noticias del condado de Berkshire para BRK.B)
- **Redpanda**: en el stack pero sin producers/consumers implementados
- **Modo offline**: inserta datos mock de AAPL y TSLA pero el sistema sigue intentando conectarse a APIs externas en background
- **Langfuse**: requiere configuración manual de usuario en el primer arranque