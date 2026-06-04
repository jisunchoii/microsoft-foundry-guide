# 01. Entra ID + Foundry Setup (CLI)

Use the Azure CLI to automate creating a Foundry resource, deploying a model, and granting RBAC permissions. This guide assumes you run the commands in a bash/zsh environment on Linux or macOS.

## Steps

- Check prerequisites
- Set variables and sign in to Azure
- Create a Resource Group and Foundry resource
- Deploy a model
- Grant Entra ID permissions to developers
- Verify the setup, or run the full script

## Prerequisites

- **Azure CLI**: [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) (version 2.x or later)
- **Permissions**: **Owner/Contributor** to create resources, and **Owner** or **User Access Administrator** to assign roles
- **Model access**: Some models have different availability by region and subscription

## Step 0 — Set variables & sign in

```bash
# Reusable variables (adjust values to your environment)
RG="rg-foundry-dev"
LOCATION="eastus"
RESOURCE="my-foundry-res"        # Foundry (= Cognitive Services account) name, globally unique
DEPLOYMENT="my-gpt4o-prod"       # Deployment name (used when calling the API)
MODEL="gpt-4o"
MODEL_VERSION="2024-11-20"
DEVELOPER="developer@contoso.com" # Change to the actual user UPN
SUBSCRIPTION=""                  # Enter a subscription ID or name if needed

# Sign in & select subscription
az account show >/dev/null || az login --use-device-code
if [[ -n "$SUBSCRIPTION" ]]; then
  az account set --subscription "$SUBSCRIPTION"
fi
```


## Step 1 — Create the resource group & Foundry resource

```bash
# Resource group
az group create --name "$RG" --location "$LOCATION"

# Create the Foundry (= AIServices) account — a custom subdomain is required for Entra ID auth
az cognitiveservices account create \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --kind AIServices \
  --sku S0 \
  --custom-domain "$RESOURCE" \
  --yes
```

Check the endpoint:

```bash
az cognitiveservices account show \
  --name "$RESOURCE" --resource-group "$RG" \
  --query "properties.endpoint" -o tsv
# e.g.: https://my-foundry-res.openai.azure.com/  (use the /openai/v1/ path when calling)
```



## Step 2 — Deploy a model

```bash
az cognitiveservices account deployment create \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --deployment-name "$DEPLOYMENT" \
  --model-name "$MODEL" \
  --model-version "$MODEL_VERSION" \
  --model-format OpenAI \
  --sku-capacity "1" \
  --sku-name "GlobalStandard"
```

> `--sku-name` values: `Standard`, `GlobalStandard`, `GlobalBatch`, `ProvisionedManaged`, `GlobalProvisionedManaged`, etc. (see [Choosing a deployment type](#reference--choosing-a-deployment-type)).
> `--sku-capacity` is the TPM-unit capacity (Standard family) or the number of PTUs (Provisioned).

Check the deployment:

```bash
az cognitiveservices account deployment list \
  --name "$RESOURCE" --resource-group "$RG" \
  --query "[].{name:name, model:properties.model.name, sku:sku.name}" -o table
```

> When calling the API you use the **deployment name (`$DEPLOYMENT`), not the model name**.



## Reference — Choosing a deployment type

| Deployment type | SKU code | Data processing location | Billing | Best for |
|-----------|----------|------------------|------|-------------|
| **Global Standard** | `GlobalStandard` | All Azure regions | Pay-as-you-go per token | **Getting started / general workloads** |
| Global Provisioned (PTU) | `GlobalProvisionedManaged` | All Azure regions | PTU reservation | Predictable high load, low latency |
| **Global Batch** | `GlobalBatch` | All Azure regions | **50% discount** (24h target) | Non-real-time, large-volume async |
| Data Zone Standard | `DataZoneStandard` | Within a data zone (US/EU) | Pay-as-you-go | EU/US data zone compliance |
| Standard | `Standard` | Single region | Pay-as-you-go | Regional compliance, low volume |
| Regional Provisioned | `ProvisionedManaged` | Single region | PTU reservation | Regional compliance + throughput |
| Developer | `DeveloperTier` | All regions | Pay-as-you-go | **Evaluation-only** for fine-tuned models |

**Recommended**: Start with `GlobalStandard` → move to `PTU` as traffic grows and latency matters → split large-volume async work to `GlobalBatch`. **Dev = Standard / Production = PTU**, and set a **TPM limit** to prevent overuse.

> To allow only specific types at the organization level, you can restrict `Microsoft.CognitiveServices/accounts/deployments/sku.name` with **Azure Policy**.

## Step 3 — Grant Entra ID permissions to developers

Assign an RBAC role instead of an API key. **Using the GUID is recommended.**

```bash
# Foundry User (least privilege) — calls models/agents
az role assignment create \
  --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
  --assignee "$DEVELOPER" \
  --scope "$(az cognitiveservices account show --name "$RESOURCE" --resource-group "$RG" --query id -o tsv)"
```

### Role GUID reference

| Role | Permission | Role GUID |
|------|------|-----------|
| **Foundry User** (formerly Azure AI User) | **Calls** models/agents (least privilege) | `53ca6127-db72-4b80-b1b0-d745d6d5456d` |
| **Foundry Project Manager** | Manages projects + grants the User role | `eadc314b-1a2d-4efa-be10-5d325db5065e` |
| **Foundry Account Owner** | Creates accounts/projects, manages models | `e47c6f54-e4a2-4754-9501-8e0985b135e1` |
| **Foundry Owner** | Full management + build (highest privilege) | `c883944f-8b7b-4483-af10-35834be79c4a` |

Verify the assignment:

```bash
az role assignment list \
  --assignee "$DEVELOPER" \
  --scope "$(az cognitiveservices account show --name "$RESOURCE" --resource-group "$RG" --query id -o tsv)" \
  --query "[].roleDefinitionName" -o table
```


## Step 4 — Verify the setup

Check the created endpoint, deployment, and role assignment status all at once.

```bash
az cognitiveservices account show \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --query properties.endpoint -o tsv

az cognitiveservices account deployment list \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --query "[].{name:name, model:properties.model.name, version:properties.model.version, sku:sku.name}" \
  -o table

az role assignment list \
  --assignee "$DEVELOPER" \
  --scope "$(az cognitiveservices account show --name "$RESOURCE" --resource-group "$RG" --query id -o tsv)" \
  --query "[].roleDefinitionName" -o table
```


## Full script (run it all at once)

```bash
#!/usr/bin/env bash
set -euo pipefail

RG="rg-foundry-dev-test"
LOCATION="eastus"
RESOURCE="my-foundry-res-$(date +%s)"   # The Foundry resource name must be globally unique
DEPLOYMENT="my-gpt4o-prod"
MODEL="gpt-4o"
MODEL_VERSION="2024-11-20"
DEVELOPER="developer@contoso.com"       # Change to the actual user UPN
SUBSCRIPTION=""                        # Enter a subscription ID or name if needed

az account show >/dev/null || az login --use-device-code
if [[ -n "$SUBSCRIPTION" ]]; then
  az account set --subscription "$SUBSCRIPTION"
fi

az group create --name "$RG" --location "$LOCATION"

az cognitiveservices account create \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --kind AIServices \
  --sku S0 \
  --custom-domain "$RESOURCE" \
  --yes

az cognitiveservices account deployment create \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --deployment-name "$DEPLOYMENT" \
  --model-name "$MODEL" \
  --model-version "$MODEL_VERSION" \
  --model-format OpenAI \
  --sku-capacity "1" \
  --sku-name "GlobalStandard"

SCOPE="$(az cognitiveservices account show \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --query id -o tsv)"

az role assignment create \
  --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
  --assignee "$DEVELOPER" \
  --scope "$SCOPE"

echo
echo "Setup complete"
echo "Resource group: $RG"
echo "Resource:       $RESOURCE"
echo "Deployment:     $DEPLOYMENT"
echo "Endpoint:"
az cognitiveservices account show \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --query properties.endpoint -o tsv

echo
echo "Deployments:"
az cognitiveservices account deployment list \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --query "[].{name:name, model:properties.model.name, version:properties.model.version, sku:sku.name}" \
  -o table

echo
echo "Role assignments for $DEVELOPER:"
az role assignment list \
  --assignee "$DEVELOPER" \
  --scope "$SCOPE" \
  --query "[].roleDefinitionName" \
  -o table
```

To clean up the resources after testing, run the following command.

```bash
az group delete --name rg-foundry-dev-test --yes --no-wait
```


## Next steps

[02. API Calls](02-api-calls.md) — Call the model with a key or Entra ID.

> To follow along in the GUI → [01. Setup (Portal)](01-setup-portal.md)

## Reference docs

- [az cognitiveservices account](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account)
- [az cognitiveservices account deployment](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment)
- [Understanding deployment types in Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types)
- [RBAC for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry)
- [Plan a Foundry rollout](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/planning)
- [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
