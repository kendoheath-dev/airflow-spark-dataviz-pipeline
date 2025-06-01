
CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,     -- 20250428 format
    date DATE NOT NULL,     
    day_of_week INT,             -- 1=Monday, 7=Sunday
    day_name TEXT,
    day_of_month INT,            -- 1-31
    month INT,                   -- 1-12
    month_name TEXT,
    quarter INT,                 -- 1-4
    year INT,
    is_weekend BOOLEAN
);

INSERT INTO dim_date
SELECT
    EXTRACT(YEAR FROM d)::INT * 10000 
    + EXTRACT(MONTH FROM d)::INT * 100 
    + EXTRACT(DAY FROM d)::INT AS date_id,       -- build date_id like 20250428
    d AS date,
    EXTRACT(ISODOW FROM d)::INT AS day_of_week,   -- 1 = Monday
    TO_CHAR(d, 'Day') AS day_name,                -- Full day name
    EXTRACT(DAY FROM d)::INT AS day_of_month,
    EXTRACT(MONTH FROM d)::INT AS month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(QUARTER FROM d)::INT AS quarter,
    EXTRACT(YEAR FROM d)::INT AS year,
    CASE 
        WHEN EXTRACT(ISODOW FROM d) IN (6,7) THEN TRUE   -- 6=Saturday, 7=Sunday
        ELSE FALSE
    END AS is_weekend
FROM generate_series(
    '2010-01-01'::date,  -- Start date
    '2030-12-31'::date,  -- End date
    interval '1 day'     -- Step = 1 day
) AS d;
    -- we would maybe want ipo year
    -- version INT DEFAULT 1
CREATE TABLE staging_stock_data (
    id SERIAL PRIMARY KEY,
    raw_json JSONB,
    data_hash TEXT UNIQUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_profile_data (
    stock_id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name VARCHAR(255),
    sector VARCHAR(100),
    exchange VARCHAR(50),
    industry VARCHAR(50),
    ipo_date VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE landing_stock_prices (
    stock_price_id SERIAL PRIMARY KEY,
    stock_id INT NOT NULL REFERENCES dim_profile_data(stock_id),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    open_price  NUMERIC,
    high_price  NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    trade_volume BIGINT,
    moving_avg NUMERIC,
    price_change NUMERIC,
    price_change_pct NUMERIC,
    daily_volatility_pct NUMERIC,
    approximate_vwap NUMERIC,
    is_bullish_day BOOLEAN,
    is_bearish_day BOOLEAN,
    daily_return NUMERIC,
    UNIQUE(stock_price_id, stock_id, date_id)
);
