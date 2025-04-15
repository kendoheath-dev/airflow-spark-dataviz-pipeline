from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, explode, col, lit, create_map
from pyspark.sql.types import StringType, IntegerType, StructType, StructField, MapType
from itertools import chain


# Initialize Spark Session
spark = SparkSession.builder \
    .appName("DataProcessingJob") \
    .master("local[*]")\
    .config("spark.jars", "/opt/bitnami/spark/jars/postgresql-42.7.3.jar") \
    .getOrCreate()


time_series_schema = StructType([
    StructField("1. open", StringType(), nullable=True),
    StructField("2. high", StringType(), nullable=True),
    StructField("3. low", StringType(), nullable=True),
    StructField("4. close", StringType(), nullable=True),
    StructField("5. volume", StringType(), nullable=True)
    ])
full_schema = StructType([
    StructField("Meta Data", 
            StructType([
                StructField("1. Information", StringType()),
                StructField("2. Symbol", StringType()),
                StructField("3. Last Refreshed", StringType()),
                StructField("4. Output Size", StringType()),
                StructField("5. Time Zone", StringType())
    ])),          
    StructField("Time Series (Daily)", 
            MapType(StringType(), time_series_schema), nullable=True)
    ])
# df contains column of string type even though its a jsonb in postgres - it gets converted to a 
# string over jdbc
raw_df = spark.read \
    .format("jdbc") \
    .option("dbtable", "fact_table") \
    .option("url", "jdbc:postgresql://postgres_staging:5432/staging_db") \
    .option("dbtable", "staging_data") \
    .option("user", "staging") \
    .option("password", "staging_password") \
    .option("driver", "org.postgresql.Driver") \
    .load()
parsed_df = raw_df.withColumn("parsed_data", from_json(col("raw_json"), full_schema))

'''
# Get the schema fields (i.e., the dynamic date keys inside "Time Series (Daily)")
time_series_struct = parsed_df.select("parsed_data.`Time Series (Daily)`").schema[0].dataType
#build a list of kv pairs
kv_pairs = list(
    chain.from_iterable(
        [(lit(field.name), col(f"`Time Series (Daily)`.`{field.name}`")) for field in time_series_struct.fields]
    )
)

# Convert to map - explode cannot use struct
df_with_map = parsed_df.select(create_map(*kv_pairs).alias("time_series"))

exploded_df = df_with_map.select(explode(col("time_series")).alias("date", "data"))

time_series_struct = parsed_df.select("parsed_data.`Time Series (Daily)`")
exploded_df = time_series_struct.select(explode("`Time Series (Daily)`").alias("date", "data"))
'''
exploded_df = parsed_df.select(explode("parsed_data.`Time Series (Daily)`").alias("date", "data"))
df_flat = exploded_df.select(
    col("date"),
    col("data.`1. open`").cast("double").alias("open"),
    col("data.`2. high`").cast("double").alias("high"),
    col("data.`3. low`").cast("double").alias("low"),
    col("data.`4. close`").cast("double").alias("close"),
    col("data.`5. volume`").cast("long").alias("volume")
)

print()
# Load Processed Data into Warehouse
# use internal postgres port not 5433

df_flat.write \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres_warehouse:5432/warehouse_db") \
    .option("dbtable", "fact_table") \
    .option("user", "postgres") \
    .option("password", "password") \
    .option("driver", "org.postgresql.Driver") \
    .mode("overwrite") \
    .save()

spark.stop()
