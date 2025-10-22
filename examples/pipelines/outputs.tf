output "catalog" {
  value = databricks_catalog.catalog.name
}

output "analytics_schema" {
  value = databricks_schema.analytics.name
}

output "token_vault_schema" {
  value = databricks_schema.token_vault.name
}

output "dlt_pipeline_id" {
  value = databricks_pipeline.phi_deid.id
}