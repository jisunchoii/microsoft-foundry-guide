# 03b. Calling Foundry Models from Claude Code (via LiteLLM)

This document covers how to call models deployed in Foundry (Kimi, Grok, GLM, etc.) from Claude Code (Anthropic's official CLI).

> ⚠️ **This is an experimental/reference document.** This setup depends on a third-party open-source proxy (LiteLLM) and is not an official integration path endorsed by Anthropic or Microsoft. The behavior has been verified, but before adopting it in production, review the "official/unofficial boundary" below and judge whether it fits your organization's security and support policies.
>
> **Officially supported parts**
> - Claude Code's gateway connection (`ANTHROPIC_BASE_URL`) and model configuration parameters — [Anthropic official docs](https://code.claude.com/docs/en/llm-gateway)
> - Foundry's Entra ID (keyless) authentication — [Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/configure-entra-id)
>
> **Unofficial (at-your-own-risk) areas**
> - **Dependence on the LiteLLM proxy**: Anthropic's docs present LiteLLM as an example but explicitly state it is "a third-party product that we do not endorse, maintain, or audit." Responsibility for security patches, version management, and operations lies with the adopting organization.
> - **Anthropic↔OpenAI format conversion**: tool calling and streaming conversion depend on LiteLLM's implementation, so some features may have friction depending on the model/version.
> - **Mapping non-Claude models to the opus/sonnet/haiku aliases**: This is a working configuration but not a pattern Anthropic recommends.

## What this document covers

- Claude Code's model connection method and format constraints
- Connecting to Foundry models via the LiteLLM proxy
- Auto-refreshing Entra ID authentication instead of an API key
- Switching between multiple Foundry models with `/model`
- Moving to production through an APIM gateway

## 0. Prerequisites (common)

- **Endpoint URL**: Use the Foundry resource root `https://<resource-name>.services.ai.azure.com`. After moving to production, use the APIM gateway URL.
- **Deployment name**: e.g., `Kimi-K2.6-1`. Used as the model routing target in the LiteLLM `config.yaml`.
- **Model requirements**: **tool calling + streaming** support is required. A context window of **128k or more is recommended**.
- **Authentication**: Entra ID (keyless) is recommended. LiteLLM issues and refreshes tokens automatically via `DefaultAzureCredential`, so no API key is needed.

> To use it in agent mode (file editing/tool execution), the model must support **tool calling** (e.g., Kimi-K2, Grok).

## 1. Why a proxy is needed — format differences

Claude Code uses the **Anthropic Messages API** (`/v1/messages`) format when calling a model. The endpoint that `ANTHROPIC_BASE_URL` points to must expose this format.

In contrast, Kimi, Grok, GLM, etc. deployed in Foundry expose only the **OpenAI-compatible format** (`/openai/v1/chat/completions`). So simply changing the base URL to Foundry won't work; you need a gateway in the middle that **converts between the Anthropic and OpenAI formats**.

```text
Claude Code  ──(/v1/messages, Anthropic)──▶  LiteLLM  ──(OpenAI-compatible + Entra ID token)──▶  Foundry (Kimi / Grok / GLM)
```

[LiteLLM](https://docs.litellm.ai/) is an open-source proxy that provides this conversion out of the box. It also handles tool calling, streaming, and thinking-block mapping.


## 2. LiteLLM proxy setup

### 2-1. Install

```bash
pip install "litellm[proxy]"
```

> LiteLLM versions 1.82.7 / 1.82.8 have a security issue, so use a different version.

### 2-2. `config.yaml` sample

You can register multiple Foundry deployments in a single proxy. For authentication, use `enable_azure_ad_token_refresh` for automatic Entra ID refresh (no API key needed).

```yaml
model_list:
  - model_name: kimi-k2
    litellm_params:
      model: azure_ai/Kimi-K2.6-1
      # Root endpoint only (don't append /openai/v1). azure_ai builds the path.
      api_base: os.environ/AZURE_AI_API_BASE_ROOT
  - model_name: grok-4
    litellm_params:
      model: azure_ai/<grok deployment name>
      api_base: os.environ/AZURE_AI_API_BASE_ROOT
  - model_name: glm-5
    litellm_params:
      model: azure_ai/<glm deployment name>
      api_base: os.environ/AZURE_AI_API_BASE_ROOT

litellm_settings:
  drop_params: true
  # Automatic token refresh based on DefaultAzureCredential (scope: cognitiveservices.azure.com/.default)
  # Uses the az login session; refreshes automatically on token expiry without restarting the proxy.
  enable_azure_ad_token_refresh: true

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

### 2-3. Run

```bash
export PYTHONUTF8=1                                                    # Windows console encoding
export AZURE_AI_API_BASE_ROOT="https://<resource-name>.services.ai.azure.com"
export LITELLM_MASTER_KEY="sk-local-anything"                         # Arbitrary key Claude Code will send

litellm --config config.yaml --port 4000 --host 127.0.0.1
```



## 3. Connecting Claude Code

Claude Code specifies the endpoint via environment variables or a settings file. To avoid mixing with existing settings, we recommend creating a **separate settings file** and launching it with `--settings`.

### 3-1. `claude-foundry-settings.json` example

To display models cleanly in the `/model` selector, map Claude Code's `opus`/`sonnet`/`haiku` alias slots 1:1 to Foundry models.

```jsonc
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:4000",
    "ANTHROPIC_AUTH_TOKEN": "sk-local-anything",
    "ANTHROPIC_CUSTOM_HEADERS": "",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",

    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k2",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "Kimi K2.6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION": "Moonshot Kimi via Foundry",

    "ANTHROPIC_DEFAULT_SONNET_MODEL": "grok-4",
    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "Grok 4.3",
    "ANTHROPIC_DEFAULT_SONNET_MODEL_DESCRIPTION": "xAI Grok via Foundry",

    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "GLM 5.1",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_DESCRIPTION": "Z.ai GLM via Foundry"
  },
  "model": "opus",
  "availableModels": ["opus", "sonnet", "haiku"]
}
```

### 3-2. Run

```bash
claude --settings claude-foundry-settings.json
```


## 4. Switching models

- During a session, open the selector with the `/model` slash command to switch. With the configuration above, the selector displays as follows.

  ```text
  Select model
   1. Default (recommended)
   2. Kimi K2.6      Moonshot Kimi via Foundry
   3. Grok 4.3       xAI Grok via Foundry
   4. GLM 5.1        Z.ai GLM via Foundry
  ```

  ![cc-02](../images/cc-02.png)


- You can also specify by alias directly: `/model opus` (Kimi), `/model sonnet` (Grok), `/model haiku` (GLM).
- You can also specify it at launch, like `claude --settings ... --model sonnet`.


![cc-04](../images/cc-04.png)


## 5. Requirements

- A custom model must support **tool calling (function calling) + streaming**.
- A context window of **128k or more is recommended**.
- Some Claude-only features such as effort levels and extended thinking may not be recognized by non-Claude models. Basic chat, coding, and tool calling work normally.

## Part C. Moving to production — connecting through an APIM gateway

In production, point LiteLLM's backend (`api_base`) at the **APIM endpoint from [04. End-to-End API Call Governance Architecture](04-api-governance-architecture.md) instead of connecting directly to Foundry**.

→ **Both your app's API calls and developers' Claude Code usage** are included in the same token limits, metrics, and logging, keeping company-wide governance consistent.

- Change `api_base` in the LiteLLM `config.yaml` to the APIM gateway URL, and if an APIM subscription key is required, add the `Ocp-Apim-Subscription-Key` header to `litellm_params` via `extra_headers`.
- APIM itself is not a converter (it does OpenAI-compatible/pass-through routing). Claude Code's Anthropic↔OpenAI conversion is still handled by LiteLLM, while APIM sits in front of it for authentication, token limits, and logging — this two-tier setup is the most robust.
![cc-05](../images/cc-05.png)
![cc-06](../images/cc-06.png)


## Checklist before production adoption

This document is for experimentation/verification. If you're considering actual adoption, check at least the following.

- **Who operates the proxy**: Make clear who is responsible for LiteLLM's deployment, version management, and security patches. Isolate it in a container and pin a trusted version.
- **Authentication path**: Local `az login`-based auth is for development. In production, switch to a Managed Identity or service principal.
- **Governance integration**: If you need token limits, logging, and metrics, build a two-tier setup with APIM in front ([04. Governance Architecture](04-api-governance-architecture.md)).
- **Support scope**: If issues arise, official Anthropic/Microsoft support may not cover a configuration routed through LiteLLM.
- **Consider alternatives**: If a third-party proxy is a burden under your organization's policies, first consider the [Copilot integration (03)](03-copilot-foundry-integration.md), which has a clear official path.

## Next steps

Once direct API calls and Copilot/Claude Code calls are all verified, proceed to **[04. End-to-End API Call Governance Architecture](04-api-governance-architecture.md)**, which consolidates these calls into a single entry point for control.

## Reference docs

- [Claude Code – LLM gateway configuration](https://code.claude.com/docs/en/llm-gateway)
- [Claude Code – Model configuration](https://code.claude.com/docs/en/model-config)
- [LiteLLM – Azure AI Studio provider](https://docs.litellm.ai/docs/providers/azure_ai)
- [LiteLLM – Azure AD token refresh](https://docs.litellm.ai/docs/providers/azure/)
- [Azure OpenAI in Microsoft Foundry Models v1 API](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/how-to/use-chat-completions)
- [Keyless authentication (Microsoft Entra ID) configuration](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/configure-entra-id)
- [Authenticate and authorize access to LLM APIs with APIM](https://learn.microsoft.com/en-us/azure/api-management/api-management-authenticate-authorize-ai-apis)
