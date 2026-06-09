# 03c. Codex CLI에서 Foundry 모델 호출하기 (custom provider)

OpenAI Codex CLI에서 Foundry에 배포한 모델을 호출하고, 여러 모델을 전환하는 방법을 정리합니다.

## 이 문서에서 다루는 내용

- Codex CLI의 custom model provider 구성 방식과 `wire_api` 제약
- Azure OpenAI 계열 모델 직접 연결 (Entra ID 자동 갱신 / API key)
- 추론(reasoning) 모델 `gpt-5-mini`로 sub-agent(병렬 하위 에이전트)까지 사용
- LiteLLM 프록시를 경유해 Kimi·Grok·DeepSeek 등 비-OpenAI 모델 연결
- 모델별 tool calling / sub-agent 지원 매트릭스
- 프로파일과 `/model`로 여러 Foundry 모델 전환
- APIM 게이트웨이를 경유한 운영 전환 방식

## 0. 사전 준비 (공통)

- **Codex CLI 설치**: macOS·Linux는 `curl -fsSL https://chatgpt.com/codex/install.sh | sh`, Windows는 `winget install OpenAI.Codex`. 설치 후 `codex --version`으로 확인합니다.
- **엔드포인트 URL**: 직접 연결 시 `https://<리소스이름>.services.ai.azure.com/openai/v1` 또는 `https://<리소스이름>.cognitiveservices.azure.com/openai/v1`을 사용합니다. 운영 전환 후에는 APIM 게이트웨이 URL을 사용합니다.
- **배포 이름**: 예: `gpt-4.1`, `Kimi-K2.6-1`. Codex 설정에서 `model` 값으로 사용합니다.
- **모델 요건**: **툴 호출(tool calling) + 스트리밍** 지원 필수. 컨텍스트 윈도우는 **128k 이상 권장**입니다.
- **인증 방식**: Entra ID(키리스)를 권장합니다. Codex는 `[model_providers.<id>.auth]`로 외부 명령에서 bearer token을 받아 자동 갱신할 수 있어, `az account get-access-token`을 토큰 헬퍼로 지정하면 API key가 필요 없습니다.

> 에이전트 모드(파일 편집/툴 실행)로 쓰려면 모델이 반드시 **tool calling**을 지원해야 합니다 (예: gpt-4.1, gpt-5-mini, Kimi-K2). 더 나아가 **sub-agent(병렬 하위 에이전트)**까지 쓰려면 Azure OpenAI Responses 계열(gpt-4.1, gpt-5-mini)이 필요합니다. 모델별 지원 범위는 아래 [1-2. 모델별 tool calling / sub-agent 지원 매트릭스](#1-2-모델별-tool-calling--sub-agent-지원-매트릭스)를 참고하세요.

## 1. 핵심 제약 — Codex는 Responses API(`wire_api = "responses"`)만 사용

Codex CLI는 모델 공급자에 요청을 보낼 때 **Responses API** 와이어 포맷만 지원합니다. `config.toml`의 `model_providers.<id>.wire_api`는 `responses`가 유일한 값이며 생략 시 기본값입니다 (Chat Completions 와이어 포맷은 지원하지 않음).

이 제약이 Foundry 모델을 두 갈래로 나눕니다.

- **Azure OpenAI 계열** (gpt-4.1, gpt-4o, gpt-5 등): Foundry의 `v1` 엔드포인트가 **Responses API를 네이티브로 노출**하므로 **프록시 없이 직접 연결**할 수 있습니다. → **Part A**
- **비-OpenAI 계열** (Kimi, Grok, DeepSeek 등): Foundry에서 **Chat Completions 형식만 노출**합니다. Codex의 Responses 요청을 Chat Completions로 변환하는 게이트웨이가 중간에 필요합니다. → **Part B** (LiteLLM 경유)

```text
[Part A] Codex ──(/responses, Entra ID 토큰)──▶ Foundry (gpt-4.1)
[Part B] Codex ──(/responses)──▶ LiteLLM ──(chat completions + Entra ID 토큰)──▶ Foundry (Kimi / Grok / DeepSeek)
```

> 설정 파일 위치: Codex는 `CODEX_HOME`(기본 `~/.codex`, Windows는 `C:\Users\<사용자>\.codex`) 아래의 `config.toml`을 읽습니다. provider 정의(`model_provider`, `model_providers`)는 **사용자 레벨 `config.toml`에만** 둘 수 있고, 프로젝트 `.codex/config.toml`에서는 무시됩니다.

## Part A. Azure OpenAI 계열 직접 연결

### A-1. Entra ID 자동 갱신 (권장) — API key 불필요

Codex의 `[model_providers.<id>.auth]`는 외부 명령을 실행해 bearer token을 받고, `refresh_interval_ms` 주기로 **자동 갱신**합니다. `az account get-access-token`을 토큰 헬퍼로 지정하면 `az login` 세션을 그대로 재사용하므로 API key를 저장할 필요가 없습니다.

`~/.codex/config.toml`:

```toml
model = "gpt-4.1"
model_provider = "azure_foundry"

[model_providers.azure_foundry]
name = "Azure Foundry (Entra ID)"
base_url = "https://<리소스이름>.services.ai.azure.com/openai/v1"
wire_api = "responses"

[model_providers.azure_foundry.auth]
# macOS / Linux
command = "az"
args = ["account", "get-access-token",
        "--resource", "https://cognitiveservices.azure.com",
        "--query", "accessToken", "-o", "tsv"]
refresh_interval_ms = 1800000   # 30분마다 토큰 자동 갱신
timeout_ms = 15000
```

> **Windows 주의**: Windows에서 `az`는 배치 파일(`az.cmd`)이라 Codex가 직접 실행하지 못합니다. `cmd /c`로 감싸야 합니다.
>
> ```toml
> [model_providers.azure_foundry.auth]
> command = "cmd"
> args = ["/c", "az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv"]
> refresh_interval_ms = 1800000
> timeout_ms = 15000
> ```

토큰 헬퍼 명령은 **표준 출력으로 토큰만** 출력해야 합니다. Codex는 앞뒤 공백을 제거하고, 빈 토큰은 오류로 처리하며, `refresh_interval_ms` 주기로 미리 갱신합니다. `auth` 블록은 `env_key`·`experimental_bearer_token`과 **함께 쓸 수 없습니다**.

실행 (사전에 `az login` 필요):

```bash
codex                        # 대화형 TUI
codex exec "Reply with exactly: CODEX_AZURE_OK"   # 비대화형 1회 실행
```

> `az login` 세션이 살아 있으면 API key 없이 호출되고, 토큰 만료 전에 자동 갱신됩니다.

### A-2. API key 방식 (대안)

빠른 PoC나 `az login`을 쓰기 어려운 환경에서는 API key를 환경 변수로 넣을 수 있습니다. `env_key`에 **환경 변수 이름**을 지정합니다(키 값을 직접 넣지 않음).

```toml
model = "gpt-4.1"
model_provider = "azure_foundry_key"

[model_providers.azure_foundry_key]
name = "Azure Foundry (API key)"
base_url = "https://<리소스이름>.services.ai.azure.com/openai/v1"
wire_api = "responses"
env_key = "AZURE_FOUNDRY_API_KEY"
```

```bash
export AZURE_FOUNDRY_API_KEY="<API_KEY>"
codex exec "Reply with exactly: CODEX_AZKEY_OK"
```

> 보안 권고: API key는 전체 접근 권한을 가지므로 운영에서는 Entra ID(A-1)를 권장합니다. 또한 Foundry 리소스에 **로컬 인증 비활성화**(`disableLocalAuth=true`, 일부 조직은 Azure Policy로 강제) 정책이 적용되면 키 발급 자체가 막히고 키 호출이 401로 거부됩니다. 이때는 A-1의 Entra ID 방식을 사용하세요.

### A-3. 추론 모델 + sub-agent — `gpt-5-mini`

Azure OpenAI **추론(reasoning) 모델**인 `gpt-5-mini`는 Responses API를 네이티브로 노출하고, Codex가 보내는 **전체 툴 세트(`function` + sub-agent용 `namespace` 툴 포함)를 모두 수용**합니다. 즉 파일 편집·셸 실행뿐 아니라 **sub-agent(병렬 하위 에이전트) 생성·관리까지** Foundry 위에서 동작합니다.

같은 Azure OpenAI 계열이라 **A-1과 동일한 `azure_foundry` provider(Responses + Entra ID 자동 갱신)를 그대로 재사용**하고 모델 이름만 바꾸면 됩니다.

배포 (예: GlobalStandard):

```bash
az cognitiveservices account deployment create \
  --name <리소스이름> --resource-group <RG> \
  --deployment-name gpt-5-mini \
  --model-name gpt-5-mini --model-version 2025-08-07 \
  --model-format OpenAI --sku-name GlobalStandard --sku-capacity 50
```

실행 — provider는 그대로 두고 모델만 전환합니다.

```bash
codex exec --model gpt-5-mini "Reply with exactly: CODEX_GPT5MINI_OK"
```

추론 모델이므로 추론 강도/요약 옵션을 조절할 수 있습니다.

```toml
model = "gpt-5-mini"
model_provider = "azure_foundry"        # A-1과 동일 provider 재사용
model_reasoning_effort = "medium"        # minimal | low | medium | high
```

> `gpt-5-mini`는 Azure OpenAI 추론 모델이라 sub-agent 툴까지 수용하므로 `[features] multi_agent = false` 없이 기본 설정 그대로 에이전트 + sub-agent로 동작합니다(아래 [1-2 매트릭스](#1-2-모델별-tool-calling--sub-agent-지원-매트릭스) 참고).

## Part B. 비-OpenAI 모델 — LiteLLM 프록시 경유

Kimi·Grok·DeepSeek 등은 Foundry에서 Chat Completions만 노출하므로, Codex의 Responses 요청을 변환하는 [LiteLLM](https://docs.litellm.ai/) 프록시를 중간에 둡니다. LiteLLM은 Responses ↔ Chat Completions 변환과 Entra ID 토큰 자동 갱신을 제공합니다.

> 이 경로는 서드파티 오픈소스 프록시(LiteLLM)에 의존합니다. 운영 도입 전 [03b 문서의 공식/비공식 경계와 프로덕션 체크리스트](03b-claude-code-foundry-integration.md)를 함께 확인하세요.

### B-1. LiteLLM 설치 및 설정

```bash
pip install "litellm[proxy]"
```

> LiteLLM 1.82.7 / 1.82.8 버전은 보안 문제가 있으니 그 외 버전을 사용하세요. Python 3.14처럼 최신 런타임은 일부 의존성(`orjson`)의 사전 빌드 휠이 없을 수 있으니, 휠이 제공되는 **Python 3.12** 가상환경 사용을 권장합니다.

`litellm-config.yaml`:

```yaml
model_list:
  - model_name: kimi-k2
    litellm_params:
      model: azure_ai/Kimi-K2.6-1          # azure_ai/<배포이름>
      api_base: os.environ/AZURE_AI_API_BASE_ROOT

litellm_settings:
  drop_params: true
  enable_azure_ad_token_refresh: true       # DefaultAzureCredential 기반 토큰 자동 갱신

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

실행:

```bash
export PYTHONUTF8=1                                                   # Windows 콘솔 인코딩
export AZURE_AI_API_BASE_ROOT="https://<리소스이름>.services.ai.azure.com"
export LITELLM_MASTER_KEY="sk-local-anything"                         # Codex가 보낼 임의 키

litellm --config litellm-config.yaml --port 4000 --host 127.0.0.1
```

### B-2. Codex 프로파일로 LiteLLM provider 등록

provider 전환은 **프로파일 파일**로 깔끔하게 분리하는 것이 좋습니다. `~/.codex/litellm.config.toml`:

```toml
model = "kimi-k2"
model_provider = "litellm"

# 필수: Codex의 sub-agent(multi_agent) 툴을 끕니다.
# 이 툴은 type="namespace"로 전송되는데, Kimi 등 엄격한 비-OpenAI 백엔드는
# function 이외의 tool type을 거부(422)하므로 반드시 비활성화해야 합니다.
[features]
multi_agent = false

[model_providers.litellm]
name = "LiteLLM (Foundry non-OpenAI)"
base_url = "http://127.0.0.1:4000"
wire_api = "responses"
env_key = "LITELLM_MASTER_KEY"
```

실행:

```bash
export LITELLM_MASTER_KEY="sk-local-anything"
codex --profile litellm exec "Reply with exactly: CODEX_LITELLM_OK"
```

> **제약 — `multi_agent = false`는 필수**: 비-OpenAI 모델은 Foundry의 Chat Completions 엔드포인트가 `type: "function"` 툴만 허용합니다. `multi_agent`를 끄지 않으면 Codex가 sub-agent 툴을 `type: "namespace"`로 함께 보내고, 백엔드가 이를 거부합니다(Kimi·DeepSeek는 422, grok은 400). 일회성으로는 `-c 'features.multi_agent=false'`로도 끌 수 있습니다.
>
> 이 설정은 sub-agent만 끄며 파일 편집·셸 실행 등 일반 에이전트 기능에는 영향이 없습니다. 배포 용량이 낮으면(`--sku-capacity 1`) 큰 컨텍스트 요청이 `429 RateLimitReached`를 유발하니 테스트 시 용량을 충분히(예: 50) 올리세요.

## 1-2. 모델별 tool calling / sub-agent 지원 매트릭스

Codex는 에이전트 모드에서 항상 **툴 목록을 함께 전송**합니다. 그중 sub-agent(병렬 하위 에이전트) 툴은 OpenAI Responses 규격의 `function`이 아닌 **`type: "namespace"`** 로 전송됩니다. 모델·백엔드별 수용 범위가 달라 다음과 같이 정리됩니다(실측).

| 모델 | 형식 / 연결 | `function` 툴 | sub-agent(`namespace`) | Codex 사용 |
|------|------------|:------------:|:----------------------:|-----------|
| **gpt-4.1** | Azure OpenAI / 직결(Part A) | ✅ | ✅ | 에이전트 + sub-agent |
| **gpt-5-mini** | Azure OpenAI 추론 / 직결(A-3) | ✅ | ✅ | 에이전트 + sub-agent |
| **Kimi-K2** | MoonshotAI / LiteLLM(Part B) | ✅ | ❌ (422 거부) | 에이전트만 (`multi_agent=false` 필요) |
| **grok-4.3** | xAI / LiteLLM(Part B) | ✅ | ❌ (400 거부) | 에이전트만 (`multi_agent=false` 필요) |
| **DeepSeek-V3.1** | DeepSeek / LiteLLM(Part B) | ✅ | ❌ (422 거부) | 에이전트만 (`multi_agent=false` 필요) |
| **MiniMax-M2.5** | Fireworks / LiteLLM(Part B) | ✅ | ❌ (422 거부) | 에이전트만 (`multi_agent=false` 필요) |
| **GLM-5.1** | Fireworks / LiteLLM(Part B) | ✅ | ❌ (422 거부) | 에이전트만 (`multi_agent=false` 필요) |

핵심 결론:

- **sub-agent까지 쓰려면 Azure OpenAI Responses 계열(gpt-4.1, gpt-5-mini)** 을 사용하세요. `namespace` 툴을 네이티브로 수용합니다.
- **비-OpenAI 모델(Kimi·grok-4.3·DeepSeek-V3.1·MiniMax-M2.5·GLM-5.1)은 sub-agent를 쓸 수 없습니다.** 이들이 공유하는 Azure AI 모델 추론(Chat Completions) 엔드포인트가 `type: "function"` 외의 툴 타입을 거부하기 때문이며, 특정 모델만의 문제가 아닙니다. `[features] multi_agent = false`로 sub-agent만 끄면 일반 에이전트로는 정상 동작합니다(Part B).

> 참고: 위 매트릭스는 "Codex가 보내는 툴을 백엔드가 받아들이는지"에 대한 것입니다. 받아들여진 뒤의 **tool calling 품질**(얼마나 정확히 툴을 호출하는지)은 모델마다 다르므로, 복잡한 워크플로는 대상 모델로 실제 검증을 권장합니다.

## 2. 모델 전환

Codex는 두 가지 전환 축이 있습니다.

- **provider 전환 (프로파일)**: `~/.codex/config.toml`(기본)과 `~/.codex/<이름>.config.toml`(프로파일)을 두고, 실행 시 `--profile <이름>`으로 겹쳐 적용합니다. provider·base_url·인증이 다른 모델은 프로파일로 나눕니다.

  ```bash
  codex                       # 기본 config.toml → azure_foundry / gpt-4.1
  codex --profile litellm     # litellm.config.toml → LiteLLM / kimi-k2
  ```

- **같은 provider 내 모델 전환**: 세션 중 `/model` 슬래시 명령으로 바꾸거나, 실행 시 `--model <배포이름>`으로 지정합니다.

  ```bash
  codex --model gpt-4.1
  codex --config model='"gpt-4.1"'    # 임의 키 1회 override (값은 TOML)
  ```

> 프로파일 파일은 기본 `config.toml` 위에 겹치는 레이어이므로, 달라지는 값만 적으면 됩니다. provider 정의를 담은 키(`model_provider`, `model_providers`)는 사용자 레벨에만 둘 수 있습니다.

> Azure OpenAI 계열(gpt-4.1·gpt-5-mini)은 sub-agent까지 그대로 동작하고, 비-OpenAI 모델은 프로파일에 `[features] multi_agent = false`가 필요합니다(위 B-2·1-2 매트릭스 참고).

## 3. 요건

- 커스텀 모델은 **tool calling(함수 호출) + 스트리밍**을 지원해야 합니다. tool calling을 지원하지 않는 모델은 에이전트 모델로 쓸 수 없습니다.
- sub-agent(병렬 하위 에이전트)까지 쓰려면 `namespace` 툴을 수용하는 **Azure OpenAI Responses 계열**(gpt-4.1, gpt-5-mini)이 필요합니다.
- 컨텍스트 윈도우 **128k 이상 권장**.
- Codex는 Responses API 와이어 포맷만 사용합니다. Chat Completions만 노출하는 모델은 Part B처럼 변환 프록시가 필요합니다.
- `model_reasoning_effort`·`model_verbosity` 등 일부 옵션은 Responses API 지원 모델에서만 적용됩니다.

## Part C. 운영 전환 — APIM 게이트웨이를 거쳐 연결

운영 환경에서는 엔드포인트를 **Foundry 직결 대신 [04. 전체 API 호출 거버닝 아키텍처](04-api-governance-architecture.md)의 APIM 엔드포인트**로 지정하세요.

→ **앱의 API 호출과 개발자의 Codex 사용량까지** 같은 토큰 한도·메트릭·로깅에 포함되어 전사 거버넌스가 일관됩니다.

- **Part A (Azure 직결)**: `[model_providers.azure_foundry]`의 `base_url`을 APIM 게이트웨이의 Azure OpenAI 호환 경로로 변경합니다. APIM 구독 키가 필요하면 `http_headers`(정적) 또는 `env_http_headers`(환경 변수)로 `api-key` 또는 `Ocp-Apim-Subscription-Key`를 추가합니다.

  ```toml
  [model_providers.azure_foundry]
  name = "Foundry via APIM"
  base_url = "https://<APIM이름>.azure-api.net/<path>/openai/v1"
  wire_api = "responses"
  env_http_headers = { "api-key" = "APIM_SUBSCRIPTION_KEY" }
  ```

- **Part B (LiteLLM 경유)**: LiteLLM `config.yaml`의 `api_base`를 APIM 게이트웨이 URL로 변경하고, 필요 시 `litellm_params`에 `extra_headers`로 구독 키를 추가합니다. Codex의 Responses↔Chat 변환은 계속 LiteLLM이 담당하고, APIM은 그 앞단에서 인증·토큰 제한·로깅을 맡는 2계층 구성이 가장 견고합니다.

## 다음 단계

직접 API 호출과 Codex 호출이 모두 검증되면, 이 호출들을 한 진입점으로 모아 통제하는 **[04. 전체 API 호출 거버닝 아키텍처](04-api-governance-architecture.md)** 로 진행하세요.

## 참고 문서

- [Codex CLI – Overview](https://developers.openai.com/codex/cli)
- [Codex – Advanced configuration (custom model providers, profiles)](https://developers.openai.com/codex/config-advanced)
- [Codex – Configuration reference (`config.toml`)](https://developers.openai.com/codex/config-reference)
- [Azure OpenAI in Microsoft Foundry Models v1 API](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/how-to/use-chat-completions)
- [Azure OpenAI Responses API](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses)
- [키리스 인증 (Microsoft Entra ID) 구성](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/managed-identity)
- [LiteLLM – Azure AI Studio provider](https://docs.litellm.ai/docs/providers/azure_ai)
- [LiteLLM – Azure AD token refresh](https://docs.litellm.ai/docs/providers/azure/)
- [APIM으로 LLM API 인증·권한 부여](https://learn.microsoft.com/en-us/azure/api-management/api-management-authenticate-authorize-ai-apis)
