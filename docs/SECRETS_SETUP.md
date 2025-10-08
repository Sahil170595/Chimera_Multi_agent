# Secrets Management Setup

Muse Protocol supports multiple secrets backends for production deployments.

## Backends

### 1. Environment Variables (Default)
```bash
# Load from env.local
export $(grep -v '^#' env.local | xargs)
python -m apps.muse_cli watcher
```

### 2. Azure Key Vault

**Setup:**
```bash
# Install Azure SDK
pip install azure-keyvault-secrets azure-identity

# Set vault URL
export AZURE_KEYVAULT_URL="https://muse-vault.vault.azure.net/"
export SECRETS_BACKEND="azure_keyvault"

# Authenticate (one of):
# - Azure CLI: az login
# - Managed Identity (in Azure)
# - Service Principal: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
```

**Migrate secrets:**
```bash
# Upload secrets to Azure Key Vault
az keyvault secret set --vault-name muse-vault --name CH-HOST --value "..."
az keyvault secret set --vault-name muse-vault --name DD-API-KEY --value "..."
# ... repeat for all secrets
```

### 3. AWS Secrets Manager

**Setup:**
```bash
# Install AWS SDK
pip install boto3

# Set region
export AWS_REGION="us-east-1"
export SECRETS_BACKEND="aws_secrets"

# Authenticate (one of):
# - AWS CLI: aws configure
# - IAM Role (in EC2/ECS)
# - Environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

**Migrate secrets:**
```bash
# Upload secrets to AWS Secrets Manager
aws secretsmanager create-secret --name CH_HOST --secret-string "..."
aws secretsmanager create-secret --name DD_API_KEY --secret-string "..."
# ... repeat for all secrets
```

### 4. Doppler

**Setup:**
```bash
# Install Doppler CLI
curl -Ls https://cli.doppler.com/install.sh | sh

# Login
doppler login

# Set project
export DOPPLER_PROJECT="muse"
export DOPPLER_TOKEN="dp.st.xxxx"
export SECRETS_BACKEND="doppler"
```

**Migrate secrets:**
```bash
# Upload secrets to Doppler
doppler secrets set CH_HOST="..." --project muse
doppler secrets set DD_API_KEY="..." --project muse
# ... repeat for all secrets

# Or bulk import from env.local
doppler secrets upload env.local --project muse
```

## Usage in Code

```python
from integrations.secrets import init_secrets, get_secret, SecretsBackend

# Initialize (once at startup)
init_secrets(SecretsBackend.AZURE_KEYVAULT)

# Get secrets
ch_host = get_secret("CH_HOST")
dd_api_key = get_secret("DD_API_KEY")
```

## Docker Deployment

### With Azure Key Vault
```yaml
services:
  orchestrator:
    environment:
      - AZURE_KEYVAULT_URL=https://muse-vault.vault.azure.net/
      - SECRETS_BACKEND=azure_keyvault
      - AZURE_CLIENT_ID=...
      - AZURE_CLIENT_SECRET=...
      - AZURE_TENANT_ID=...
```

### With AWS Secrets Manager
```yaml
services:
  orchestrator:
    environment:
      - AWS_REGION=us-east-1
      - SECRETS_BACKEND=aws_secrets
      - AWS_ACCESS_KEY_ID=...
      - AWS_SECRET_ACCESS_KEY=...
```

### With Doppler
```yaml
services:
  orchestrator:
    environment:
      - DOPPLER_TOKEN=dp.st.xxxx
      - DOPPLER_PROJECT=muse
      - SECRETS_BACKEND=doppler
```

## Secret Rotation

### Azure Key Vault
```bash
# Update secret
az keyvault secret set --vault-name muse-vault --name DD-API-KEY --value "new-key"

# Restart service (secrets are fetched on startup)
docker-compose -f infra/docker-compose.prod.yml restart
```

### AWS Secrets Manager
```bash
# Update secret
aws secretsmanager update-secret --secret-id DD_API_KEY --secret-string "new-key"

# Restart service
docker-compose -f infra/docker-compose.prod.yml restart
```

### Doppler
```bash
# Update secret
doppler secrets set DD_API_KEY="new-key" --project muse

# Restart service (Doppler can auto-restart on change)
docker-compose -f infra/docker-compose.prod.yml restart
```

## Best Practices

1. **Never commit secrets** to git (`.gitignore` includes `env.local`, `.env.*`)
2. **Use managed identities** in cloud (Azure Managed Identity, AWS IAM Role)
3. **Rotate secrets regularly** (every 90 days minimum)
4. **Audit access** via vault logs (Azure Monitor, AWS CloudTrail, Doppler Audit Log)
5. **Principle of least privilege** - only grant access to needed secrets
6. **Separate environments** - use different vaults for dev/staging/prod
