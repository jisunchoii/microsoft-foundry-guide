# OpenCode Entra 인증 구성 가이드

OpenCode가 호출하는 모델을 Azure Entra ID(Azure AD) 토큰으로 인증하는 방법입니다. Azure AI Foundry와 Azure Databricks 모델 서빙을 대상으로 하며, API 키를 디스크에 저장하지 않고 Azure CLI(`az`) 세션의 토큰을 매 요청마다 주입합니다. 토큰은 만료 직전에 자동으로 갱신됩니다.

## 동작 방식

OpenCode는 provider별로 API 키를 받아 `~/.local/share/opencode/auth.json`에 저장하는 방식을 기본으로 합니다. 이 가이드는 키를 저장하는 대신, OpenCode 플러그인이 provider에 설치한 `fetch` 래퍼로 매 요청 직전에 Entra 토큰을 `Authorization: Bearer` 헤더에 넣습니다. 토큰은 `az account get-access-token`으로 발급하므로 비밀 값을 파일에 두지 않으며, 플러그인이 토큰을 메모리에 캐싱하고 만료 5분 전에 재발급하며, 서버가 401을 반환하면 토큰을 강제로 갱신하여 한 번 재시도합니다.

provider별로 토큰의 리소스(audience)가 다릅니다.

| Provider | Azure AD 토큰 리소스 | 용도 |
| :--- | :--- | :--- |
| foundry | `https://cognitiveservices.azure.com` | Azure AI Foundry(Cognitive Services) |
| databricks | `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d` | Azure Databricks 글로벌 애플리케이션 ID |

## 사전 준비

1. Azure CLI가 설치되어 있고 `az login`으로 로그인된 상태여야 합니다. 토큰은 이 세션에서 발급됩니다.
2. 대상 리소스에 대한 RBAC 권한이 필요합니다.
   - Foundry: Azure AI Foundry(AI Services) 리소스에 `Cognitive Services User` 역할
   - Databricks: 워크스페이스 접근 권한과 serving endpoint에 대한 `CAN_USE` 권한
3. 모델 배포가 끝나 있어야 합니다. Foundry는 모델 deployment, Databricks는 serving endpoint가 `READY` 상태여야 합니다.

로그인과 토큰 발급은 다음 명령으로 확인합니다.

```powershell
az account show --query "{user:user.name, sub:name}" -o json
az account get-access-token --resource "https://cognitiveservices.azure.com" --query expiresOn -o tsv
```

## 1단계: OpenCode와 Bun 설치

OpenCode CLI와 플러그인 런타임인 Bun을 설치합니다. OpenCode 플러그인은 Bun으로 설치되므로 Bun이 필요합니다. Windows에서는 winget으로 설치합니다.

```powershell
winget install -e --id SST.opencode --source winget --accept-package-agreements --accept-source-agreements
winget install -e --id Oven-sh.Bun --source winget --accept-package-agreements --accept-source-agreements
```

설치 후 새 셸을 열어 PATH를 갱신하고 버전을 확인합니다.

```powershell
opencode --version
bun --version
```

> Bun을 winget으로 설치하면 실행 파일이 winget 패키지 폴더에 `bun.exe`로 들어가며 사용자 PATH에 등록됩니다. 별도의 `bunx.exe`는 제공되지 않으므로 `bunx` 대신 `bun x`를 사용합니다.

## 2단계: Entra 인증 플러그인 작성

OpenCode의 로컬 플러그인은 `~/.config/opencode/plugins/` 디렉터리(복수형 `plugins`)에 두면 시작 시 자동으로 로드됩니다. 이 디렉터리를 만들고 Entra 토큰을 주입하는 플러그인을 작성합니다.

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\plugins" | Out-Null
```

`~/.config/opencode/plugins/foundry-entra-auth.js` 파일을 다음 내용으로 만듭니다.

```javascript
import { execFile } from "node:child_process"

// opencode provider id -> Azure AD token resource (audience)
const RESOURCE_BY_PROVIDER = {
  foundry: "https://cognitiveservices.azure.com",
  databricks: "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d", // Azure Databricks global app id
}

const cache = new Map() // providerId -> { token, expiresAtMs }
const SKEW_MS = 5 * 60 * 1000 // refresh this long before expiry

// Run `az account get-access-token`, with a small retry for transient failures.
// Throws a clear, actionable error when sign-in is required.
function azToken(resource, attempt = 0) {
  return new Promise((resolve, reject) => {
    execFile(
      "az",
      ["account", "get-access-token", "--resource", resource, "--output", "json"],
      { shell: true, windowsHide: true, maxBuffer: 1024 * 1024 },
      (err, stdout, stderr) => {
        if (err) {
          const msg = `${stderr || err.message || ""}`
          const needsLogin = /AADSTS|az login|not logged in|refresh token|re-?authenticate|expired/i.test(msg)
          if (needsLogin) {
            return reject(
              new Error(
                "Entra sign-in required for opencode model auth. Run `az login` " +
                  "(interactive) or `az login --service-principal ...` / use a Managed " +
                  `Identity for unattended runs. Underlying error: ${msg.trim()}`,
              ),
            )
          }
          // transient failure: retry up to 2 more times with backoff
          if (attempt < 2) {
            setTimeout(() => azToken(resource, attempt + 1).then(resolve, reject), 400 * (attempt + 1))
            return
          }
          return reject(new Error(`az token failed (${resource}): ${msg.trim()}`))
        }
        try {
          const j = JSON.parse(stdout)
          resolve({ token: j.accessToken, expiresAtMs: new Date(j.expiresOn).getTime() })
        } catch (e) {
          reject(new Error(`failed to parse az output: ${e.message}`))
        }
      },
    )
  })
}

async function getToken(providerId, forceRefresh = false) {
  const resource = RESOURCE_BY_PROVIDER[providerId]
  if (!resource) return undefined
  const cached = cache.get(providerId)
  if (!forceRefresh && cached && cached.expiresAtMs - SKEW_MS > Date.now()) return cached.token
  const fresh = await azToken(resource)
  cache.set(providerId, fresh)
  return fresh.token
}

// fetch() wrapper bound to a provider id: injects the bearer token, and on a
// 401/403 forces a token refresh and retries the request once.
function makeAuthedFetch(providerId) {
  const base = globalThis.fetch
  return async (url, init = {}) => {
    const headers = new Headers(init.headers || {})
    headers.set("Authorization", `Bearer ${await getToken(providerId)}`)
    let res = await base(url, { ...init, headers })
    if (res.status === 401 || res.status === 403) {
      const retryHeaders = new Headers(init.headers || {})
      retryHeaders.set("Authorization", `Bearer ${await getToken(providerId, true)}`)
      res = await base(url, { ...init, headers: retryHeaders })
    }
    return res
  }
}

export const FoundryEntraAuth = async ({ client }) => {
  return {
    // Install a token-injecting fetch on each managed provider at config load.
    config: async (config) => {
      const providers = config?.provider
      if (!providers) return
      for (const providerId of Object.keys(RESOURCE_BY_PROVIDER)) {
        const p = providers[providerId]
        if (!p) continue
        p.options = p.options || {}
        p.options.fetch = makeAuthedFetch(providerId)
      }
    },

    // Azure gpt-5.x reasoning models reject `max_tokens` (require
    // `max_completion_tokens`) and only allow temperature=1.
    "chat.params": async (input, output) => {
      if (input?.provider?.id !== "foundry") return
      output.maxOutputTokens = undefined
      output.temperature = 1
      output.topP = 1
    },
  }
}
```

플러그인의 동작은 두 가지입니다. 먼저 `config` 훅이 시작 시 각 provider에 토큰 주입 `fetch`를 설치하여, 매 요청마다 Entra 토큰을 `Authorization: Bearer` 헤더에 넣습니다. 토큰은 메모리에 캐싱하고 만료 5분 전에 자동으로 재발급하며, 서버가 401 또는 403을 반환하면 토큰을 강제로 갱신하여 요청을 한 번 재시도합니다. `az` 토큰 발급이 실패하면 재인증이 필요한 경우와 일시적 오류를 구분하여, 전자에는 `az login` 또는 서비스 주체/관리 ID 사용을 안내하는 메시지를 던지고 후자는 짧은 백오프로 재시도합니다. 다음으로 `chat.params` 훅은 Foundry의 GPT-5 계열 추론 모델이 `max_tokens`를 거부하고 `max_completion_tokens`만 허용하며 temperature를 1로 고정해야 하는 제약을 처리합니다. Databricks만 사용하고 GPT-5 계열을 쓰지 않는다면 `chat.params` 훅은 생략합니다.

> 토큰 주입을 `fetch` 래퍼로 구현하는 이유는 응답 상태 코드를 확인하여 401에서 재시도하기 위함입니다. provider의 식별자는 런타임에서 `input.provider.id` 경로로 노출되며, `chat.params` 훅에서 이 값을 사용합니다.

## 3단계: provider 구성

`~/.config/opencode/opencode.json`에 provider를 등록합니다. 두 provider 모두 OpenAI 호환 API를 사용하므로 `@ai-sdk/openai-compatible` 패키지로 연결합니다. `apiKey` 항목에는 더미 값을 넣습니다. SDK 초기화를 위해 형식상 필요하나, 실제 인증 헤더는 2단계의 플러그인이 덮어쓰므로 키 값 자체는 사용되지 않습니다.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "databricks/databricks-claude-opus-4-8",
  "provider": {
    "foundry": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Azure AI Foundry (Entra)",
      "options": {
        "baseURL": "https://<foundry-resource>.cognitiveservices.azure.com/openai/v1",
        "apiKey": "entra-via-plugin"
      },
      "models": {
        "gpt-5.4": { "name": "GPT-5.4 (Foundry)" }
      }
    },
    "databricks": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Azure Databricks (Entra)",
      "options": {
        "baseURL": "https://<workspace>.azuredatabricks.net/serving-endpoints",
        "apiKey": "entra-via-plugin"
      },
      "models": {
        "databricks-claude-opus-4-8": { "name": "Claude Opus 4.8 (Databricks)" },
        "databricks-claude-sonnet-4-6": { "name": "Claude Sonnet 4.6 (Databricks)" },
        "databricks-claude-haiku-4-5": { "name": "Claude Haiku 4.5 (Databricks)" }
      }
    }
  }
}
```

Foundry 하나만 쓰거나 Databricks 하나만 쓴다면 해당 provider 블록만 남기면 됩니다. baseURL의 경로 규칙은 provider마다 다릅니다.

- Foundry: 리소스 endpoint 뒤에 `/openai/v1`을 붙입니다. 모델 id는 deployment 이름입니다.
- Databricks: 워크스페이스 host 뒤에 `/serving-endpoints`를 붙입니다. 모델 id는 serving endpoint 이름이며, 요청 본문의 `model` 필드로 라우팅됩니다.

워크스페이스 host와 serving endpoint 목록은 다음 명령으로 확인합니다.

```powershell
# Databricks 워크스페이스 host
az resource show -g <rg> -n <workspace> --resource-type "Microsoft.Databricks/workspaces" --query "properties.workspaceUrl" -o tsv

# serving endpoint 목록 (Entra 토큰 사용)
$dbxRes = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
$token = az account get-access-token --resource $dbxRes --query accessToken -o tsv
Invoke-RestMethod -Uri "https://<workspace>.azuredatabricks.net/api/2.0/serving-endpoints" -Headers @{ Authorization = "Bearer $token" } | Select-Object -ExpandProperty endpoints | Select-Object name
```

Foundry deployment 목록은 다음 명령으로 확인합니다.

```powershell
az cognitiveservices account deployment list --name <foundry-resource> --resource-group <rg> --query "[].{Name:name, Model:properties.model.name}" -o table
```

### Foundry open-weight 모델

Foundry는 OpenAI 모델 외에 Llama, Phi, Mistral, DeepSeek 같은 open-weight 모델도 서빙합니다. 인증 방식은 동일하나(같은 `https://cognitiveservices.azure.com` 리소스 토큰), 엔드포인트 경로가 다릅니다. OpenAI 모델은 `/openai/v1` 경로를 사용하는 반면, open-weight 모델은 Azure AI Model Inference 엔드포인트로 서빙되며 호스트와 경로가 다음과 같습니다.

```
https://<resource>.services.ai.azure.com/models
```

이 경우 provider 블록을 별도로 두고 baseURL을 위 형식으로 지정합니다. 모델 id는 배포 이름입니다.

```jsonc
"foundry-models": {
  "npm": "@ai-sdk/openai-compatible",
  "name": "Azure AI Foundry Models (Entra)",
  "options": {
    "baseURL": "https://<resource>.services.ai.azure.com/models",
    "apiKey": "entra-via-plugin"
  },
  "models": {
    "Llama-3.3-70B-Instruct": { "name": "Llama 3.3 70B" }
  }
}
```

이 provider도 Entra 토큰을 사용하므로 플러그인의 `RESOURCE_BY_PROVIDER`에 같은 리소스로 항목을 추가합니다.

```javascript
const RESOURCE_BY_PROVIDER = {
  foundry: "https://cognitiveservices.azure.com",
  "foundry-models": "https://cognitiveservices.azure.com",
  databricks: "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d",
}
```

open-weight 모델은 OpenAI 호환 surface를 제공하더라도 모델별로 지원 파라미터가 다릅니다. 일부 모델은 `stream_options`, `temperature`, `max_tokens` 같은 필드를 거부하므로, 거부되는 필드가 있으면 `chat.params` 훅에서 해당 provider나 모델에 맞게 조정합니다.

## 4단계: 연결 검증

각 provider로 실제 추론이 되는지 확인합니다.

```powershell
$env:OPENCODE_CONFIG = "$env:USERPROFILE\.config\opencode\opencode.json"

# Databricks Claude
opencode run --model databricks/databricks-claude-opus-4-8 "Reply with exactly: DBX_OK"

# Foundry GPT
opencode run --model foundry/gpt-5.4 "Reply with exactly: FOUNDRY_OK"
```

각각 `DBX_OK`, `FOUNDRY_OK`로 응답하면 Entra 인증과 provider 연결이 정상입니다.

## 문제 해결

- `Unauthorized` 또는 `Credential was not sent`: 플러그인이 로드되지 않았거나 RBAC 권한이 누락된 경우입니다. `opencode run --print-logs --log-level INFO ...`로 플러그인 로드 여부와 provider id를 확인합니다. provider id가 `undefined`로 찍히면 `input.provider.id` 경로를 점검합니다.
- `'max_tokens' is not supported`: Foundry의 GPT-5 추론 모델에서 발생합니다. 2단계의 `chat.params` 훅이 적용되었는지 확인합니다.
- `unknown field "stream_options"`: 일부 비-Claude Databricks serving endpoint(예: Qwen, Llama 계열)는 OpenAI 호환 클라이언트가 보내는 `stream_options` 필드를 거부합니다. Claude 계열 endpoint는 정상 동작합니다.

## 토큰 만료와 장기 운영

Entra 인증에는 두 종류의 만료가 있으며, 동작과 대처가 다릅니다.

먼저 AAD 액세스 토큰의 만료입니다. 액세스 토큰의 수명은 약 60~90분입니다. 플러그인이 만료 5분 전에 `az account get-access-token`을 다시 호출하여 새 토큰으로 교체하며, `az`는 내부적으로 refresh token으로 무인 갱신(silent refresh)을 수행합니다. 따라서 세션을 몇 시간 동안 연속으로 돌려도 사용자 개입 없이 인증이 유지됩니다. 추가로, 토큰이 예상보다 일찍 무효화되어 서버가 401 또는 403을 반환하면 플러그인이 토큰을 강제로 갱신하여 요청을 한 번 재시도하므로, 시계 오차나 일시적 폐기 상황도 자동으로 복구됩니다.

다음으로 `az` 로그인 세션 자체의 만료입니다. refresh token이 만료되거나(기본 수명은 길지만 Conditional Access 정책에 따라 수 시간으로 짧아질 수 있습니다), MFA 재요구, 토큰 폐기 등이 발생하면 `az account get-access-token`이 실패합니다. 이때 플러그인은 재인증이 필요하다는 명확한 메시지를 던지고 해당 요청은 실패합니다. 대화형 환경에서는 `az login`을 다시 수행하면 즉시 복구됩니다.

고객이 장시간 무인으로 운영하는 경우 대화형 `az login`은 적합하지 않으므로, 다음 두 가지 중 하나를 사용합니다.

1. 서비스 주체(Service Principal)와 인증서: `az login --service-principal -u <appId> --tenant <tenantId> -p <cert.pem>`으로 로그인하면 비대화형으로 토큰을 갱신합니다. 대상 리소스에 서비스 주체로 `Cognitive Services User` 역할을 부여합니다.
2. 관리 ID(Managed Identity): Azure VM이나 컨테이너에서 실행하면 `az`가 인스턴스 메타데이터 서비스로 토큰을 받아 완전 무인으로 동작합니다. 별도의 자격 증명 관리가 없어 가장 단순합니다.

## 보안 참고

이 구성은 API 키를 디스크에 저장하지 않으며 인증을 Entra 토큰으로 일원화합니다. `opencode.json`의 `apiKey` 더미 값은 인증에 사용되지 않습니다. 키 기반 인증을 완전히 차단하려면 리소스에서 로컬 인증(`disableLocalAuth`)을 비활성화하고 Entra 인증만 허용합니다.

## 참고 자료

- [OpenCode Providers](https://opencode.ai/docs/providers/)
- [OpenCode Plugins](https://opencode.ai/docs/plugins/)
- [Azure AI Foundry 문서](https://learn.microsoft.com/azure/ai-foundry/)
- [Azure Databricks Foundation Model API](https://learn.microsoft.com/azure/databricks/machine-learning/foundation-model-apis/)
