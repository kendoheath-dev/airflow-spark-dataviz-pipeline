CREATE TABLE staging_data (
    id SERIAL PRIMARY KEY,
    raw_json JSONB,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);