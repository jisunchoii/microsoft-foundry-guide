# 00. 개념 소개

Microsoft Foundry를 쓰기 전에 알아야 하는 리소스 구조, 프로젝트 유형, 배포 이름, 인증 개념을 정리합니다.

## 이 문서에서 다루는 내용

- Foundry 리소스 계층
- 리소스 기반 프로젝트와 Hub 기반 프로젝트 차이
- API 호출 시 사용하는 배포 이름
- Microsoft Entra ID와 키리스 인증

## 1. 전체 구조

- **구독**: 과금·결제의 최상위 경계
- **리소스 그룹**: 함께 관리·삭제되는 리소스 묶음
- **Foundry 리소스**: AI 환경 전체. 보안·모니터링·과금의 단위
- **프로젝트**: 리소스 안의 작업 공간. 에이전트·평가·파일·연결·권한 관리 단위
- **배포**: Foundry 리소스에 생성되는 호출 가능한 모델. API 호출 시 배포 이름 사용

## 2. 리소스 기반 프로젝트 vs Hub 기반 프로젝트

Foundry에는 두 가지 프로젝트 유형이 있습니다. **신규 고객은 무조건 "리소스 기반(새 포털)"으로 시작하세요.**

| 구분 | 리소스 기반 프로젝트 (신규) | Hub 기반 프로젝트 (클래식) |
|------|----------------------------|----------------------------|
| 상태 | **신규 투자 집중** | 유지보수 모드 |
| 포털 | 새 Foundry 포털 (`ai.azure.com`) | Foundry (classic) 포털 |
| 기반 | Foundry 리소스 | Hub (Azure ML 워크스페이스 기반) |
| SDK | `azure-ai-projects` 2.x | 구형 패키지 |
| 엔드포인트 | 단일 프로젝트 엔드포인트 | 여러 엔드포인트 |
| API 버전 | v1 안정 경로(`/openai/v1/`) | 월별 `api-version` |

## 3. 배포(Deployment)의 핵심 — "모델 이름이 아니라 배포 이름"

- 모델을 배포할 때 **배포 이름**을 직접 정합니다 (예: 모델 `gpt-4o` → 배포 이름 `my-gpt4o-prod`).
- **API 호출 시에는 배포 이름을 사용**합니다. OpenAI 공개 API와의 가장 큰 차이점입니다.

```python
# OpenAI 공개 API 방식 (모델 이름)
client.responses.create(model="gpt-4o", input="...")

# Azure Foundry 방식 (배포 이름)
client.responses.create(model="my-gpt4o-prod", input="...")
```


## 4. Microsoft Entra ID — Azure의 신원/권한 시스템

**Microsoft Entra ID**(구 Azure AD)는 "누가 무엇을 할 수 있는가"를 관리하는 Azure의 ID 서비스입니다.

- **RBAC (역할 기반 접근 제어)**: 사용자/앱에 **역할(Role)** 을 부여해 권한을 제어합니다.
- **키리스(Keyless) 인증**: API 키를 뿌리는 대신 Entra ID 토큰으로 인증 → 키 유출 위험 제거, 세분화된 권한, 추적성 확보.
- **Managed Identity(관리 ID)**: Azure에서 실행되는 앱(VM, Functions 등)이 **자격 증명을 저장하지 않고** 자동으로 인증.

> Microsoft 공식 권고: *"키 기반 인증은 키가 전체 접근 권한을 부여하므로 역할 제한이 없습니다. 보안과 세분화된 접근 제어를 위해 Entra ID 인증을 권장합니다."*

자세한 인증 방법은 [02. API 호출](02-api-calls.md)에서 다룹니다.

## 다음 단계

개념을 이해했다면 [01. Entra ID + Foundry 셋업 (포털)](01-setup-portal.md) 또는 [(CLI)](01-setup-cli.md)로 진행하세요.


## 참고 문서

- [What is Microsoft Foundry?](https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry)
- [Plan a Foundry rollout](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/planning)
- [Azure 리소스 그룹 개념](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview)
- [What is Microsoft Entra ID?](https://learn.microsoft.com/en-us/entra/fundamentals/whatis)
