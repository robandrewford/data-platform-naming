#####################
# Terraform variables
#####################

variable "databricks_host" {}
variable "databricks_token" {}

variable "uc_catalog" {
  default = "oncology"
}

variable "uc_schema" {
  default = "analytics"
}

variable "uc_token_vault_schema" {
  default = "token_vault"
}

variable "group_data_engineering" {
  description = "Databricks group name with engineering privileges"
  default     = "data-engineering"
}

variable "group_privacy_officer" {
  description = "Databricks group name for Privacy Office"
  default     = "privacy-office"
}

variable "group_researchers" {
  description = "Databricks group name for researchers"
  default     = "researchers"
}

variable "secret_scope" {
  default = "secrets"
}

variable "hmac_salt_key" {
  default = "hmac_salt_v1"
}

variable "hmac_salt_value" {
  description = "Provide via TF var or environment; rotate regularly"
  default     = "REPLACE_ME_FOR_DEV_ONLY"
}

variable "token_vault_table" {
  default = "token_map"
}

variable "raw_path" {
  default = "s3://landing/clinical/"
}

variable "schema_path" {
  default = "s3://dlt/schemas/clinical"
}

variable "dlt_storage" {
  default = "s3://dlt/storage/phi_deid_pipeline"
}

# Path to the Python script in the Databricks Workspace, e.g., "Workspace:/Repos/org/repo/dlt_phi_deid.py"
variable "workspace_file_path" {
  default = "Workspace:/Repos/your-org/your-repo/dlt_phi_deid.py"
}