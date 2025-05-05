from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField, MapType
from pyspark.sql.functions import from_json, explode, col, lit, create_map, avg, lag, monotonically_increasing_id
from pyspark.sql.window import Window

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
#  JSONb in postgres - it gets converted to a string over jdbc
raw_df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres_staging:5432/staging_db") \
    .option("dbtable", "staging_stock_data") \
    .option("user", "staging") \
    .option("password", "staging_password") \
    .option("driver", "org.postgresql.Driver") \
    .load()
dim_stock_df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://postgres_staging:5432/staging_db") \
    .option("dbtable", "dim_profile_data") \
    .option("user", "staging") \
    .option("password", "staging_password") \
    .option("driver", "org.postgresql.Driver") \
    .load()
dim_date_df  = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://postgres_staging:5432/staging_db") \
    .option("dbtable", "dim_date") \
    .option("user", "staging") \
    .option("password", "staging_password") \
    .option("driver", "org.postgresql.Driver") \
    .load()

parsed_df = raw_df.withColumn("parsed_data", from_json(col("raw_json"), full_schema))
exploded_df = parsed_df.selectExpr("*","parsed_data.`Meta Data`.`2. Symbol` as symbol")
exploded_df = exploded_df.select(col("symbol"), explode("parsed_data.`Time Series (Daily)`").alias("date", "data"))
df_flat = exploded_df.select(
    col("symbol"),
    col("date"),
    col("data.`1. open`").cast("double").alias("open_price"),
    col("data.`2. high`").cast("double").alias("high_price"),
    col("data.`3. low`").cast("double").alias("low_price"),
    col("data.`4. close`").cast("double").alias("close_price"),
    col("data.`5. volume`").cast("long").alias("trade_volume")
)
df_flat.show()
# Create derived columns
enriched_df = df_flat.selectExpr(
                        "*",
                        "(close_price - open_price) AS price_change",
                        "((close_price - open_price) / open_price) * 100 AS price_change_pct",
                        "((high_price - low_price) / open_price) * 100 AS daily_volatility_pct",
                        "(open_price + high_price + low_price + close_price) / 4 AS approximate_vwap",
                        "CASE WHEN close_price > open_price THEN TRUE ELSE FALSE END AS is_bullish_day",
                        "CASE WHEN close_price < open_price THEN TRUE ELSE FALSE END AS is_bearish_day")
# Join to get stock_id and date_id
enriched_df = enriched_df.join(dim_stock_df.select("stock_id", "symbol"), on="symbol", how="left")
enriched_df = enriched_df.join(dim_date_df.select("date_id", "date"), on="date", how="left")

# compute daily return and moving average per stock 
windowSpec = Window.partitionBy("stock_id").orderBy("date")
enriched_df = enriched_df \
                    .withColumn("moving_avg", avg("close_price")\
                        .over(windowSpec.rowsBetween(-6, 0)))\
                    .withColumn(
                        "prev_close", 
                        lag("close_price").over(windowSpec)
                    ).withColumn(
                        "daily_return",
                        ((col("close_price") - col("prev_close")) / col("prev_close")) * 100
                    ).drop("prev_close")

enriched_df = enriched_df.drop("symbol").drop("date")
print("dim date")
dim_date_df.show()

# needed for fact table primary key
enriched_df = enriched_df.withColumn("stock_price_id", monotonically_increasing_id())
enriched_df.show()

final_df = enriched_df.select(
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
    "daily_return"
)
# final_df.dropDuplicates(["date_id", "stock"])
# Load Processed Data into landing table
final_df.write \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres_staging:5432/staging_db") \
    .option("dbtable", "landing_stock_prices") \
    .option("user", "staging") \
    .option("password", "staging_password") \
    .option("driver", "org.postgresql.Driver") \
    .mode("overwrite") \
    .save()
spark.stop()