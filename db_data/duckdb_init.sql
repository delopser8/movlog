--
-- schema de tablas en DuckDB
--

-- activos_detalles  (flujo batch diario / inicio del seguimiento)
CREATE TABLE IF NOT EXISTS activos_detalles (
    activo_id         INTEGER PRIMARY KEY,
    ticker            VARCHAR NOT NULL UNIQUE,
    nombre            VARCHAR,
    sector            VARCHAR,
    industria         VARCHAR,
    url               VARCHAR,

    -- precios históricos
    cierre_ajustado_diario   DOUBLE,
    cierre_ajustado_semanal  DOUBLE,
    cierre_ajustado_mensual  DOUBLE,
    apertura_diaria          DOUBLE,
    apertura_semanal         DOUBLE,
    apertura_mensual         DOUBLE,
    maximo_diario            DOUBLE,
    maximo_semanal           DOUBLE,
    maximo_mensual           DOUBLE,
    minimo_diario            DOUBLE,
    minimo_semanal           DOUBLE,
    minimo_mensual           DOUBLE,

    -- fundamentales
    ratio_pe          DOUBLE,
    eps               DOUBLE,
    market_cap        DOUBLE,
    dividend_yield    DOUBLE,
    esg_score         DOUBLE,

    -- recomendación
    operacion_recomendada VARCHAR,  -- compra | holdea | vende
    target_price          DOUBLE,

    actualizado_en    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- activos_precios (flujo en streaming de OHLC (polling Alpaca REST))
CREATE TABLE IF NOT EXISTS activos_precios (
    activo_id  INTEGER NOT NULL REFERENCES activos_detalles(activo_id),
    timestamp  TIMESTAMP NOT NULL,
    timeframe  VARCHAR NOT NULL,   -- 1Min | 5Min | 1Day | 1Week | 1Month
    apertura   DOUBLE,
    maximo     DOUBLE,
    minimo     DOUBLE,
    cierre     DOUBLE,
    volumen    BIGINT,

    PRIMARY KEY (activo_id, timestamp, timeframe)
);

ALTER TABLE activos_detalles ADD COLUMN IF NOT EXISTS clase VARCHAR DEFAULT 'us_equity';