# airflow-spark-dataviz-pipeline

├── README.md
├── airflow_home
│   ├── Dockerfile.airflow
│   ├── airflow.cfg
│   ├── dags
│   │   └── api_to_spark.py
│   ├── plugins
│   └── webserver_config.py
├── db
│   ├── postgres_staging
│   │   └── init.sql
│   └── postgres_warehouse
│       └── init.sql
├── docker-compose.yml
└── spark
    ├── Dockerfile.spark
    └── src
        └── processing_script.py
