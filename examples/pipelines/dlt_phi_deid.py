# dlt_phi_deid.py
# Databricks Delta Live Tables pipeline for HIPAA Safe Harbor de-identification with token vault
# Notes:
# - Replace secret scope/key, catalog/schema names, and raw/storage paths per your environment.
# - This script is meant to be referenced by a DLT pipeline (see dlt_pipeline.json).

import dlt
from pyspark.sql import functions as F, types as T, Window as W
import uuid

# -------------------- Configuration --------------------
RAW_PATH            = spark.conf.get("raw_path")                  # e.g., s3://landing/clinical/
SCHEMA_PATH         = spark.conf.get("schema_path")               # e.g., s3://dlt/schemas/clinical
TOKEN_VAULT_CATALOG = spark.conf.get("token_vault_catalog", "main")
TOKEN_VAULT_SCHEMA  = spark.conf.get("token_vault_schema",  "token_vault")
TOKEN_VAULT_TABLE   = spark.conf.get("token_vault_table",   "token_map")
# Secret scope/key should exist and be ACL-restricted
SECRET_SCOPE        = spark.conf.get("secret_scope", "secrets")
SECRET_KEY          = spark.conf.get("hmac_salt_secret_key", "hmac_salt_v1")

# Salt used for HMAC; rotate periodically as per KMS procedure
try:
    HMAC_SALT = dbutils.secrets.get(SECRET_SCOPE, SECRET_KEY)
except Exception as e:
    # Fallback for local testing; DO NOT use in production
    HMAC_SALT = "dev-only-not-for-prod"

# -------------------- Helpers --------------------
def parse_ts(col):
    return F.coalesce(
        F.to_timestamp(col, "yyyy-MM-dd'T'HH:mm:ssXXX"),
        F.to_timestamp(col, "yyyy-MM-dd HH:mm:ss"),
        F.to_timestamp(col, "yyyy-MM-dd"),
        F.to_timestamp(col, "MM/dd/yyyy HH:mm"),
        F.to_timestamp(col, "MM/dd/yyyy")
    )

def redact_free_text(col):
    c = F.regexp_replace(col, r"\\b\\d{3}-\\d{2}-\\d{4}\\b", "[SSN]")
    c = F.regexp_replace(c, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "[EMAIL]")
    c = F.regexp_replace(c, r"\\b(?:\\+?1[-.\\s]?)*\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b", "[PHONE]")
    return F.regexp_replace(c, r"\\b\\d{1,5}\\s+[A-Za-z0-9.\\s]{3,}\\b", "[ADDR]")

def year_only(ts_col):
    return F.year(ts_col)

def to_zip3(zip_col):
    return F.when(zip_col.isNotNull() & (F.length(zip_col) >= 3), F.substring(zip_col, 1, 3)).otherwise(F.lit("000"))

# --- Token vault upsert (re-identifiable but ACL-restricted) ---
def upsert_tokens(df, col_name: str, field_label: str):
    """
    Creates tokens for distinct values of df[col_name] and returns df with new column <col_name>_token.
    Uses LIVE.<catalog>.<schema>.<table> as the mapping table.
    """
    from pyspark.sql import DataFrame

    # Build fully-qualified LIVE table name
    fq_table = f"LIVE_{TOKEN_VAULT_CATALOG}_{TOKEN_VAULT_SCHEMA}_{TOKEN_VAULT_TABLE}".replace(".", "_")

    # Create LIVE view over the vault to avoid UC resolution issues inside DLT
    # The physical table should be created once via SQL/TF; here we just reference it.
    spark.sql(f"CREATE TABLE IF NOT EXISTS {TOKEN_VAULT_CATALOG}.{TOKEN_VAULT_SCHEMA}.{TOKEN_VAULT_TABLE} (field STRING, source_value STRING, token STRING, created_ts TIMESTAMP)")

    vault = spark.table(f"{TOKEN_VAULT_CATALOG}.{TOKEN_VAULT_SCHEMA}.{TOKEN_VAULT_TABLE}")
    distinct_vals = (df.select(F.col(col_name).alias("source_value"))
                       .where(F.col("source_value").isNotNull())
                       .distinct()
                       .withColumn("field", F.lit(field_label))
                    )

    # Find new values to insert into the vault
    to_insert = (distinct_vals.join(vault, on=["field", "source_value"], how="left_anti")
                 .withColumn("token", F.expr("uuid()"))
                 .withColumn("created_ts", F.current_timestamp()))

    # Append new tokens
    if to_insert.take(1):
        (to_insert.write
            .format("delta")
            .mode("append")
            .saveAsTable(f"{TOKEN_VAULT_CATALOG}.{TOKEN_VAULT_SCHEMA}.{TOKEN_VAULT_TABLE}"))

    # Join tokens back to df
    joined = (df.join(spark.table(f"{TOKEN_VAULT_CATALOG}.{TOKEN_VAULT_SCHEMA}.{TOKEN_VAULT_TABLE}")
                      .filter(F.col("field") == field_label)
                      .select("source_value", "token"),
                      on=df[col_name] == F.col("source_value"),
                      how="left")
                .withColumn(col_name + "_token", F.col("token"))
                .drop("token", "source_value"))
    return joined

# -------------------- Bronze (raw ingest) --------------------
BRONZE_SCHEMA = T.StructType([
    T.StructField("mrn", T.StringType()),
    T.StructField("patient_name", T.StringType()),
    T.StructField("dob", T.StringType()),
    T.StructField("admit_dt", T.StringType()),
    T.StructField("discharge_dt", T.StringType()),
    T.StructField("zip", T.StringType()),
    T.StructField("email", T.StringType()),
    T.StructField("phone", T.StringType()),
    T.StructField("provider_notes", T.StringType()),
])

@dlt.view(comment="Raw PHI-bearing clinical rows via Auto Loader with rescued data.")
def raw_clinical():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("cloudFiles.schemaLocation", SCHEMA_PATH)
            .option("header", "true")
            .option("multiLine", "true")
            .option("quote", '"').option("escape", '"')
            .option("rescuedDataColumn", "_rescued_data")
            .schema(BRONZE_SCHEMA)
            .load(RAW_PATH))

@dlt.table(name="bronze_clinical_raw", comment="Lossless bronze with ingest metadata.")
def bronze_clinical_raw():
    df = dlt.read_stream("raw_clinical")
    return (df.withColumn("_ingest_ts", F.current_timestamp())
              .withColumn("_src_file", F.input_file_name())
              .withColumn("_row_hash", F.md5(F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in df.columns]))))

@dlt.table(name="bronze_clinical_quarantine", comment="Parsing violations / unexpected columns.")
def bronze_clinical_quarantine():
    return dlt.read_stream("bronze_clinical_raw").filter(F.col("_rescued_data").isNotNull())

# -------------------- Silver (classification & normalization) --------------------
@dlt.table(
    name="silver_classified",
    comment="Typed data with PHI classification flags and basic normalization."
)
@dlt.expect_or_drop("has_mrn", "mrn IS NOT NULL")
def silver_classified():
    b = dlt.read_stream("bronze_clinical_raw")
    return (b
      .withColumn("dob_ts", parse_ts(F.col("dob")))
      .withColumn("admit_ts", parse_ts(F.col("admit_dt")))
      .withColumn("discharge_ts", parse_ts(F.col("discharge_dt")))
      # PHI flags
      .withColumn("phi_name", F.col("patient_name").isNotNull())
      .withColumn("phi_email", F.col("email").isNotNull())
      .withColumn("phi_phone", F.col("phone").isNotNull())
      .withColumn("phi_geo", F.col("zip").isNotNull())
      .withColumn("phi_free_text", F.col("provider_notes").isNotNull())
    )

# -------------------- Silver (Safe Harbor de-identification) --------------------
@dlt.table(
    name="silver_deid_safeharbor",
    comment="Safe Harbor de-identified dataset with tokens and generalizations."
)
@dlt.expect("no_direct_identifiers_left", "patient_name IS NULL AND email IS NULL AND phone IS NULL")
def silver_deid_safeharbor():
    s = dlt.read_stream("silver_classified")

    # Tokenize direct identifiers (reversible under strict ACL)
    s = upsert_tokens(s, "mrn", "MRN")
    s = upsert_tokens(s, "patient_name", "NAME")
    s = upsert_tokens(s, "email", "EMAIL")
    s = upsert_tokens(s, "phone", "PHONE")

    # Free-text scrubbing
    s = s.withColumn("provider_notes_scrub", redact_free_text(F.col("provider_notes")))

    # Date generalization (keep only year) and ZIP3
    s = (s.withColumn("dob_year", year_only(F.col("dob_ts")))
           .withColumn("admit_year", year_only(F.col("admit_ts")))
           .withColumn("discharge_year", year_only(F.col("discharge_ts")))
           .withColumn("zip3", to_zip3(F.col("zip"))))

    # Project PHI-free analytics fields
    return (s.select(
        F.col("mrn_token").alias("subject_token"),
        "zip3",
        "dob_year", "admit_year", "discharge_year",
        "provider_notes_scrub",
        "_ingest_ts", "_src_file", "_row_hash"
    ))

# -------------------- Gold (analytics mart) --------------------
@dlt.table(
    name="gold_outcomes_analytics",
    comment="PHI-free analytics mart derived from Safe Harbor dataset."
)
def gold_outcomes_analytics():
    d = dlt.read("silver_deid_safeharbor")
    return (d.groupBy("admit_year","zip3")
              .agg(F.countDistinct("subject_token").alias("n_subjects")))