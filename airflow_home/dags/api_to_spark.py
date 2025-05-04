from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from datetime import datetime
import requests
import hashlib
import json


staging_hook = PostgresHook(postgres_conn_id="postgres_staging")
warehouse_hook = PostgresHook(postgres_conn_id="postgres_warehouse")

def hash_json(dataset):
    hash_object = hashlib.sha256()
    hash_object.update(dataset)
    return hash_object.hexdigest()

# Function to extract API data and save it to PostgreSQL (Staging Layer)
def _extract_and_stage(symbol):
    # av_api_key: str = "TUIC1EDE34L1LOYA"
    av_api_key: str = "KGPRB0VYQ0ISWTOI"
    fmp_apikey="qMZXWlXSQjw6scFJbsTLE0h5aR7KQP3p"
    function="OVERVIEW"
    av_url = f'https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={av_api_key}'
    fmp_url = f'https://financialmodelingprep.com/stable/profile?symbol={symbol}&apikey={fmp_apikey}'
    # Fetch from alphaVantage (av) API
    response = requests.get(av_url)
    if response.status_code == 200:
        av_profile_data = response.json()
    else: 
        response.raise_for_status()
    # Fetch from financial modeling prep (fmp) API
    response = requests.get(fmp_url)
    if response.status_code == 200:
        fmp_profile_data = response.json()[0]

    # Blend data
    records = []
    if av_profile_data.get("Symbol") not in records:
        records.append({
                "symbol": av_profile_data.get("Symbol"),
                "name": av_profile_data.get("Name"),
                "sector": av_profile_data.get("Sector"),
                "industry": av_profile_data.get("Industry"),
                "exchange": av_profile_data.get("Exchange"),
                "ipo_date": fmp_profile_data.get("ipoDate"),
                "is_active": fmp_profile_data.get("isActivelyTrading")
            })
    # Save to PostgreSQL (Staging)
    # UPSERT handles duplicate records; stock symbol exist, Postgres ignores it
    # using upsert ensures downstream tasks still run cleanly
    # no duplicates are inserted if piplines reruns

    # pg_hook = PostgresHook(postgres_conn_id="postgres_staging")
    insert_query = """
        INSERT  INTO dim_profile_data (
            symbol, name, sector, industry, exchange, ipo_date, is_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s )
        ON CONFLICT (symbol) DO NOTHING;
        """
    for record in records:
        staging_hook.run(insert_query, parameters=(
            record['symbol'],
            record['name'],
            record['sector'],
            record['industry'],
            record['exchange'],
            record['ipo_date'],
            record['is_active'],
    ))
    # Extract OHLCV data (open high low close volume) from av API
    function = "TIME_SERIES_DAILY"
    url = f'https://www.alphavantage.co/query?function={function}&outputsize=compact&symbol={symbol}&apikey={av_api_key}'
    response = requests.get(url)
    OHLCV_data = response.json()


    # Save to PostgreSQL (Staging)
    # pg_hook = PostgresHook(postgres_conn_id="postgres_staging")
    hashed_data = hash_json(json.dumps(OHLCV_data).encode("utf-8"))
    insert_query = """
        INSERT INTO staging_stock_data (raw_json, data_hash) 
        VALUES(%s, %s) ON CONFLICT (data_hash) DO NOTHING;
        """
    staging_hook.run(insert_query, parameters=(json.dumps(OHLCV_data), hashed_data))


def _warehouse_load():
    profile_dataframe = staging_hook.get_pandas_df("SELECT * FROM dim_profile_data")
    OHLCV_dataframe = staging_hook.get_pandas_df("SELECT * FROM landing_stock_prices")

    # Load into warehouse
    for _, row in profile_dataframe.iterrows():
        warehouse_hook.run("""
        INSERT  INTO dim_profile_data (stock_id, symbol, name, sector, industry, exchange, ipo_date, is_active) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s );
        """, parameters=(row['stock_id'], row['symbol'], row['name'], row['sector'], row['industry'], row['exchange'], row['ipo_date'], row['is_active']))
    for _, row in OHLCV_dataframe.iterrows():
        warehouse_hook.run("""
            INSERT INTO fact_stock_prices_daily ( 
                            "stock_price_id",
                            "stock_id",
                            "date_id",   
                            "open_price",
                            "high_price",
                            "low_price",
                            "close_price",
                            "trade_volume",
                            "moving_avg",
                            "price_change",
                            "price_change_pct",
                            "daily_volatility_pct",
                            "approximate_vwap",
                            "is_bullish_day",
                            "is_bearish_day",
                            "daily_return" ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stock_id, date_id) DO NOTHING;
        """, parameters=(row["stock_price_id"],
                            row["stock_id"],
                            row["date_id"],   
                            row["open_price"],
                            row["high_price"],
                            row["low_price"],
                            row["close_price"],
                            row["trade_volume"],
                            row["moving_avg"],
                            row["price_change"],
                            row["price_change_pct"],
                            row["daily_volatility_pct"],
                            row["approximate_vwap"],
                            row["is_bullish_day"],
                            row["is_bearish_day"],
                            row["daily_return"]))
        # -- stg_ohlcv_stock_prices

with DAG(
    dag_id="api_to_spark", 
    schedule_interval="@daily", 
    start_date=datetime(2025, 4, 12), 
    catchup=False,) as dag:
        
# Step 1: Extract Data from API to Staging        
        fetch_tasks = []
        # symbols = ["TSLA", "AAPL", "IBM"]           
        symbols = ["IBM"]           
        for symbol in symbols:
            extract_task = PythonOperator(
                task_id=f"fetch_{symbol.lower()}_data",
                python_callable=_extract_and_stage,
                op_kwargs={"symbol": symbol}
            )
            fetch_tasks.append(extract_task)

# Step 2: Transform with Spark
        submit_spark_job = SparkSubmitOperator(
            task_id="submit_spark_job",
            application="/opt/bitnami/spark/src/processing_script.py",
            conn_id="spark_default",
            conf={
                    "spark.master":"spark://spark-master:7077",
                    "spark.jars":"/opt/bitnami/spark/jars/postgresql-42.7.3.jar"},
            verbose=True
        )
# Step 3: Load to datawarehouse
        load_to_warehouse = PythonOperator(
            task_id="load_to_warehouse",
            python_callable=_warehouse_load
        )
        
        fetch_tasks >> submit_spark_job >> load_to_warehouse
        # fetch_tasks >> submit_spark_job