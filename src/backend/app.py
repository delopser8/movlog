'''
    entrada principal al backend con FastAPI
'''


from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
 
from api.routes.routers import router
from services.ingesta.alpaca_client import iniciar_schedule, iniciar_polling
from services.ingesta.yfinance_client import iniciar_schedule as iniciar_schedule_yfinance
from services.db.mongodb_client import activos_elegidos_listar
from services.main_noticias_pipeline import iniciar_pipeline_noticias


def _get_tickers() -> list[str]:
    # devuelve la lista actual de tickers en seguimiento desde MongoDB
    return [a["ticker"] for a in activos_elegidos_listar()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Arrancando backend Movlog...")
    iniciar_schedule()
    iniciar_schedule_yfinance(_get_tickers)
    iniciar_polling(_get_tickers)
    iniciar_pipeline_noticias(_get_tickers)
    yield
    logger.info("Backend Movlog detenido")
 

app = FastAPI(
    title="Movlog API",
    version="0.1.0",
    lifespan=lifespan,
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(router, prefix="/api")
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
