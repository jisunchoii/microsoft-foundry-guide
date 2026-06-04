# Microsoft Foundry Adoption Guide

This guide is structured so that a team adopting Microsoft Foundry for the first time can verify the following flow in order.

- Understand Foundry's resource, project, and deployment concepts
- Configure Foundry resources and model deployments via the portal or the Azure CLI
- Verify model calls using both the API Key and Microsoft Entra ID methods
- Connect Foundry models from VS Code Copilot Chat, the GitHub Copilot CLI, and Claude Code
- Govern both app and developer-tool calls together with the APIM AI gateway

## Guide structure

Each document can be read independently, but for first-time adoption we recommend the order below.

### 00. Concepts

[Open document](docs/00-concepts.md)

- The relationship between Foundry resources, projects, and deployments
- The difference between resource-based and Hub-based projects
- The difference between deployment names and model names
- The basics of Microsoft Entra ID and keyless authentication

### 01. Entra ID + Foundry Setup

[Portal guide](docs/01-setup-portal.md) | [CLI guide](docs/01-setup-cli.md)

- Creating a Resource Group, Foundry resource, and default project
- Deploying a model and choosing a deployment type
- Granting developers the Foundry User role
- A portal-based manual track and a CLI-based automation track

### 02. API Calls

[Open document](docs/02-api-calls.md)

- Calling with the API Key method
- Keyless calls based on Microsoft Entra ID
- Examples based on the Python SDK and the Responses API
- The difference in authentication flow between local development and production

### 03. Calling Foundry Models from Copilot

[Open document](docs/03-copilot-foundry-integration.md)

- VS Code Copilot Chat BYOK setup
- GitHub Copilot CLI custom provider setup
- The difference between API Key, bearer token, and APIM-routed calls
- Verified Kimi and APIM call patterns

### 03b. Calling Foundry Models from Claude Code (experimental/reference)

[Open document](docs/03b-claude-code-foundry-integration.md)

> An unofficial configuration that depends on a third-party proxy (LiteLLM). The official/unofficial boundary and a production checklist are laid out within the document.

- Connecting via the LiteLLM proxy (Anthropic ↔ OpenAI format conversion)
- Auto-refreshing Entra ID authentication (no API Key needed)
- Switching between multiple Foundry models such as Kimi, Grok, and GLM with `/model`
- Moving to production through an APIM gateway

### 04. End-to-End API Call Governance Architecture

[Open document](docs/04-api-governance-architecture.md)

- A central entry point via the APIM AI gateway
- Token limits, quotas, logging, and metric collection
- Observability based on Application Insights and Azure Monitor
- A link to an enterprise reference architecture

## Getting started

1. If the concepts are unfamiliar, start with [00. Concepts](docs/00-concepts.md).
2. To follow along on screen, do the [Portal setup](docs/01-setup-portal.md); to verify automation, do the [CLI setup](docs/01-setup-cli.md).
3. After deploying a model, verify direct calls in [API Calls](docs/02-api-calls.md).
4. If you need developer-tool integration, proceed with the [Copilot integration](docs/03-copilot-foundry-integration.md) or the [Claude Code integration](docs/03b-claude-code-foundry-integration.md).
5. When moving to production, consolidate the call paths with the [APIM governance architecture](docs/04-api-governance-architecture.md).

## Authoring notes

- Authored: 2026-06
- Microsoft Foundry updates rapidly, so verify the latest details in the Microsoft Learn links within each document before applying.
- The body uses Microsoft Foundry as the default name to reflect the product rebranding, and notes the Azure AI Foundry name alongside it where needed.
