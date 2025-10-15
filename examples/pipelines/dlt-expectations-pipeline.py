import dlt
from pyspark.sql import functions as F, types as T, Window as W

# ---------- 0) Pipeline configuration ----------
RAW_PATH    = spark.conf.get("raw_path")      # e.g., s3://landing/encounters/
SCHEMA_PATH = spark.conf.get("schema_path")   # e.g., s3://dlt/schemas/encounters

# Optional: explicitly define an initial schema for dirty sources
BRONZE_SCHEMA = T.StructType([
    T.StructField("encounter_id",  T.StringType()),
    T.StructField("patient_id",    T.StringType()),
    T.StructField("visit_dt",      T.StringType()),     # dirty string; normalize later
    T.StructField("charge_amt",    T.StringType()),     # currency in text
    T.StructField("notes",         T.StringType()),
    T.StructField("ssn",           T.StringType()),
])

# ---------- 1) Raw ingest (streaming source) ----------
@dlt.view(
    comment="Raw files ingested via Auto Loader with rescued data retained for diagnostics."
)
def raw_encounters():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("cloudFiles.inferColumnTypes", "false")  # we provide a schema
            .option("cloudFiles.schemaLocation", SCHEMA_PATH)
            .option("header", "true")
            .option("multiLine", "true")
            .option("quote", '"')
            .option("escape", '"')
            .option("rescuedDataColumn", "_rescued_data")     # capture corrupt/unknown columns/rows
            .schema(BRONZE_SCHEMA)
            .load(RAW_PATH))

# ---------- 2) Bronze (lossless; add ingest metadata) ----------
@dlt.table(
    name="bronze_encounters",
    comment="Lossless Bronze table including ingest metadata and rescued records."
)
def bronze_encounters():
    df = dlt.read_stream("raw_encounters")
    return (df
        .withColumn("_ingest_ts", F.current_timestamp())
        .withColumn("_src_file",  F.input_file_name())
        .withColumn("_row_hash",  F.md5(F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in df.columns]))))

# ---------- 2a) Bronze quarantine (anything with rescued data) ----------
@dlt.table(
    name="bronze_encounters_quarantine",
    comment="Rows with parsing errors or unexpected columns captured from _rescued_data."
)
def bronze_encounters_quarantine():
    b = dlt.read_stream("bronze_encounters")
    return b.filter(F.col("_rescued_data").isNotNull())

# ---------- 3) Helpers for Silver normalization ----------
def to_decimal_str(col):
    # strip $ , and whitespace then cast
    return F.regexp_replace(F.regexp_replace(F.trim(col), r"[$,]", ""), r"\s+", "")

def parse_any_ts(col):
    return F.coalesce(
        F.to_timestamp(col, "yyyy-MM-dd'T'HH:mm:ssXXX"),
        F.to_timestamp(col, "yyyy-MM-dd HH:mm:ss"),
        F.to_timestamp(col, "MM/dd/yyyy HH:mm"),
        F.to_timestamp(col, "MM/dd/yyyy")
    )

# ---------- 3) Silver with expectations & dedupe ----------
@dlt.table(
    name="silver_encounters",
    comment="Normalized encounters with strict typing, DQ flags, and latest-version dedupe by business keys."
)
@dlt.expect_or_drop("has_keys", "encounter_id IS NOT NULL AND patient_id IS NOT NULL")
@dlt.expect("valid_amount_format", "charge_amt IS NULL OR charge_amt RLIKE '^[ $\\,]*[0-9]+(\\.[0-9]{1,2})?$'")
@dlt.expect("valid_date_string", "visit_dt IS NULL OR LENGTH(visit_dt) >= 8")
def silver_encounters():
    b = dlt.read_stream("bronze_encounters")

    clean = (b
        # Standardize IDs
        .withColumn("encounter_id", F.upper(F.regexp_replace(F.col("encounter_id"), r"\s+", "")))
        .withColumn("patient_id",   F.upper(F.regexp_replace(F.col("patient_id"),   r"\s+", "")))

        # Parse/normalize timestamps
        .withColumn("visit_ts", parse_any_ts(F.col("visit_dt")))
        .withColumn("visit_dt_utc", F.to_utc_timestamp("visit_ts", "UTC"))

        # Coerce charge amount
        .withColumn("charge_amt_num", to_decimal_str(F.col("charge_amt")).cast("decimal(18,2)"))

        # PHI misplacement heuristic (example)
        .withColumn("ssn_flag", F.when(F.col("ssn").rlike(r"^\d{3}-\d{2}-\d{4}$"), F.lit("SSN_PRESENT")).otherwise(F.lit("NONE")))

        # DQ flags
        .withColumn("dq_missing_keys", F.when(F.col("encounter_id").isNull() | F.col("patient_id").isNull(), F.lit(True)).otherwise(F.lit(False)))
        .withColumn("dq_bad_dates",    F.col("visit_ts").isNull())
        .withColumn("dq_bad_amt",      F.when(F.col("charge_amt").isNotNull() & F.col("charge_amt_num").isNull(), F.lit(True)).otherwise(F.lit(False)))
        .withColumn("dq_any_issue",    F.expr("dq_missing_keys OR dq_bad_dates OR dq_bad_amt"))

        # Projection
        .select(
            "encounter_id",
            "patient_id",
            "visit_dt_utc",
            F.col("charge_amt_num").alias("charge_amt"),
            "notes",
            "ssn_flag",
            "_src_file",
            "_ingest_ts",
            "_row_hash",
            "dq_any_issue"
        )
    )

    # Dedupe: keep latest ingest per (encounter_id, patient_id)
    w = W.partitionBy("encounter_id", "patient_id").orderBy(F.col("_ingest_ts").desc())
    return (clean
            .withColumn("_rn", F.row_number().over(w))
            .filter(F.col("_rn") == 1)
            .drop("_rn"))

# ---------- 3a) Silver violations (when expectations fire) ----------
@dlt.table(
    name="silver_encounters_violations",
    comment="Records that failed expectations in silver; retained for investigation."
)
def silver_encounters_violations():
    # DLT automatically tracks expectation failures; we can surface them explicitly
    # by filtering on dq flags for operational visibility.
    s = dlt.read("silver_encounters")
    return s.filter(F.col("dq_any_issue") == True)

# ---------- 4) Gold rollup ----------
@dlt.table(
    name="gold_charges_by_day",
    comment="Daily charges roll-up excluding rows with data quality issues."
)
def gold_charges_by_day():
    s = dlt.read("silver_encounters").filter(~F.col("dq_any_issue"))
    return (s.groupBy(F.to_date("visit_dt_utc").alias("visit_date"))
              .agg(F.sum("charge_amt").alias("charges")))
