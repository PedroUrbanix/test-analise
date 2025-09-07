variable "project" {
  description = "Nome curto do projeto"
  type        = string
  default     = "flows-ia"
}
variable "location" {
  description = "Região Azure"
  type        = string
  default     = "brazilsouth"
}
variable "env" {
  description = "Ambiente (dev/stg/prd)"
  type        = string
  default     = "dev"
}

# Postgres
variable "pg_version" {
  description = "Versão do PostgreSQL"
  type        = string
  default     = "14"
}
variable "pg_sku_name" {
  description = "SKU do Postgres Flexible Server"
  type        = string
  default     = "B_Standard_B1ms"
}
variable "pg_storage_mb" {
  description = "Armazenamento em MB"
  type        = number
  default     = 32768
}
variable "pg_admin_user" {
  description = "Usuário admin do Postgres"
  type        = string
  default     = "pgadmin"
}
variable "pg_admin_password" {
  description = "Senha admin do Postgres"
  type        = string
  sensitive   = true
  default     = null
}

# Container image
variable "image_name" {
  description = "Nome da imagem (repo/image:tag)"
  type        = string
  default     = "flows-ia-api:latest"
}

# Azure OpenAI / chaves externas (opcional)
variable "openai_api_key" {
  description = "OpenAI API Key (opcional)"
  type        = string
  default     = ""
}
variable "azure_openai_key" {
  description = "Azure OpenAI Key (opcional)"
  type        = string
  default     = ""
}
variable "azure_openai_endpoint" {
  description = "Azure OpenAI Endpoint (opcional)"
  type        = string
  default     = ""
}
variable "brave_api_key" {
  description = "Brave Search API Key (opcional)"
  type        = string
  default     = ""
}

# Job (opcional)
variable "enable_etl_job" {
  description = "Habilita job diário Container Apps"
  type        = bool
  default     = false
}
variable "etl_city" {
  description = "Cidade para o job diário"
  type        = string
  default     = "Londrina"
}
variable "etl_uf" {
  description = "UF para o job diário"
  type        = string
  default     = "PR"
}
variable "etl_cron" {
  description = "CRON do job diário (UTC)"
  type        = string
  default     = "0 3 * * *"
}
