
# Full-Stack Stock Market Data Pipeline (Airflow, Spark, PostgreSQL, Metabase)

## Project Overview:

This project is an end-to-end data pipeline that extracts stock market data from multiple external APIs, processes and transforms it using Apache Spark, stages and warehouses the data in PostgreSQL, and visualizes insights through Metabase.

The workflow is fully orchestrated using Airflow and runs in a Dockerized environment for easy deployment.

Data Modeling:

Designed and implemented a star-schema data warehouse consisting of a fact table (fact_stock_prices) and two dimension tables (dim_stock, dim_date). Referential integrity is enforced through foreign keys and optimized for analytical querying. Built a complete data ingestion pipeline using Airflow, Spark, Postgres, Docker, and Metabase.


Tech Stack:

- Multiple APIs (multi-source ingestion)
- Airflow (orchestration)
- Spark 
- Postgres staging → Postgres warehouse (proper ELT modeling)
- Metabase (visualization)
- Docker Compose (local infra)

 ## Pipeline Flow
1. Airflow task pulls stock API data into staging
2. Spark job reads staging & transforms data (cleans, enriches)
3. Spark loads to warehouse schema in PostgreSQL
4. Metabase dashboards query the warehouse

## How to Run
    docker-compose up --build
Access Airflow: http://localhost:8888
5. Access Metabase: http://localhost:3000
