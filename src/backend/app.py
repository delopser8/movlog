'''
    entrada principal al backend con FastAPI
'''


from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.routes.routers import router
from services.ingesta.alpaca_client import iniciar_schedule


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Arrancando backend Movlog...")
    iniciar_schedule()
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