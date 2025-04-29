# Full-Stack Stock Market Data Pipeline (Airflow, Spark, PostgreSQL, Metabase)

Project Overview

This project builds a full-stack data engineering pipeline that extracts stock market data from multiple external APIs, processes and transforms it using Apache Spark, stages and warehouses the data in PostgreSQL, and visualizes insights through Metabase.

The workflow is fully orchestrated using Airflow and runs in a Dockerized environment for easy deployment.

Designed and implemented a star-schema data warehouse consisting of a fact table (fact_stock_prices) and two dimension tables (dim_stock, dim_date). Enforced referential integrity through foreign keys and optimized for analytical querying. Built a complete data ingestion pipeline using Airflow, Spark, Postgres, Docker, and Metabase.
