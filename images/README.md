# 스크린샷 이미지 폴더

각 문서에 표시된 `[스크린샷 placeholder]` 위치에 아래 파일명으로 캡처 이미지를 넣으세요.
문서의 마크다운 이미지 경로는 `images/<파일명>` 형식으로 추가하면 됩니다.

예시:
```markdown
![모델 배포 화면](../images/01-deploy-model.png)
```

> 참고: 텍스트 다이어그램을 대체한 `.svg` 파일은 이 폴더에서 관리합니다. Microsoft 공식 문서/Azure-Samples 레퍼런스 다이어그램은 문서에서 직접 링크합니다.

## 필요한 스크린샷 목록

### 공통 / 개념
- [x] `00-guide-roadmap.svg` — README 권장 진행 순서 다이어그램

### 01. Entra + Foundry 셋업
- [ ] `01-create-project.png` — Foundry 포털 "Create project" 화면
- [ ] `01-project-endpoint.png` — 프로젝트 Overview의 엔드포인트 영역
- [ ] `01-deploy-model.png` — 모델 배포 설정 다이얼로그 (배포 이름/유형/TPM)
- [ ] `01-role-assignment.png` — IAM 역할 할당(Foundry User) 화면

### 02. API 호출
- [ ] `02-keys-endpoint.png` — Keys and Endpoint 화면 (키 마스킹)

### 03. Copilot + Foundry 연동
- [x] `03-copilot-apim-governance-flow.svg` — Copilot 호출의 APIM 운영 전환 흐름
- [ ] `03-vscode-add-azure.png` — VS Code Manage Models → Add Models → Azure 선택
- [ ] `03-vscode-key-endpoint.png` — API 키/엔드포인트 입력 화면 (키 마스킹)
- [ ] `03-vscode-model-picker.png` — 모델 선택기에 추가된 Foundry 모델

### 04. 전체 API 호출 거버닝 아키텍처
- [x] `04-governance-entry-flow.svg` — 모든 LLM 호출을 APIM으로 모으는 중앙 진입점 다이어그램
- [x] `04-gateway-comparison.svg` — APIM AI 게이트웨이 도입 전후 비교 다이어그램
- [x] `04-observability-data-flow.svg` — APIM 관측 가능성 데이터 소스 계층 다이어그램
- [ ] `04-foundry-ai-gateway.png` — Foundry에서 AI 게이트웨이 연결 화면 (미리 보기)
- [ ] `04-apim-llm-logs.png` — APIM LLM API 로깅 설정 화면
- [ ] `04-token-metrics-workbook.png` — Azure Monitor/Workbook 토큰 메트릭 화면
- [ ] `04-architecture-custom.png` — (선택) 고객 환경 전용 아키텍처 다이어그램

## 팁
- 캡처에 **키/구독 ID/이메일 등 민감 정보가 보이면 마스킹**하세요.
- PNG 권장. 너무 큰 이미지는 가로 1600px 정도로 리사이즈하면 레포가 가벼워집니다.
