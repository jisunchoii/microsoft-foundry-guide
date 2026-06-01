# 02. API 호출

Foundry에 배포한 모델을 API Key와 Microsoft Entra ID 방식으로 호출합니다. 예제는 신규 개발 권장 방식인 **Responses API** 기준입니다.

## 이 문서에서 다루는 내용

- 공통 Python 패키지 설치와 환경 변수 설정
- API Key 방식 호출
- Microsoft Entra ID 기반 키리스 호출
- `DefaultAzureCredential` 인증 흐름

> **지원 확인**: Responses API는 `v1` API 경로가 필요하며, 지역과 모델별 지원 여부가 다릅니다. 배포 전 [Azure OpenAI Responses API 공식 문서](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses)에서 지원 지역·모델을 확인하세요.

## 1. 인증 방식

- **API Key**: 가장 간단해서 빠른 테스트/PoC에 적합합니다. 다만 키 하나가 전체 권한을 가지므로 유출 시 위험하고, 역할 기반 제한을 적용할 수 없습니다.
- **Microsoft Entra ID(키리스)**: RBAC 세분화, 키 저장 불필요, Managed Identity 사용이 가능하므로 운영 환경에 권장합니다. 초기 설정은 한 단계 더 필요합니다.

> Microsoft 공식 권고: *"키 기반 인증은 키가 전체 접근 권한을 부여하므로 역할 제한이 없습니다. 보안과 세분화된 접근 제어를 위해 Entra ID 인증을 권장합니다."*

![endpoints](../images/02-keys-endpoint.png)

## 2. 설치

```bash
pip install openai azure-identity
```

공통 환경 변수 설정 (Bash):

```bash
export AZURE_OPENAI_ENDPOINT="https://<리소스이름>.openai.azure.com/openai/v1/"
export AZURE_OPENAI_DEPLOYMENT="my-gpt4o-prod"  # 배포 이름 (모델 이름 아님)
```

## 3. API Key 방식

환경 변수 설정 (Bash):

```bash
export AZURE_OPENAI_API_KEY="<your-api-key>"
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

resp = client.responses.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    input="안녕하세요! Azure Foundry를 한 문장으로 설명해 주세요.",
)
print(resp.output_text)
```

> 키를 코드/깃에 하드코딩하지 마세요. 환경 변수나 [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)를 사용하세요.

## 4. Entra ID(키리스) 방식 — 운영 권장

개발자는 사전에 `az login`만 하면, `DefaultAzureCredential`이 자동으로 토큰을 가져옵니다. 

Bash:

```bash
az login

export AZURE_OPENAI_ENDPOINT="https://<리소스이름>.openai.azure.com/openai/v1/"
export AZURE_OPENAI_DEPLOYMENT="my-gpt4o-prod"
```

```python
import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",     # Foundry 토큰 스코프
)

client = OpenAI(
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=token_provider,               # 토큰 공급자를 전달
)

resp = client.responses.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    input="안녕하세요! Azure Foundry를 한 문장으로 설명해 주세요.",
)
print(resp.output_text)
```

### `DefaultAzureCredential` 동작방식

아래의 순서대로 자격 증명을 시도합니다.

1. 환경 변수 (서비스 주체)
2. **관리 ID (Managed Identity)** — Azure VM/Functions/App Service에서 실행 시
3. **Azure CLI 로그인** (`az login`) — 로컬 개발 시
4. VS Code, Azure Developer CLI 등

→ **로컬에서는 `az login`, 운영(Azure)에서는 Managed Identity**가 자동으로 적용되어 코드 수정 없이 동일하게 동작합니다.

## 다음 단계

앱에서 직접 호출이 되면, 같은 Foundry 배포를 개발자 도구에서도 쓸 수 있는지 **[03. Copilot에서 Foundry 모델 호출](03-copilot-foundry-integration.md)** 로 확인하세요.


## 참고 문서

- [Azure OpenAI Responses API](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses)
- [Switch between OpenAI and Azure OpenAI endpoints](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/switching-endpoints)
- [Entra ID / managed identity 인증](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/managed-identity)
- [Quickstart: Build with models and agents](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code)
- [DefaultAzureCredential 개요](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains)
- [Azure Key Vault 개요](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)
