# 03. Calling Foundry Models from Copilot (BYOK)

This document covers how to call Foundry models — or models routed through APIM — from VS Code Copilot Chat and the GitHub Copilot CLI.

## What this document covers

- Adding a BYOK model in VS Code Copilot Chat
- Configuring a custom provider in the GitHub Copilot CLI
- The difference between using an API key and an Entra ID bearer token
- Moving to production through an APIM gateway

## 0. Prerequisites (common)

- **Endpoint URL**: For a direct connection, use `https://<resource-name>.openai.azure.com` or `https://<resource-name>.services.ai.azure.com/openai/v1`. After moving to production, use the APIM gateway URL.
- **Deployment name**: e.g., `my-gpt4o-prod`. In Copilot settings it's used like a model ID.
- **Model requirements**: **tool calling + streaming** support is required. A context window of **128k or more is recommended**.
- **Authentication**: VS Code Copilot Chat can configure Entra ID in the Azure provider, while the Copilot CLI's custom provider uses an API key or bearer token environment variable.

The recommended authentication method differs by who is making the call.

- **App/service code**: Use **Entra ID / Managed Identity**, like the production-recommended approach in [02. API Calls](02-api-calls.md).
- **VS Code Copilot Chat**: **Entra ID is possible**, and an API key works too. The VS Code BYOK Azure provider example shows an Entra ID auth configuration.
- **GitHub Copilot CLI**: Uses an **API key or Entra ID bearer token**. The official BYOK docs focus on API key examples, but based on the CLI help and actual testing, `COPILOT_PROVIDER_BEARER_TOKEN` is also supported.

> To use it in agent mode (file editing/tool execution), the model must support **tool calling** (e.g., gpt-4o, gpt-4.1).

## Part A. VS Code Copilot Chat

### A-1. Steps to add

1. Open the Copilot **Chat** window.
2. **Model selector** → **gear / Manage Models** icon (or the command palette `Ctrl+Shift+P` → **"Chat: Manage Language Models"**)
![ghcp-01](../images/ghcp-01.png)

3. **Add Models** → choose **Azure** as the provider
![ghcp-02](../images/ghcp-02.png)

4. Enter a **group name** → enter the **endpoint URL** and authentication info
5. VS Code opens `chatLanguageModels.json` to set model properties (`id`, `name`, `url`, tool calling/vision/token limits, etc.)
6. Save → the Azure model **appears in the model selector**.
![ghcp-03](../images/ghcp-03.png)

### A-2. `chatLanguageModels.json` example

The example below follows the Azure provider format from the official VS Code docs. It is based on a configuration where there is no `apiKey` field and the Azure provider calls the Azure OpenAI/Foundry deployment with Entra ID authentication.

```jsonc
[
  {
    "name": "Azure",
    "vendor": "azure",
    "models": [
      {
        "id": "my-gpt4o-prod",
        "name": "Foundry GPT-4o (internal)",
        "url": "https://<resource-name>.openai.azure.com",
        "toolCalling": true,
        "vision": true,
        "maxInputTokens": 128000,
        "maxOutputTokens": 16384
      }
    ]
  }
]
```

> BYOK feature scope and availability may vary by Copilot plan (per the VS Code docs).

## Part B. GitHub Copilot CLI

The GitHub Copilot CLI can be configured to use **its own model provider** instead of GitHub-hosted models. Supported: **Azure OpenAI**, OpenAI-compatible endpoints (including Ollama and vLLM), and Anthropic.

The official BYOK docs mostly show `COPILOT_PROVIDER_API_KEY` examples, but per the current CLI's `copilot help providers`, `COPILOT_PROVIDER_BEARER_TOKEN` is also supported. In other words, unlike the VS Code Azure provider it does not automatically reuse your login state, but you can call a Foundry endpoint by putting an Entra ID access token issued via the Azure CLI into the bearer token.

In actual testing, calling the remote Foundry endpoint for the `Kimi-K2.6-1` deployment without an API key returned a 401, while putting a token obtained from `az account get-access-token` into `COPILOT_PROVIDER_BEARER_TOKEN` returned a normal response.

### B-1. Configure with environment variables

- `COPILOT_PROVIDER_TYPE`: Use `azure` for an Azure OpenAI native endpoint, and `openai` for a Foundry `/openai/v1`-compatible endpoint.
- `COPILOT_PROVIDER_BASE_URL`: e.g., `https://<resource-name>.services.ai.azure.com/openai/v1` or `https://<resource-name>.openai.azure.com/openai/v1`
- `COPILOT_PROVIDER_API_KEY`: Used with the API key method.
- `COPILOT_PROVIDER_BEARER_TOKEN`: Used with the Entra ID bearer token method. Takes precedence over the API key.
- `COPILOT_MODEL`: Put the deployment name here. e.g., `my-gpt4o-prod`, `Kimi-K2.6-1`

**bash / zsh (macOS·Linux) - Entra ID bearer token method**:

```bash
export COPILOT_PROVIDER_BEARER_TOKEN=$(az account get-access-token \
  --resource https://cognitiveservices.azure.com \
  --query accessToken -o tsv)

export COPILOT_PROVIDER_BASE_URL="https://ai-account-qbitb34amoe7c.services.ai.azure.com/openai/v1"
export COPILOT_PROVIDER_TYPE="openai"
export COPILOT_MODEL="Kimi-K2.6-1"

copilot
```

**bash / zsh (macOS·Linux) - API key method**:

```bash
export COPILOT_PROVIDER_TYPE="openai"
export COPILOT_PROVIDER_BASE_URL="https://<resource-name>.services.ai.azure.com/openai/v1"
export COPILOT_PROVIDER_API_KEY="<API_KEY>"
export COPILOT_MODEL="<deployment-name>"

copilot
```

![ghcp-04](../images/ghcp-04.png)
![ghcp-05](../images/ghcp-05.png)

> Run `copilot help providers` to check the current configuration and supported providers. This help explains that `COPILOT_PROVIDER_BEARER_TOKEN` takes precedence over the API key.

> Bearer tokens expire quickly. If you open a new terminal or the token expires, you must reissue it with `az account get-access-token`.

> Don't set `COPILOT_PROVIDER_API_KEY` and `COPILOT_PROVIDER_BEARER_TOKEN` at the same time. When testing, removing the unused value with something like `unset COPILOT_PROVIDER_API_KEY` reduces confusion.

### B-2. Why it doesn't appear in the model list

A BYOK model is not registered in the GitHub-hosted model catalog; instead, the provider and model specified via environment variables are applied to the current CLI session. As a result, a Foundry deployment name like `Kimi-K2.6-1` may not appear in the `/model` list.

Instead, specify the model in one of these ways.

- `COPILOT_MODEL=<deployment-name>`
- `COPILOT_PROVIDER_MODEL_ID=<a well-known reference model ID>` + `COPILOT_PROVIDER_WIRE_MODEL=<the actual deployment name to send to the provider>`
- `--model <deployment-name>` at runtime

`COPILOT_MODEL` is the simplest method, setting both the internal model ID and the wire model name passed to the provider to the same value.

### B-3. Switching models

- Switch GitHub-hosted models during a session with the `/model` slash command.
- For BYOK models, specifying them via environment variables (`COPILOT_MODEL`, `COPILOT_PROVIDER_WIRE_MODEL`) is the clearest approach.
- You can also specify it with the `--model <deployment-name>` option at runtime.

### B-4. Requirements

- A custom model must support **tool calling (function calling) + streaming**.
- A context window of **128k or more is recommended**.

## Part C. Moving to production — connecting through an APIM gateway

For both VS Code Copilot and the Copilot CLI, in production point the endpoint at the **APIM endpoint from [04. End-to-End API Call Governance Architecture](04-api-governance-architecture.md) instead of connecting directly to Foundry**.

![Copilot call production transition flow](../images/03-copilot-apim-governance-flow.svg)

→ **Both your app's API calls and developers' Copilot usage** are included in the same token limits, metrics, and logging, keeping company-wide governance consistent.

- VS Code: Change the `url` in `chatLanguageModels.json` to the APIM gateway URL, and add `requestHeaders` to the model entry if an APIM subscription key is required
- Copilot CLI: Point the `azure` provider at the APIM gateway root URL, and configure APIM's Azure OpenAI-compatible API to accept the `api-key` header as the subscription key

### C-1. Adding an APIM API in VS Code Copilot Chat

When attaching an API in VS Code that requires an APIM subscription key, add the APIM model under the existing Azure provider and include `requestHeaders` inside the model object.

**Example registering both a direct Foundry connection and an APIM-routed model**:

```jsonc
[
  {
    "name": "Azure",
    "vendor": "azure",
    "models": [
      {
        "id": "Kimi-K2.6-1",
        "name": "Kimi K2.6 1",
        "url": "https://ai-account-qbitb34amoe7c.services.ai.azure.com/openai/v1",
        "toolCalling": true,
        "vision": false,
        "maxInputTokens": 128000,
        "maxOutputTokens": 16000
      },
      {
        "id": "gpt-4o",
        "name": "GPT-4o via APIM",
        "url": "https://apim-ai-gw-eastus-demo.azure-api.net/models/chat/completions",
        "toolCalling": false,
        "vision": true,
        "maxInputTokens": 128000,
        "maxOutputTokens": 16000,
        "requestHeaders": {
          "Ocp-Apim-Subscription-Key": "<APIM_SUBSCRIPTION_KEY>"
        }
      }
    ]
  }
]
```

> Verification result: Calling without `requestHeaders` produces a `missing subscription key` error from APIM. Adding `Ocp-Apim-Subscription-Key` passes APIM authentication. If a `content_filter` error occurs afterward, it's not an APIM connection issue but the backend Azure OpenAI/Foundry content filter blocking the prompt.

### C-2. Calling an APIM API from the Copilot CLI

For the Copilot CLI, rather than calling APIM's `/models/chat/completions` path with the `openai` provider, the correct approach is to call APIM's Azure OpenAI-compatible API (`/openai/deployments/{deployment-id}/chat/completions`) with the `azure` provider.

First check whether the APIM API's subscription key header name is `api-key`.

```bash
az apim api show \
  --resource-group rg-ai-foundry \
  --service-name apim-ai-gw-eastus-demo \
  --api-id azure-openai-api \
  --query "subscriptionKeyParameterNames" \
  -o json
```

If the result's `header` value is not `api-key`, change it as follows.

```bash
az apim api update \
  --resource-group rg-ai-foundry \
  --service-name apim-ai-gw-eastus-demo \
  --api-id azure-openai-api \
  --subscription-key-header-name api-key \
  --subscription-key-query-param-name subscription-key
```

Here's an example of running the Copilot CLI through APIM.

```bash
export COPILOT_PROVIDER_TYPE="azure"
export COPILOT_PROVIDER_BASE_URL="https://apim-ai-gw-eastus-demo.azure-api.net"
export COPILOT_PROVIDER_API_KEY="<APIM_SUBSCRIPTION_KEY>"
export COPILOT_PROVIDER_AZURE_API_VERSION="2024-10-21"
export COPILOT_MODEL="gpt-4o"

copilot -p "Reply with exactly: APIM_CLI_OK"
```

With this configuration, the Copilot CLI calls the following APIM path.

```text
https://apim-ai-gw-eastus-demo.azure-api.net/openai/deployments/gpt-4o/chat/completions?api-version=2024-10-21
```

> Verification result: The configuration above confirmed an `APIM_CLI_OK` response. The `openai` provider + `/models` API combination may fail because the model validation/call path doesn't match the APIM route.

## Next steps

Once both direct API calls and Copilot calls are verified, proceed to **[04. End-to-End API Call Governance Architecture](04-api-governance-architecture.md)**, which consolidates these calls into a single entry point for control.

## Reference docs

- [VS Code – Language models / BYOK](https://code.visualstudio.com/docs/copilot/customization/language-models)
- [GitHub Copilot in VS Code](https://code.visualstudio.com/docs/copilot/overview)
- [Use BYOK models in GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models)
- [About GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli)
- [Azure OpenAI in Microsoft Foundry Models v1 API](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/how-to/use-chat-completions)
- [Azure OpenAI Entra ID / managed identity authentication](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/managed-identity)
- [Authenticate and authorize access to LLM APIs with APIM](https://learn.microsoft.com/en-us/azure/api-management/api-management-authenticate-authorize-ai-apis)
