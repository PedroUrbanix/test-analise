locals {
  name = "${var.project}-${var.env}"
}

resource "azurerm_resource_group" "rg" {
  name     = "${local.name}-rg"
  location = var.location
}

# Container Registry
resource "azurerm_container_registry" "acr" {
  name                = replace("${local.name}acr", "-", "")
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true  # Simplifica o início; para prod use Managed Identity
}

# Log Analytics (requerido pelo ACA)
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${local.name}-law"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Container Apps Environment
resource "azurerm_container_app_environment" "cenv" {
  name                       = "${local.name}-cae"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

# Key Vault + secrets
resource "azurerm_key_vault" "kv" {
  name                        = "${local.name}-kv"
  resource_group_name         = azurerm_resource_group.rg.name
  location                    = azurerm_resource_group.rg.location
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = false
  soft_delete_retention_days  = 7
}

data "azurerm_client_config" "current" {}

# Identity para o Container App acessar o Key Vault
resource "azurerm_user_assigned_identity" "uami" {
  name                = "${local.name}-uami"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

resource "azurerm_key_vault_access_policy" "kv_uami_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.uami.principal_id

  secret_permissions = ["Get", "List"]
}

# Access policy para a identidade que executa o Terraform (CI/SP) poder gravar secrets
resource "azurerm_key_vault_access_policy" "kv_tf_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

# PostgreSQL Flexible Server
resource "random_password" "pg_password" {
  length  = 24
  special = true
}

resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "${local.name}-pg"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = var.pg_version
  sku_name               = var.pg_sku_name
  storage_mb             = var.pg_storage_mb
  administrator_login    = var.pg_admin_user
  administrator_password = coalesce(var.pg_admin_password, random_password.pg_password.result)
  zone                   = "1"

  # Para expor publicamente (rápido para POC). Em prod use VNet/Private endpoints.
  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  lifecycle {
    ignore_changes = [ zone ] # Algumas regiões não suportam zones
  }
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "flowsdb"
  server_id = azurerm_postgresql_flexible_server.pg.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

# Connection string
locals {
  db_conn = "postgresql+psycopg2://${var.pg_admin_user}:${azurerm_postgresql_flexible_server.pg.administrator_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}"
}

# Secrets no Key Vault
resource "azurerm_key_vault_secret" "sec_database_url" {
  name         = "DATABASE-URL"
  value        = local.db_conn
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [ azurerm_key_vault_access_policy.kv_tf_policy ]
}

resource "azurerm_key_vault_secret" "sec_openai" {
  count        = var.openai_api_key == "" ? 0 : 1
  name         = "OPENAI-API-KEY"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [ azurerm_key_vault_access_policy.kv_tf_policy ]
}

resource "azurerm_key_vault_secret" "sec_az_openai_key" {
  count        = var.azure_openai_key == "" ? 0 : 1
  name         = "AZURE-OPENAI-KEY"
  value        = var.azure_openai_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [ azurerm_key_vault_access_policy.kv_tf_policy ]
}

resource "azurerm_key_vault_secret" "sec_az_openai_endpoint" {
  count        = var.azure_openai_endpoint == "" ? 0 : 1
  name         = "AZURE-OPENAI-ENDPOINT"
  value        = var.azure_openai_endpoint
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [ azurerm_key_vault_access_policy.kv_tf_policy ]
}

resource "azurerm_key_vault_secret" "sec_brave" {
  count        = var.brave_api_key == "" ? 0 : 1
  name         = "BRAVE-API-KEY"
  value        = var.brave_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [ azurerm_key_vault_access_policy.kv_tf_policy ]
}

# Container App (API)
resource "azurerm_container_app" "api" {
  name                         = "${local.name}-api"
  container_app_environment_id = azurerm_container_app_environment.cenv.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  depends_on                   = [ azurerm_key_vault_access_policy.kv_uami_policy ]

  registry {
    server   = azurerm_container_registry.acr.login_server
    username = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-pwd"
  }

  secret {
    name  = "acr-pwd"
    value = azurerm_container_registry.acr.admin_password
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.sec_database_url.id
    identity            = azurerm_user_assigned_identity.uami.id
  }
  # Secrets opcionais do Key Vault
  dynamic "secret" {
    for_each = concat(
      var.openai_api_key == "" ? [] : [{ name = "openai-api-key", id = azurerm_key_vault_secret.sec_openai[0].id }],
      var.azure_openai_key == "" ? [] : [{ name = "azure-openai-key", id = azurerm_key_vault_secret.sec_az_openai_key[0].id }],
      var.azure_openai_endpoint == "" ? [] : [{ name = "azure-openai-endpoint", id = azurerm_key_vault_secret.sec_az_openai_endpoint[0].id }],
      var.brave_api_key == "" ? [] : [{ name = "brave-api-key", id = azurerm_key_vault_secret.sec_brave[0].id }]
    )
    content {
      name                = secret.value.name
      key_vault_secret_id = secret.value.id
      identity            = azurerm_user_assigned_identity.uami.id
    }
  }

  template {
    container {
      name   = "api"
      image  = "${azurerm_container_registry.acr.login_server}/${var.image_name}"
      cpu    = 1.0
      memory = "2Gi"

      # Executa a API FastAPI com uvicorn
      command = ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      # Garante que os imports funcionem (api.main)
      env {
        name  = "PYTHONPATH"
        value = "/app/src"
      }
      # OPENAI_API_KEY (opcional)
      dynamic "env" {
        for_each = var.openai_api_key == "" ? [] : [{ name = "OPENAI_API_KEY", secret_name = "openai-api-key" }]
        content {
          name        = env.value.name
          secret_name = env.value.secret_name
        }
      }
      # Demais opcionais (somente se definidos)
      dynamic "env" {
        for_each = concat(
          var.azure_openai_key == "" ? [] : [{ name = "AZURE_OPENAI_KEY", secret_name = "azure-openai-key" }],
          var.azure_openai_endpoint == "" ? [] : [{ name = "AZURE_OPENAI_ENDPOINT", secret_name = "azure-openai-endpoint" }],
          var.brave_api_key == "" ? [] : [{ name = "BRAVE_API_KEY", secret_name = "brave-api-key" }]
        )
        content {
          name        = env.value.name
          secret_name = env.value.secret_name
        }
      }
    }

    http_scale_rule {
      name                = "auto"
      concurrent_requests = 50
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  identity {
    type = "UserAssigned"
    identity_ids = [ azurerm_user_assigned_identity.uami.id ]
  }
}

# Job diário opcional (Container Apps Job)
resource "azurerm_container_app_job" "etl_daily" {
  count                        = var.enable_etl_job ? 1 : 0
  name                         = "${local.name}-etl-londrina"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  container_app_environment_id = azurerm_container_app_environment.cenv.id
  replica_timeout_in_seconds   = 3600

  schedule {
    trigger_type    = "Schedule"
    cron_expression = var.etl_cron
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-pwd"
  }

  secret {
    name  = "acr-pwd"
    value = azurerm_container_registry.acr.admin_password
  }

  # DATABASE_URL via Key Vault
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.sec_database_url.id
    identity            = azurerm_user_assigned_identity.uami.id
  }

  template {
    container {
      name  = "etl"
      image = "${azurerm_container_registry.acr.login_server}/${var.image_name}"
      args  = ["python","-m","cli","run","--city", var.etl_city, "--uf", var.etl_uf]
      env { name = "DATABASE_URL" secret_name = "database-url" }
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [ azurerm_user_assigned_identity.uami.id ]
  }
}

output "containerapp_fqdn" { value = azurerm_container_app.api.latest_revision_fqdn }
output "acr_login_server"  { value = azurerm_container_registry.acr.login_server }
output "postgres_fqdn"     { value = azurerm_postgresql_flexible_server.pg.fqdn }
output "key_vault_name"    { value = azurerm_key_vault.kv.name }
