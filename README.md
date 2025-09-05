flows-ia: Infra + App (Azure)

Estrutura
- `app/`: API FastAPI + pipelines, Dockerfile e Compose
- `infra/terraform/`: IaC Azure (RG, ACR, KV, Postgres, ACA, Job opcional)
- `.github/workflows/`: CI (Terraform Apply, App Deploy)

Segurança e segredos
- Nunca commitar segredos reais.
- Arquivos ignorados: `app/.env`, estados do Terraform (`.terraform/`, `*.tfstate*`).
- Exemplo local: `app/.env.example` (copie para `.env`).
- Exemplo TF: `infra/terraform/terraform.tfvars.example` (copie para `terraform.tfvars`).
- Em produção, os segredos ficam no Key Vault e são lidos pelo Container Apps via Managed Identity.

Provisionar Infra (Terraform)
```
cd infra/terraform
# opcional: export TF_VAR_pg_admin_password='SUA_SENHA_FORTE_123!'
terraform init
terraform apply -auto-approve
terraform output
```

Build & Push do App
```
ACR=$(terraform -chdir=infra/terraform output -raw acr_login_server)
RG=$(terraform -chdir=infra/terraform output -raw resource_group)
az acr login -n ${ACR%%.*}
docker build -t $ACR/flows-ia-api:latest app
docker push $ACR/flows-ia-api:latest
```

Atualizar Container App
```
az containerapp update \
  --name flows-ia-dev-api \
  --resource-group "$RG" \
  --image $ACR/flows-ia-api:latest
```

Local (Compose)
```
cd app
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

CI (GitHub Actions)
- `infra-apply.yml`: aplica Terraform.
- `app-deploy.yml`: build/push e update no Container Apps.

Crie Secrets / Vars no repositório:
- Secret `AZURE_CREDENTIALS`
- Secrets `ACR_USERNAME`, `ACR_PASSWORD` (inicialmente; para prod use Managed Identity)
- Vars: `AZ_SUBSCRIPTION_ID`, `AZ_RESOURCE_GROUP`, `AZ_ACR_LOGIN_SERVER`, `CA_NAME`

Primeiro Commit
```
git add -A
git commit -m "chore: initial infra+app, CI, ignore secrets"
```
