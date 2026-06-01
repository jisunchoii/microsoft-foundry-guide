# 01. Entra ID + Foundry 셋업 (CLI)

Azure CLI로 Foundry 리소스 생성, 모델 배포, RBAC 권한 부여를 자동화합니다. 리눅스 또는 macOS의 bash/zsh 환경에서 실행하는 흐름을 기준으로 합니다.

## 진행 순서

- 사전 준비물 확인
- 변수 설정 및 Azure 로그인
- Resource Group과 Foundry 리소스 생성
- 모델 배포
- 개발자에게 Entra ID 권한 부여
- 셋업 검증 또는 전체 스크립트 실행


## 사전 준비물

- **Azure CLI**: [설치](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) (버전 2.x 이상)
- **권한**: 리소스 생성에 **Owner/Contributor**, 역할 부여에 **Owner** 또는 **User Access Administrator**
- **모델 접근**: 일부 모델은 지역·구독에 따라 가용성이 다름

## 0단계 — 변수 설정 & 로그인

```bash
# 재사용할 변수 (값을 환경에 맞게 수정)
RG="rg-foundry-dev"
LOCATION="eastus"
RESOURCE="my-foundry-res"        # Foundry(=Cognitive Services 계정) 이름, 전역 고유
DEPLOYMENT="my-gpt4o-prod"       # 배포 이름 (API 호출 시 사용)
MODEL="gpt-4o"
MODEL_VERSION="2024-11-20"
DEVELOPER="developer@contoso.com" # 실제 사용자 UPN으로 변경
SUBSCRIPTION=""                  # 필요하면 구독 ID 또는 이름 입력

# 로그인 & 구독 선택
az account show >/dev/null || az login --use-device-code
if [[ -n "$SUBSCRIPTION" ]]; then
  az account set --subscription "$SUBSCRIPTION"
fi
```


## 1단계 — 리소스 그룹 & Foundry 리소스 생성

```bash
# 리소스 그룹
az group create --name "$RG" --location "$LOCATION"

# Foundry(=AIServices) 계정 생성 — custom subdomain은 Entra ID 인증에 필수
az cognitiveservices account create \
  --name "$RESOURCE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --kind AIServices \
  --sku S0 \
  --custom-domain "$RESOURCE" \
  --yes
```

엔드포인트 확인:

```bash
az cognitiveservices account show \
  --name "$RESOURCE" --resource-group "$RG" \
  --query "properties.endpoint" -o tsv
# 예: https://my-foundry-res.openai.azure.com/  (호출 시 /openai/v1/ 경로 사용)
```



## 2단계 — 모델 배포

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

> `--sku-name` 값: `Standard`, `GlobalStandard`, `GlobalBatch`, `ProvisionedManaged`, `GlobalProvisionedManaged` 등 ([배포 유형 선택](#참조--배포-유형-선택) 참고).
> `--sku-capacity` 는 TPM 단위 용량(Standard 계열) 또는 PTU 수(Provisioned).

배포 확인:

```bash
az cognitiveservices account deployment list \
  --name "$RESOURCE" --resource-group "$RG" \
  --query "[].{name:name, model:properties.model.name, sku:sku.name}" -o table
```

> API 호출 시에는 **모델 이름이 아니라 배포 이름(`$DEPLOYMENT`)** 을 사용합니다.



## 참조 — 배포 유형 선택

| 배포 유형 | SKU 코드 | 데이터 처리 위치 | 과금 | 적합한 용도 |
|-----------|----------|------------------|------|-------------|
| **Global Standard** | `GlobalStandard` | 모든 Azure 지역 | 토큰당 종량제 | **처음 시작 / 일반 워크로드** |
| Global Provisioned (PTU) | `GlobalProvisionedManaged` | 모든 Azure 지역 | PTU 예약 | 예측 가능한 고부하, 낮은 지연 |
| **Global Batch** | `GlobalBatch` | 모든 Azure 지역 | **50% 할인** (24h 목표) | 실시간 아닌 대량 비동기 |
| Data Zone Standard | `DataZoneStandard` | 데이터 존(US/EU) 내 | 종량제 | EU/US 데이터 존 규정 준수 |
| Standard | `Standard` | 단일 지역 | 종량제 | 지역 규정 준수, 낮은 볼륨 |
| Regional Provisioned | `ProvisionedManaged` | 단일 지역 | PTU 예약 | 지역 규정 + 처리량 |
| Developer | `DeveloperTier` | 모든 지역 | 종량제 | 파인튜닝 모델 **평가 전용** |

**권장**: `GlobalStandard`로 시작 → 트래픽↑·지연 중요해지면 `PTU` → 대량 비동기는 `GlobalBatch`. **개발=Standard / 프로덕션=PTU**, 과용 방지로 **TPM 한도** 설정.

> 조직 차원에서 특정 유형만 허용하려면 **Azure Policy**로 `Microsoft.CognitiveServices/accounts/deployments/sku.name` 을 제한할 수 있습니다.

## 3단계 — 개발자에게 Entra ID 권한 부여

API key 대신 RBAC 역할을 부여합니다. **GUID 사용을 권장**합니다.

```bash
# Foundry User (최소 권한) — 모델·에이전트 호출
az role assignment create \
  --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
  --assignee "$DEVELOPER" \
  --scope "$(az cognitiveservices account show --name "$RESOURCE" --resource-group "$RG" --query id -o tsv)"
```

### 역할 GUID 참조

| 역할 | 권한 | 역할 GUID |
|------|------|-----------|
| **Foundry User** (구 Azure AI User) | 모델·에이전트 **호출** (최소 권한) | `53ca6127-db72-4b80-b1b0-d745d6d5456d` |
| **Foundry Project Manager** | 프로젝트 관리 + User 역할 부여 | `eadc314b-1a2d-4efa-be10-5d325db5065e` |
| **Foundry Account Owner** | 계정/프로젝트 생성, 모델 관리 | `e47c6f54-e4a2-4754-9501-8e0985b135e1` |
| **Foundry Owner** | 전체 관리 + 빌드 (최고 권한) | `c883944f-8b7b-4483-af10-35834be79c4a` |

부여 확인:

```bash
az role assignment list \
  --assignee "$DEVELOPER" \
  --scope "$(az cognitiveservices account show --name "$RESOURCE" --resource-group "$RG" --query id -o tsv)" \
  --query "[].roleDefinitionName" -o table
```


## 4단계 — 셋업 검증

생성된 엔드포인트, 배포, 역할 부여 상태를 한 번에 확인합니다.

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


## 전체 스크립트 (한 번에 실행)

```bash
#!/usr/bin/env bash
set -euo pipefail

RG="rg-foundry-dev-test"
LOCATION="eastus"
RESOURCE="my-foundry-res-$(date +%s)"   # Foundry 리소스 이름은 전역 고유해야 함
DEPLOYMENT="my-gpt4o-prod"
MODEL="gpt-4o"
MODEL_VERSION="2024-11-20"
DEVELOPER="developer@contoso.com"       # 실제 사용자 UPN으로 변경
SUBSCRIPTION=""                        # 필요하면 구독 ID 또는 이름 입력

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

테스트가 끝난 리소스를 정리하려면 다음 명령을 실행합니다.

```bash
az group delete --name rg-foundry-dev-test --yes --no-wait
```


## 다음 단계

[02. API 호출](02-api-calls.md) — 키 또는 Entra ID로 모델을 호출합니다.

> GUI 화면으로 확인하려면 → [01. 셋업 (포털)](01-setup-portal.md)

## 참고 문서

- [az cognitiveservices account](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account)
- [az cognitiveservices account deployment](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment)
- [Understanding deployment types in Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types)
- [RBAC for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry)
- [Plan a Foundry rollout](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/planning)
- [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
