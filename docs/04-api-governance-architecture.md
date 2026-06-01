# 04. 전체 API 호출 거버닝 아키텍처 — AI 게이트웨이 · 관측 가능성

> 앞 장까지는 ① 앱 코드에서 직접 Foundry 배포를 호출하고, ② VS Code Copilot / Copilot CLI에서도 같은 배포를 호출했습니다. 운영 단계에서는 이 모든 호출을 **APIM AI 게이트웨이**로 모아 통제하고, 게이트웨이의 **Observability**(토큰 메트릭·로깅)로 "누가, 얼마나 쓰는가"를 추적하며, 이를 **엔터프라이즈 참조 아키텍처**로 종합합니다.

## 이 문서에서 다루는 내용

- APIM AI 게이트웨이의 역할
- 토큰 한도, 쿼터, 시맨틱 캐싱, 로드밸런싱
- Application Insights와 Azure Monitor 기반 관측 가능성
- 엔터프라이즈 참조 아키텍처 연결

![APIM AI 게이트웨이 중앙 진입점 아키텍처](../images/04-governance-entry-flow.svg)

## Part A. APIM AI 게이트웨이 — 모든 호출을 한 곳에서 통제

### A-1. APIM "AI 게이트웨이"란?

**Azure API Management(APIM)** 의 "AI 게이트웨이"는 **별도 제품이 아니라** 기존 API 게이트웨이에 포함된 **기능 묶음**입니다. (기능 가용성은 APIM 티어별로 다름.)

지원 대상:

- **OpenAI Chat Completions / Responses API** 스키마를 따르는 LLM API
- **Anthropic Messages API** 스키마를 따르는 LLM API (현재 APIM v2 티어에서 지원)
- Microsoft Foundry 배포 모델, Amazon Bedrock 같은 비-Microsoft 공급자 모델, 자체 호스팅 모델/엔드포인트
- 원격 **MCP 서버** 및 **A2A 에이전트 API**

### 왜 게이트웨이를 두나?

![APIM AI 게이트웨이 도입 전후 비교](../images/04-gateway-comparison.svg)

- 팀/앱별 **토큰 한도·쿼터** 강제 (비용 폭주 방지)
- **소비자별 토큰 메트릭** 수집 (정밀 거버넌스)
- **시맨틱 캐싱**으로 응답 지연과 백엔드 호출 비용 절감 (Embeddings API와 RediSearch 호환 외부 캐시 필요)
- 여러 모델 엔드포인트 **로드밸런싱** (PTU 우선 사용 등)
- 단일 진입점에서 **인증·로깅·콘텐츠 안전**

![APIM AI 게이트웨이 기능 요약](https://learn.microsoft.com/en-us/azure/api-management/media/genai-gateway-capabilities/capabilities-summary.png)

*출처: [AI gateway capabilities in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities)*

## Part B. APIM 게이트웨이 관측 가능성 — 소비자별 토큰·로깅

APIM AI 게이트웨이는 정책과 진단 설정을 통해 게이트웨이를 지나는 LLM 호출의 **토큰 소비를 메트릭으로 방출**하고, 필요하면 **프롬프트/완성 메시지를 로그로 수집**합니다. 토큰 메트릭은 Application Insights 커스텀 메트릭으로, LLM 로그는 Azure Monitor Logs/Log Analytics의 `ApiManagementGatewayLlmLog` 테이블로 분석하는 흐름이 기본입니다.

### B-1. 토큰 메트릭 — `llm-emit-token-metric`

토큰 소비를 **Application Insights 커스텀 메트릭**으로 전송 → **소비자별 정밀 추적**. 토큰 범주는 모델/공급자 응답에 따라 total, prompt, completion, cached, reasoning, thinking 등이 포함될 수 있습니다. 정책당 최대 **5개 커스텀 차원**(Azure Monitor 커스텀 메트릭 제한)을 구성할 수 있습니다.

필수 전제:

- LLM API가 APIM에 추가되어 있어야 함
- APIM이 Application Insights와 통합되어 있어야 함
- 해당 LLM API의 Application Insights 로깅과 차원 포함 커스텀 메트릭이 활성화되어 있어야 함

```xml
<llm-emit-token-metric namespace="genai">
  <dimension name="Subscription ID" value="@(context.Subscription.Id)" />
  <dimension name="Client IP"       value="@(context.Request.IpAddress)" />
  <dimension name="API ID"          value="@(context.Api.Id)" />
</llm-emit-token-metric>
```

→ 이 메트릭으로 Azure Monitor 대시보드/Workbook에서 **팀별 토큰 소비**를 추적할 수 있습니다. Datadog을 함께 쓰는 경우 Azure Native ISV 연동 또는 Azure Monitor 메트릭 수집 구성을 통해 같은 운영 관점으로 통합할 수 있습니다.

![토큰 메트릭 방출](https://learn.microsoft.com/en-us/azure/api-management/media/genai-gateway-capabilities/emit-token-metrics.png)

### B-2. 로깅·콘텐츠 안전·관리 ID

- **프롬프트/완성 로깅**: APIM 진단 설정에서 "generative AI gateway" 로그를 Log Analytics로 보내고, API 설정의 **Log LLM messages**에서 프롬프트/완성 로깅을 켜야 합니다. 메시지는 32KB 단위로 분할될 수 있고, 요청/응답 메시지는 각각 최대 2MB까지 로깅됩니다.
- **콘텐츠 안전**: `llm-content-safety` 정책으로 Azure AI Content Safety 모더레이션 적용. APIM 관리 ID에는 Content Safety 리소스에 대한 Cognitive Services User 권한이 필요합니다.
- **관리 ID 인증**: APIM이 관리 ID로 Azure AI 서비스에 인증 (키리스). Azure AI 서비스 대상 리소스 ID는 일반적으로 `https://cognitiveservices.azure.com/`를 사용합니다.

### B-3. 데이터 소스 계층

![APIM AI 게이트웨이 관측 가능성 데이터 흐름](../images/04-observability-data-flow.svg)

- **소비자별 토큰 거버넌스의 1차 소스**는 `llm-emit-token-metric`이 내보내는 Application Insights 커스텀 메트릭입니다.
- **프롬프트/완성 감사·디버깅·평가 데이터**는 Azure Monitor Logs의 `ApiManagementGatewayLlmLog`에서 KQL로 분석합니다.
- **소비자(팀/앱/사용자)별로 정밀하게 토큰을 추적**하려면 `Subscription ID`, `User ID`, `API ID`처럼 카디널리티를 통제할 수 있는 차원을 고르는 것이 중요합니다. 너무 많은 고유값을 가진 차원은 Azure Monitor 커스텀 메트릭 시계열 제한에 빨리 도달할 수 있습니다.

## Part C. 엔터프라이즈 참조 아키텍처 — AI Hub Gateway Landing Zone

Azure-Samples 공식 솔루션 액셀러레이터 **AI Hub Gateway Landing Zone** 의 종합 아키텍처입니다. APIM을 중앙 AI 게이트웨이로 두고 다중 백엔드·네트워킹·모니터링·아이덴티티를 모두 포함한, 가장 완성도 높은 엔터프라이즈 참조 구성입니다.

![AI Hub Gateway Landing Zone 아키텍처](https://raw.githubusercontent.com/Azure-Samples/ai-hub-gateway-solution-accelerator/main/assets/architecture-1-0-6.png)

*출처: [Azure-Samples/ai-hub-gateway-solution-accelerator](https://github.com/Azure-Samples/ai-hub-gateway-solution-accelerator)*

## 참고 문서

**APIM AI 게이트웨이 · 관측 가능성**

- [AI gateway capabilities in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities)
- [Configure AI Gateway in your Foundry resources](https://learn.microsoft.com/en-us/azure/ai-foundry/configuration/enable-ai-api-management-gateway-portal)
- [llm-token-limit policy](https://learn.microsoft.com/en-us/azure/api-management/llm-token-limit-policy)
- [llm-emit-token-metric policy](https://learn.microsoft.com/en-us/azure/api-management/llm-emit-token-metric-policy)
- [Log token usage, prompts, and completions for language model APIs](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-llm-logs)
- [llm-content-safety policy](https://learn.microsoft.com/en-us/azure/api-management/llm-content-safety-policy)
- [Enable semantic caching for LLM APIs in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/azure-openai-enable-semantic-caching)
- [Datadog - Azure Native Integrations 개요](https://learn.microsoft.com/en-us/azure/partner-solutions/datadog/overview)
- [Azure Monitor 개요](https://learn.microsoft.com/en-us/azure/azure-monitor/overview)
- [Application Insights 개요](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)

**엔터프라이즈 아키텍처**

- [Azure-Samples/ai-hub-gateway-solution-accelerator](https://github.com/Azure-Samples/ai-hub-gateway-solution-accelerator)
