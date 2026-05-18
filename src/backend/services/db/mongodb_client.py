'''
    servicio del Cliente MongoDB para operaciones CRUD sobre las colecciones de Movlog
'''

import os
from loguru import logger
from pymongo import MongoClient, errors
from pymongo.collection import Collection


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "movlog"

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=3000)
    return _client


def get_col(nombre: str) -> Collection:
    return get_client()[DB_NAME][nombre]


# ------------------ CRUD sobre las COLECCIONES -------------------------

# --- activos_elegidos ---
def activos_elegidos_listar() -> list[dict]:
    try:
        return list(get_col("activos_elegidos").find({}, {"_id": 0}).sort("ticker", 1))
    except errors.PyMongoError as e:
        logger.error(f"MongoDB activos_elegidos_listar: {e}")
        return []

def activos_elegidos_añadir(ticker: str, nombre: str) -> bool:
    try:
        get_col("activos_elegidos").update_one(
            {"ticker": ticker},
            {"$setOnInsert": {
                "ticker": ticker,
                "nombre": nombre,
            }},
            upsert=True,
        )
        logger.info(f"Activo añadido: {ticker}")
        return True
    except errors.DuplicateKeyError:
        logger.warning(f"Activo ya existe: {ticker}")
        return False
    except errors.PyMongoError as e:
        logger.error(f"MongoDB activos_elegidos_añadir: {e}")
        return False

def activos_elegidos_eliminar(ticker: str) -> bool:
    try:
        result = get_col("activos_elegidos").delete_one({"ticker": ticker})
        if result.deleted_count > 0:
            logger.info(f"Activo eliminado: {ticker}")
            return True
        return False
    except errors.PyMongoError as e:
        logger.error(f"MongoDB activos_elegidos_eliminar: {e}")
        return False


# --- alertas ---
def alertas_listar() -> list[dict]:
    try:
        return list(get_col("alertas").find({}, {"_id": 0}))
    except errors.PyMongoError as e:
        logger.error(f"MongoDB alertas_listar: {e}")
        return []

def alertas_actualizar(alerta_id: str, umbral: list | None = None, estado: str | None = None) -> bool:
    try:
        update = {}
        if umbral is not None:
            update["umbral"] = umbral
        if estado is not None:
            update["estado"] = estado
        if not update:
            return False
        get_col("alertas").update_one({"alerta_id": alerta_id}, {"$set": update})
        return True
    except errors.PyMongoError as e:
        logger.error(f"MongoDB alertas_actualizar: {e}")
        return False