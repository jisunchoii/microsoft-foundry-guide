# 03b1. Claude Code에서 Databricks 호스팅 Claude 호출하기

Claude Code(Anthropic 공식 CLI)에서 Azure Databricks에 서빙된 Claude 모델(예: `databricks-claude-opus-4-8`)을 호출하는 방법을 정리합니다.

> [03b. Claude Code + Foundry(LiteLLM)](03b-claude-code-foundry-integration.md) 문서와 달리, 이 구성에는 **변환 프록시(LiteLLM)가 필요 없습니다.** Azure Databricks가 **Anthropic 호환 서빙 엔드포인트**(`/serving-endpoints/anthropic`)를 직접 노출하므로, Claude Code의 `ANTHROPIC_BASE_URL`만 그쪽으로 바꾸면 그대로 연결됩니다.

## 이 문서에서 다루는 내용

- Databricks 포털의 "Integrate external agents"에서 Claude Code 설정 가져오기
- `ANTHROPIC_BASE_URL`을 Databricks 서빙 엔드포인트로 직결
- 코딩 에이전트 모드 헤더(`x-databricks-use-coding-agent-mode`) 적용
- 개인용 액세스 토큰(PAT)으로 인증
- `/model`로 opus·sonnet·haiku 슬롯에 매핑된 Databricks Claude 전환

## 0. 사전 준비

- **워크스페이스 URL**: Azure Databricks 워크스페이스의 per-workspace URL을 사용합니다. 예: `https://adb-7405611817568192.12.azuredatabricks.net`
- **서빙 엔드포인트 이름**: Databricks에 배포된 Claude 모델 엔드포인트 이름. 예: `databricks-claude-opus-4-8`. 워크스페이스 좌측 **Serving** 탭의 Endpoints 목록에서 확인합니다.

> 에이전트 모드(파일 편집/툴 실행)로 쓰려면 모델이 **tool calling**을 지원해야 합니다. Databricks가 호스팅하는 Claude 모델은 이를 지원합니다.

## 1. 포털에서 설정 가져오기

Databricks 워크스페이스가 Claude Code 연결 설정을 직접 생성해 줍니다.

1. 좌측 **Serving** 탭으로 이동합니다.
2. 상단의 **Integrate external agents**(외부 에이전트 통합) 카드에서 **Get Started**를 클릭합니다.
![cc-db-o1](../images/cc-db-01.png)

3. **Other Integrations** 탭에서 **Select an integration**을 **Claude Code CLI**로 선택합니다.
4. **Select your models** 에서 Claude Code가 사용할 모델을 지정합니다.
   - **Default Anthropic Model**: 기본 모델. 예: `databricks-claude-opus-4-8`
   - **Default Opus / Sonnet / Haiku Model (Optional)**: `opus`·`sonnet`·`haiku` 별칭에 각각 매핑할 모델(선택). 비워 두면 기본 모델만 사용합니다.
5. **Update settings.json** 에서 **Generate API Key** 를 클릭해 토큰을 발급받고, 표시된 `settings.json` 구성을 복사합니다.
![cc-db-02](../images/cc-db-02.png)


포털이 생성하는 구성은 다음과 같은 형태입니다.

```jsonc
{
  "env": {
    "ANTHROPIC_MODEL": "databricks-claude-opus-4-8",
    "ANTHROPIC_BASE_URL": "https://adb-7405611817568192.12.azuredatabricks.net/serving-endpoints/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your_token_will_appear_here>",
    "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1"
  }
}
```

| 키 | 의미 |
| --- | --- |
| `ANTHROPIC_MODEL` | 기본으로 호출할 Databricks 서빙 엔드포인트 이름 |
| `ANTHROPIC_BASE_URL` | 워크스페이스 URL 뒤에 `/serving-endpoints/anthropic`를 붙인 Anthropic 호환 엔드포인트 |
| `ANTHROPIC_AUTH_TOKEN` | 인증 토큰 (아래 [3. 인증](#3-인증) 참고) |
| `ANTHROPIC_CUSTOM_HEADERS` | 코딩 에이전트 모드 활성화 헤더. Claude Code용 동작을 켭니다 |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Claude 전용 실험 베타 기능 비활성화 (호환성 확보) |

## 2. Claude Code 연결

기존 설정과 섞이지 않도록 **별도 settings 파일**을 만들어 `--settings`로 띄우는 방식을 권장합니다.

### 2-1. `claude-databricks-settings.json` 예시

`/model` 선택기에 모델을 깔끔하게 표시하기 위해 `opus`/`sonnet`/`haiku` 별칭 슬롯을 Databricks 엔드포인트에 매핑할 수 있습니다(선택).

```jsonc
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://adb-7405611817568192.12.azuredatabricks.net/serving-endpoints/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<발급받은 토큰>",
    "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",

    "ANTHROPIC_MODEL": "databricks-claude-opus-4-8",

    "ANTHROPIC_DEFAULT_OPUS_MODEL": "databricks-claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "databricks-claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "databricks-claude-haiku-4-5"
  },
  "model": "opus"
}
```

> `ANTHROPIC_DEFAULT_*` 값에는 워크스페이스에 실제 존재하는 서빙 엔드포인트 이름을 넣습니다. 매핑이 필요 없으면 `ANTHROPIC_MODEL` 하나만 두어도 됩니다.

### 2-2. 실행

```bash
claude --settings claude-databricks-settings.json
```

## 3. 인증

이 문서는 포털이 안내하는 **개인용 액세스 토큰(PAT)** 방식을 사용합니다. PAT는 **키 기반(워크스페이스 토큰) 인증**입니다.

- 포털의 **Generate API Key** 가 PAT를 발급하며, 발급된 값을 `ANTHROPIC_AUTH_TOKEN`에 넣습니다.
- 직접 발급하려면 워크스페이스에서 **Settings → Developer → Access tokens → Manage → Generate new token** 을 사용합니다.
- 토큰에는 **수명(lifetime)** 이 있습니다. 만료되면 새로 발급해 settings 파일의 값을 교체하세요. 90일간 사용되지 않은 토큰은 자동 폐기됩니다.
- 토큰은 비밀 값입니다. 소스·git에 커밋하지 말고 안전하게 보관하세요.

> Databricks는 사용자 계정 인증에 PAT보다 **Databricks OAuth**를 권장합니다. 조직 정책상 키 기반 토큰 사용이 제한된다면 관리자와 Databricks OAuth/서비스 주체 기반 토큰 발급 방식을 협의하세요.

## 4. 모델 전환

- 세션 중 `/model` 슬래시 명령으로 선택기를 열어 전환합니다. 위 설정이면 `opus`(Opus)·`sonnet`(Sonnet)·`haiku`(Haiku) 슬롯이 각 Databricks 엔드포인트로 연결됩니다.
- 별칭으로 직접 지정할 수도 있습니다: `/model opus`, `/model sonnet`, `/model haiku`.
- 실행 시 `claude --settings ... --model sonnet` 처럼 지정할 수도 있습니다.

![cc-db-o3](../images/cc-db-03.png)

## 5. 요건 및 주의

- 대상 **서빙 엔드포인트가 가동(Ready) 상태**여야 합니다. 스케일 투 제로로 잠든 엔드포인트는 첫 호출에서 콜드 스타트 지연이 있을 수 있습니다.
- `x-databricks-use-coding-agent-mode: true` 헤더는 Claude Code용 동작을 활성화합니다. `ANTHROPIC_CUSTOM_HEADERS`에서 빠지면 정상 동작하지 않을 수 있습니다.
- 토큰 만료 시 401이 발생합니다. 토큰을 재발급해 교체하세요.
- 모델·엔드포인트 가용성과 한도는 워크스페이스 리전·구성에 따라 다릅니다. 자세한 내용은 아래 참고 문서를 확인하세요.

## 참고 문서

- [Claude Code – Model configuration](https://code.claude.com/docs/en/model-config)
- [Claude Code – LLM gateway configuration](https://code.claude.com/docs/en/llm-gateway)
- [Databricks Foundation Model APIs (Azure)](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/foundation-model-apis/)
- [Query foundation models on Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/model-serving/score-foundation-models)
- [Azure Databricks 개인용 액세스 토큰(PAT) 인증](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/pat)
