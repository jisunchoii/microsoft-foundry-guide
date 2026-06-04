# 00. Core Concepts

Before using Microsoft Foundry, this document covers the resource structure, project types, deployment names, and authentication concepts you need to know.

## What this document covers

- The Foundry resource hierarchy
- The difference between resource-based and Hub-based projects
- Deployment names used when calling the API
- Microsoft Entra ID and keyless authentication

## 1. Overall structure

- **Subscription**: The top-level boundary for billing and payment
- **Resource group**: A bundle of resources managed and deleted together
- **Foundry resource**: The entire AI environment. The unit of security, monitoring, and billing
- **Project**: A workspace inside the resource. The unit for managing agents, evaluations, files, connections, and permissions
- **Deployment**: A callable model created on the Foundry resource. You use the deployment name when calling the API

## 2. Resource-based project vs. Hub-based project

Foundry has two project types. **New customers should always start with the "resource-based (new portal)" type.**

| Aspect | Resource-based project (new) | Hub-based project (classic) |
|------|----------------------------|----------------------------|
| Status | **Focus of new investment** | Maintenance mode |
| Portal | New Foundry portal (`ai.azure.com`) | Foundry (classic) portal |
| Foundation | Foundry resource | Hub (based on Azure ML workspace) |
| SDK | `azure-ai-projects` 2.x | Legacy packages |
| Endpoint | Single project endpoint | Multiple endpoints |
| API version | Stable v1 path (`/openai/v1/`) | Monthly `api-version` |

## 3. The key to deployments — "deployment name, not model name"

- When you deploy a model, you choose the **deployment name** yourself (e.g., model `gpt-4o` → deployment name `my-gpt4o-prod`).
- **When calling the API, you use the deployment name.** This is the biggest difference from the public OpenAI API.

```python
# Public OpenAI API style (model name)
client.responses.create(model="gpt-4o", input="...")

# Azure Foundry style (deployment name)
client.responses.create(model="my-gpt4o-prod", input="...")
```


## 4. Microsoft Entra ID — Azure's identity/permission system

**Microsoft Entra ID** (formerly Azure AD) is Azure's identity service that manages "who can do what."

- **RBAC (role-based access control)**: Controls permissions by assigning **roles** to users/apps.
- **Keyless authentication**: Instead of distributing API keys, authenticates with Entra ID tokens → eliminates key-leak risk, enables fine-grained permissions, and ensures traceability.
- **Managed Identity**: Lets apps running on Azure (VMs, Functions, etc.) authenticate automatically **without storing credentials**.

> Microsoft's official recommendation: *"Key-based authentication grants full access through the key, so it has no role restrictions. For security and fine-grained access control, we recommend Entra ID authentication."*

Detailed authentication methods are covered in [02. API Calls](02-api-calls.md).

## Next steps

Once you understand the concepts, proceed to [01. Entra ID + Foundry Setup (Portal)](01-setup-portal.md) or [(CLI)](01-setup-cli.md).


## Reference docs

- [What is Microsoft Foundry?](https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry)
- [Plan a Foundry rollout](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/planning)
- [Azure resource group concepts](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview)
- [What is Microsoft Entra ID?](https://learn.microsoft.com/en-us/entra/fundamentals/whatis)
