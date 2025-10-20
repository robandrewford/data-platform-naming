#############################################
# Terraform: Databricks UC + DLT deployment #
#############################################

terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50.0"
    }
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

#############################
# Unity Catalog primitives  #
#############################

resource "databricks_catalog" "catalog" {
  name         = var.uc_catalog
  comment      = "Catalog for PHI de-identification pipeline and analytics."
  isolation_mode = "ISOLATED"
}

resource "databricks_schema" "analytics" {
  catalog_name = databricks_catalog.catalog.name
  name         = var.uc_schema
  comment      = "Analytics schema for Safe Harbor outputs."
}

resource "databricks_schema" "token_vault" {
  catalog_name = databricks_catalog.catalog.name
  name         = var.uc_token_vault_schema
  comment      = "Secured schema for token vault (re-identification map)."
}

########################
# Secret scope & value #
########################

resource "databricks_secret_scope" "phi" {
  name = var.secret_scope
}

resource "databricks_secret" "hmac_salt" {
  key          = var.hmac_salt_key
  string_value = var.hmac_salt_value
  scope        = databricks_secret_scope.phi.name
}

########################
# Token vault table    #
########################

resource "databricks_sql_table" "token_vault" {
  name          = "${databricks_catalog.catalog.name}.${databricks_schema.token_vault.name}.${var.token_vault_table}"
  table_type    = "MANAGED"
  comment       = "KMS-protected reverse map for re-identification; restricted access"
  data_source_format = "DELTA"

  column {
    name = "field"
    type = "STRING"
  }
  column {
    name = "source_value"
    type = "STRING"
  }
  column {
    name = "token"
    type = "STRING"
  }
  column {
    name = "created_ts"
    type = "TIMESTAMP"
  }
}

########################
# Grants (Unity)       #
########################

# Catalog grants
resource "databricks_grants" "catalog" {
  catalog = databricks_catalog.catalog.name

  grant {
    principal  = var.group_data_engineering
    privileges = ["USE_CATALOG", "CREATE_SCHEMA", "READ_FILES"]
  }

  grant {
    principal  = var.group_privacy_officer
    privileges = ["USE_CATALOG", "CREATE_SCHEMA", "READ_FILES"]
  }
}

# Analytics schema grants
resource "databricks_grants" "analytics_schema" {
  schema = "${databricks_catalog.catalog.name}.${databricks_schema.analytics.name}"

  grant {
    principal  = var.group_data_engineering
    privileges = ["USAGE", "CREATE_TABLE", "SELECT", "MODIFY"]
  }

  grant {
    principal  = var.group_researchers
    privileges = ["USAGE", "SELECT"]
  }
}

# Token vault schema grants (tighter)
resource "databricks_grants" "token_vault_schema" {
  schema = "${databricks_catalog.catalog.name}.${databricks_schema.token_vault.name}"

  grant {
    principal  = var.group_data_engineering
    privileges = ["USAGE", "CREATE_TABLE"]
  }

  grant {
    principal  = var.group_privacy_officer
    privileges = ["USAGE", "CREATE_TABLE", "SELECT", "MODIFY"]
  }
}

# Token vault table grants (restrict SELECT)
resource "databricks_grants" "token_vault_table" {
  table = databricks_sql_table.token_vault.id

  grant {
    principal  = var.group_privacy_officer
    privileges = ["SELECT", "MODIFY"]
  }
}

########################
# DLT pipeline         #
########################

resource "databricks_pipeline" "phi_deid" {
  name       = "PHI-Deidentification-DLT"
  continuous = false
  photon     = true
  edition    = "ADVANCED"
  channel    = "CURRENT"

  target  = "${databricks_catalog.catalog.name}.${databricks_schema.analytics.name}"
  storage = var.dlt_storage

  configuration = {
    raw_path               = var.raw_path
    schema_path            = var.schema_path
    token_vault_catalog    = databricks_catalog.catalog.name
    token_vault_schema     = databricks_schema.token_vault.name
    token_vault_table      = var.token_vault_table
    secret_scope           = databricks_secret_scope.phi.name
    hmac_salt_secret_key   = var.hmac_salt_key
  }

  cluster {
    label = "default"
    autoscale {
      min_workers = 2
      max_workers = 8
    }
    spark_conf = {
      "spark.sql.adaptive.enabled" = "true"
    }
  }

  library {
    file {
      # Path to the Python script in the workspace (import with databricks_workspace_file if desired)
      path = var.workspace_file_path
    }
  }
}