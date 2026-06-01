# 01. Entra ID + Foundry 셋업 (포털)

Azure Portal과 Foundry 포털을 사용해 Resource Group, Foundry 리소스, 모델 배포, RBAC 권한을 순서대로 구성합니다.

## 진행 순서

- 사전 준비물 확인
- Resource Group 생성
- Foundry 리소스 및 기본 프로젝트 생성
- 모델 배포
- 배포 유형 선택
- 개발자에게 Entra ID 권한 부여

## 사전 준비물

- **Azure 구독**: [무료 계정](https://azure.microsoft.com/free/) 또는 회사 구독
- **권한**: 리소스를 만들려면 구독/리소스 그룹에 **Owner** 또는 **Contributor** 필요
- **모델 접근**: 일부 모델(예: GPT-4 계열)은 지역·구독에 따라 가용성이 다름

## 1단계 — Resource Group 생성

Resource Group은 Azure 리소스를 논리적으로 묶는 컨테이너입니다. 고객 환경에서는 비용 추적, 권한, 정책, 삭제 범위를 명확히 하기 위해 **리소스 그룹을 먼저 만드는 흐름**을 권장합니다.

1. [Azure Portal (`https://portal.azure.com`)](https://portal.azure.com)에 로그인합니다.
2. 상단 검색창에서 **Resource groups**를 검색합니다.
3. **+ Create**를 클릭합니다.

![Resource Group ](../images/00-rg.png)

4. 다음 값을 입력합니다.

   | 항목 | 예시 |
   |---|---|
   | Subscription | 고객 구독 |
   | Resource group | `rg-foundry-dev` |
   | Region | `eastus2` 또는 모델 가용 지역 |

5. **Review + create → Create**를 클릭합니다.

![Resource Group 생성 화면](../images/01-resource-group-create.png)


## 2단계 — Foundry 리소스 및 기본 프로젝트 생성

이 단계에서는 방금 만든 Resource Group 안에 **Foundry 리소스**를 만들고, 기본 프로젝트를 함께 생성합니다.

1. Azure Portal 또는 Foundry 포털에서 **Microsoft Foundry**를 검색합니다.
2. **Create a Foundry Resource** 또는 **Create**를 클릭합니다.

![Foundry Resource 생성 화면](../images/02-fr.png)

3. 다음 값을 입력합니다.

   | 항목 | 예시 |
   |---|---|
   | Resource group | `rg-foundry-dev` |
   | Name | `foundry-<고유이름>` |
   | Location | Resource Group과 같은 지역 또는 모델 가용 지역 |
   | Default project name | `proj-default` |

4. **Review + create → Create**를 클릭합니다.

![Foundry Resource 생성 화면](../images/01-foundry-resource-overview.png)

생성이 끝나면 Foundry 리소스 개요에서 **Go to Foundry portal**을 클릭해 프로젝트로 이동합니다.

## 3단계 — 모델 배포

1. 프로젝트 우측 상단 메뉴 → **Discover**  → **Models**.

![모델 배포 설정 화면](../images/01-models.png)

2. 모델 카탈로그에서 모델을 선택합니다 (예: `gpt-4o`).
3. 다음을 설정합니다:
   - **배포 이름(Deployment name)**: API 호출 시 사용할 이름 (예: `my-gpt4o-prod`)
   - **배포 유형(Deployment type)**: [참조 - 배포유형](#4단계--배포-유형-선택) 표 참고
   - (선택) **콘텐츠 필터**, **TPM(분당 토큰) 한도**
4. **Create deployment**.

![모델 배포 설정 화면](../images/01-deploy-model.png)

> API 호출 시에는 **모델 이름이 아니라 배포 이름**을 사용합니다. 배포 이름을 꼭 기록하세요.


## 참조 — 배포 유형 선택

Foundry 배포는 크게 **종량제(Standard)** 와 **예약 용량(Provisioned/PTU)** 으로 나뉘며, 각각 global / data zone / regional 변형이 있습니다.

| 배포 유형 | SKU 코드 | 데이터 처리 위치 | 과금 | 적합한 용도 |
|-----------|----------|------------------|------|-------------|
| **Global Standard** | `GlobalStandard` | 모든 Azure 지역 | 토큰당 종량제 | **처음 시작 / 일반 워크로드 (가장 추천, 쿼터 가장 큼)** |
| Global Provisioned (PTU) | `GlobalProvisionedManaged` | 모든 Azure 지역 | PTU 예약 | 예측 가능한 고부하, 낮고 일정한 지연 |
| **Global Batch** | `GlobalBatch` | 모든 Azure 지역 | **50% 할인** (24h 목표) | 실시간이 아닌 대량 비동기 작업 |
| Data Zone Standard | `DataZoneStandard` | 데이터 존(US/EU) 내 | 종량제 | EU/US 데이터 존 규정 준수 |
| Data Zone Provisioned | `DataZoneProvisionedManaged` | 데이터 존 내 | PTU 예약 | 데이터 존 + 일정 처리량 |
| Standard | `Standard` | 단일 지역 | 종량제 | 지역 규정 준수, 낮은 볼륨 |
| Regional Provisioned | `ProvisionedManaged` | 단일 지역 | PTU 예약 | 지역 규정 + 처리량 |
| Developer | `DeveloperTier` | 모든 지역 | 종량제 | 파인튜닝 모델 **평가 전용** (SLA 없음, 24h 수명) |

**처음 시작하는 고객 권장**: `GlobalStandard` 로 시작 → 트래픽↑·지연 중요해지면 `PTU` → 대량 비동기는 `GlobalBatch`로 분리.

**데이터 거주(Data residency)**: 저장 데이터는 항상 선택 지역에 머물고, **추론 데이터** 경로만 유형별로 다릅니다 (Global=모든 지역 / Data Zone=US 또는 EU 존 / Standard·Regional=배포 지역).

> 조직 차원에서 특정 배포 유형만 허용하려면 **Azure Policy**로 `Microsoft.CognitiveServices/accounts/deployments/sku.name` 을 제한할 수 있습니다.


## 5단계 — 개발자에게 Entra ID 권한 부여

API Key 대신 Entra ID 역할(RBAC)을 부여합니다.

1. Azure 포털에서 **Foundry 리소스**(또는 프로젝트) → **Access control (IAM)** 으로 이동합니다.

![IAM 역할 할당 화면](../images/01-iam.png)

2. **+ Add → Add role assignment** 클릭.
3. 역할에서 **Foundry User**(최소 권한)를 선택 → **Next**.

![IAM 역할 할당 화면](../images/02-user.png)

4. **+ Select members** 에서 개발자 계정/그룹 선택 → **Review + assign**.

![IAM 역할 할당 화면](../images/03-assign.png)

### Microsoft Foundry 역할

| 역할 | 권한 | 대상 |
|------|------|------|
| **Foundry User** (구 Azure AI User) | 프로젝트에서 모델·에이전트 **호출**(최소 권한) | 개발자 |
| **Foundry Project Manager** | 프로젝트 관리 + User 역할 부여 + 에이전트 게시 | 팀 리드 |
| **Foundry Account Owner** | 계정/프로젝트 생성, 모델 관리, 역할 부여 | 매니저 |
| **Foundry Owner** | 전체 관리 + 빌드 (최고 권한) | — |

## 다음 단계

[02. API 호출](02-api-calls.md) — 키 또는 Entra ID로 모델을 호출합니다.

> 같은 셋업을 스크립트로 자동화하려면 → [01. 셋업 (CLI)](01-setup-cli.md)

## 참고 문서

- [Quickstart: Build with models and agents](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code)
- [Create and deploy an Azure OpenAI resource](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/create-resource)
- [Understanding deployment types in Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types)
- [RBAC for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry)
- [Plan a Foundry rollout](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/planning)
