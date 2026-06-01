# Microsoft Foundry 도입 가이드



이 가이드는 Microsoft Foundry를 처음 도입하는 팀이 다음 흐름을 순서대로 검증할 수 있도록 구성되어 있습니다.

- Foundry의 리소스, 프로젝트, 배포 개념 이해
- 포털 또는 Azure CLI로 Foundry 리소스와 모델 배포 구성
- API Key와 Microsoft Entra ID 방식으로 모델 호출 검증
- VS Code Copilot Chat과 GitHub Copilot CLI에서 Foundry 모델 연결
- APIM AI 게이트웨이로 앱과 개발자 도구 호출을 함께 거버닝

## 가이드 구성

각 문서는 독립적으로 읽을 수 있지만, 처음 도입하는 경우에는 아래 순서를 권장합니다.

### 00. 개념 소개

[문서 열기](docs/00-concepts.md)

- Foundry 리소스, 프로젝트, 배포의 관계
- 리소스 기반 프로젝트와 Hub 기반 프로젝트 차이
- 배포 이름과 모델 이름의 차이
- Microsoft Entra ID와 키리스 인증의 기본 개념

### 01. Entra ID + Foundry 셋업

[포털 가이드](docs/01-setup-portal.md) | [CLI 가이드](docs/01-setup-cli.md)

- Resource Group, Foundry 리소스, 기본 프로젝트 생성
- 모델 배포와 배포 유형 선택
- 개발자에게 Foundry User 역할 부여
- 포털 기반 수동 셋업과 CLI 기반 자동화 트랙 제공

### 02. API 호출

[문서 열기](docs/02-api-calls.md)

- API Key 방식 호출
- Microsoft Entra ID 기반 키리스 호출
- Python SDK와 Responses API 기준 예제
- 로컬 개발과 운영 환경의 인증 흐름 차이

### 03. Copilot에서 Foundry 모델 호출

[문서 열기](docs/03-copilot-foundry-integration.md)

- VS Code Copilot Chat BYOK 설정
- GitHub Copilot CLI custom provider 설정
- API Key, bearer token, APIM 경유 호출 차이
- 실제 검증된 Kimi 및 APIM 호출 패턴

### 04. 전체 API 호출 거버닝 아키텍처

[문서 열기](docs/04-api-governance-architecture.md)

- APIM AI 게이트웨이를 통한 중앙 진입점 구성
- 토큰 한도, 쿼터, 로깅, 메트릭 수집
- Application Insights와 Azure Monitor 기반 관측 가능성
- 엔터프라이즈 참조 아키텍처 연결

## 시작하기

1. 개념이 낯설다면 [00. 개념 소개](docs/00-concepts.md)부터 읽습니다.
2. 화면으로 따라 하려면 [포털 셋업](docs/01-setup-portal.md), 자동화를 검증하려면 [CLI 셋업](docs/01-setup-cli.md)을 진행합니다.
3. 모델 배포 후 [API 호출](docs/02-api-calls.md)에서 직접 호출을 확인합니다.
4. 개발자 도구 연동이 필요하면 [Copilot 연동](docs/03-copilot-foundry-integration.md)을 진행합니다.
5. 운영 전환 시 [APIM 거버넌스 아키텍처](docs/04-api-governance-architecture.md)로 호출 경로를 통합합니다.

## 작성 기준

- 작성일: 2026-06
- Microsoft Foundry는 빠르게 업데이트되므로, 실제 적용 전 각 문서의 Microsoft Learn 링크에서 최신 내용을 확인하세요.
- 본문에서는 제품 리브랜딩을 반영해 Microsoft Foundry를 기본 명칭으로 사용하고, 필요한 경우 Azure AI Foundry 명칭을 함께 표기합니다.

