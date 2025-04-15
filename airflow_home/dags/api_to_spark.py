from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.docker.operators.docker import DockerOperator
# from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator

import requests
import json
import os
from psycopg2.extras import Json
from datetime import datetime, timedelta



# API extraction function
def _fetch_api_data():
    api_key: str = "TUIC1EDE34L1LOYA"
    symbol = "IBM"
    function = "TIME_SERIES_DAILY"
    url = f'https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
    else:
        raise Exception("Failed tp fetch API data")
    pg_hook = PostgresHook(postgres_conn_id="postgres_staging")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    insert_query = "INSERT INTO staging_data (raw_json) VALUES(%s)"
    cursor.execute(insert_query, (Json(data),))
    conn.commit()
    cursor.close()
    conn.close()

with DAG(
    dag_id="api_to_spark", 
    schedule_interval="@daily", 
    start_date=datetime(2025, 4, 12), 
    catchup=False,) as dag:
        
        # Task: Fetch API Data
        fetch_api_task = PythonOperator(
                task_id="fetch_api_data",
                python_callable=_fetch_api_data,)
        
        # Task: Trigger Spark Job
        
        submit_spark_job = SparkSubmitOperator(
             task_id="submit_spark_job",
             application="/opt/bitnami/spark/src/processing_script.py",
             conn_id="spark_default",
             conf={"spark.master":"spark://spark-master:7077",
                   "spark.jars":"/opt/bitnami/spark/jars/postgresql-42.7.3.jar"},
             verbose=True

        )
        
            #  volumes=["./spark/src/processing_script.py:/opt/spark-jobs"],
fetch_api_task >> submit_spark_job