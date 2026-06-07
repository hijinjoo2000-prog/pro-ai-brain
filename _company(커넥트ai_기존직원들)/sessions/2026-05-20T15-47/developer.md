# 💻 코다리 — Researcher가 제공한 기술적 가이드라인을 바탕으로 '재개발 정보 통합 게이트웨이'의 아키텍처 초안(High-Level Design)을 설계하고, 핵심 모듈 인터페이스 정의서(API Spec)를 작성해 주세요. 이 게이트웨이는 나중에 연동될 모든 외부 API (네이버, 법제처, 정보몽땅 등)의 요청과 응답을 표준화된 단일 데이터 포맷으로 변환하는 역할을 담당해야 합니다.

💻 코다리: 작업 시작합니다.

CEO 지시가 매우 명확하고 중요도가 최상입니다. Researcher가 제시한 기술적 필요성(이벤트 소싱, 마이크로서비스)을 바탕으로 실제 시스템의 뼈대인 '게이트웨이 아키텍처'를 설계하는 것은 이 프로젝트의 성패를 가르는 핵심 작업입니다.

단순히 기능을 나열하는 API Spec은 의미가 없습니다. 모든 데이터 흐름과 상호 의존성을 정의한 **통합 표준 데이터 모델(Unified Schema)**을 먼저 확정하고, 이를 기준으로 게이트웨이를 설계해야 합니다. 그렇지 않으면 어느 외부 API의 응답이 들어와도 우리가 원하는 형태로 재조립할 수 없기 때문입니다.

따라서, 저는 이 통합 아키텍처를 담은 마스터 문서인 `RedevelopmentGateway_DesignSpec.md` 파일을 생성하고, 그 안에 High-Level Design과 필수적인 모듈 인터페이스 정의서(API Spec)를 포함하겠습니다.

### ⚙️ 작업 계획:
1.  **통합 표준 데이터 모델 (Unified Schema)** 정의: 네이버 매물, 법제처 절차, 정보몽땅 진행상황을 모두 포괄하는 공통 스키마를 설계합니다.
2.  **아키텍처 다이어그램/흐름 정의**: Gateway가 각 외부 API(Adapter)로부터 데이터를 받아 어떻게 통합하고 검증하여 최종 사용자에게 제공할지 단계별로 명시합니다.
3.  **API Specification 작성**: 핵심 엔드포인트와 요청/응답 포맷을 OpenAPI Spec 형태로 상세히 정의합니다.

이 설계서는 향후 백엔드 팀이 스캐폴딩(Scaffolding) 및 구현 시 '규격서' 역할을 할 것입니다.

<create_file path="./src/arch/RedevelopmentGateway_DesignSpec.md"># 🏗️ 재개발 정보 통합 게이트웨이 (Redevelopment Gateway) 설계 명세서 V1.0

## 🎯 목표 및 역할
본 Gateway는 대한민국 재개발 플랫폼의 핵심 데이터 허브 역할을 수행합니다. 외부에서 유입되는 세 가지 성격이 다른 데이터를 **'법적 위험도'와 '시장 적정성'이라는 단일 관점**으로 통합하고, 이를 표준화된 포맷으로 사용자에게 제공하는 것이 목표입니다.

핵심 기능은 단순한 데이터 취합(Aggregation)을 넘어, 각 데이터 간의 **논리적 모순(Legal Contradiction)**을 발견하고 이를 서비스 레이어에서 '리스크 스코어'로 가공하여 전달하는 것입니다.

## Ⅰ. 아키텍처 개요 (High-Level Design)
본 Gateway는 마이크로서비스 패턴 기반으로 설계되며, 데이터 흐름은 다음의 4단계 파이프라인을 따릅니다.

### 1. Ingestion & Adapters Layer (데이터 수집/어댑터 레이어)
*   **역할:** 외부 API 호출 및 응답 처리를 전담합니다. 각 외부 API는 고유한 요청 포맷, 인증 방식, 오류 코드를 가집니다. 이 계층은 모든 비표준화된 데이터를 받아 표준 데이터 모델로 변환하는 'Adapter' 역할을 합니다.
*   **모듈:**
    *   `NaverMatterAdapter`: 네이버 부동산 크롤링/API 호출 및 매물 데이터 추출. (비정형 텍스트 $\rightarrow$ 표준 구조)
    *   `LawMinistryAdapter`: 법제처 API 연동. 재개발 절차법, 규제 변경 이력 등 법적 근거 데이터를 가져옴. (규격화된 JSON $\rightarrow$ 표준 구조)
    *   `InfoMongttangAdapter`: 정보몽땅 데이터 수집. 구역별 진행 상황 및 행정 정보를 가져옴. (반구조화된 API 응답 $\rightarrow$ 표준 구조)

### 2. Event Sourcing & Data Persistence Layer (핵심 저장소/이벤트 소싱)
*   **역할:** 모든 원본 데이터를 가공하기 전에, 데이터의 '상태 변화'를 시간 순서대로 기록합니다. 이는 "어떤 시점 T에서 이 법규가 이러했고, 매물 가격은 저랬다"라는 과거 상황을 재현(Replay)하는 데 필수적입니다.
*   **기술:** Event Store (예: Kafka + PostgreSQL/Cassandra).
*   **핵심 데이터 흐름:** `[Event] LawStatusChanged` $\rightarrow$ `[Event] PriceFluctuationDetected` $\rightarrow$ **Current State Update.**

### 3. Standardization & Business Logic Layer (데이터 통합 및 검증)
*   **역할:** 가장 중요한 계층입니다. Adapter를 통해 들어온 데이터를 표준 스키마로 변환하고, 비즈니스 로직(검증/분석)을 수행합니다.
    *   **핵심 분석 모듈 1: 법적 논리 충돌 검사 (Legal Conflict Checker):** LawMinistryAdapter의 결과와 InfoMongttangAdapter의 결과를 교차 검증하여 '법규 A가 요구하는 절차'와 '실제 진행 상황 B' 간에 Gap이 있는지 식별합니다.
    *   **핵심 분석 모듈 2: 시장 적정성 비교 (Market Fit Checker):** 매물 데이터(가격)를 법적 상태/진행 단계에 따라 표준화된 가치 지표와 비교하여 '과대평가/저평가 위험도'를 산출합니다.

### 4. API Gateway Layer (사용자 인터페이스 노출)
*   **역할:** 클라이언트(프론트엔드)의 요청을 받아, 내부의 복잡한 데이터 처리 과정을 숨기고, 최종적으로 하나의 응답 객체(Unified Red-Report DTO)를 반환합니다.

---

## Ⅱ. 통합 표준 데이터 모델 (Unified Schema / DTO)
모든 외부 API가 이 스키마로 변환되는 것을 목표로 합니다.

| 필드명 | 타입 | 설명 | 출처 우선순위 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| `areaId` | String | 표준화된 지역 코드 (예: '서울_강남구_A-1') | 필수 | 모든 데이터의 기본 Key. |
| `reportDate` | Date | 보고서가 작성/갱신된 기준 시점 (UTC) | 필수 | 법적 유효성을 위한 시간 정보. |
| `legalStatusSummary` | String | 현재 재개발 구역의 법적 요약 상태 (예: '조합설립추진위 단계 진행 중') | InfoMongttangAdapter | 핵심 진단 값 1. |
| `currentLegalStage` | Enum | 가장 높은 수준의 공식적인 법률 진행 단계를 정의. | LawMinistryAdapter | 예: PRE-DESIGN $\rightarrow$ DESIGN $\rightarrow$ CONSTRUCTION. |
| `legalConflictDetected` | Boolean | 법적/행정적 충돌 위험 감지 여부. (True 시 상세 리포트 필수) | Business Logic Layer | **[최고 가치 지표]** 이 값이 True면 Warning Level 상승. |
| `marketPriceRange` | Object | 현재 매물의 표준화된 가격 범위 및 변동성 데이터. | NaverMatterAdapter | {min: Number, max: Number, avg: Number} |
| `riskAnalysisReport` | Array<Object> | 법적/시장 리스크 보고서 세부 내용 (Impact Red Box용). | Business Logic Layer | `{type: 'LEGAL'/'MARKET', severity: 'High'/'Medium', detail: String}` |

---

## Ⅲ. 핵심 모듈 인터페이스 정의서 (API Spec)
모든 API 호출은 백엔드 게이트웨이를 통해서만 이루어져야 하며, 클라이언트는 다음의 단일 엔드포인트를 사용합니다.

### 📌 Endpoint: `/api/v1/diagnose/{areaId}`
*   **Method:** `GET`
*   **Description:** 특정 지역 ID에 대한 종합적인 법적 위험도 및 시장 적정성 진단 리포트 조회. (가장 핵심 기능)
*   **Request Parameters:**
    *   `areaId` (Path, Required): 진단을 원하는 표준화된 지역 식별자.
    *   `detailLevel` (Query, Optional): 'SUMMARY' 또는 'DEEP'. (기본값: SUMMARY)

*   **Response Schema (200 OK - Unified Red-Report DTO):**
    ```json
    {
      "status": "SUCCESS",
      "data": {
        "areaId": "서울_강남구_A-1",
        "reportDate": "2026-05-21T12:00:00Z",
        "overallRiskLevel": "HIGH", // LOW, MEDIUM, HIGH (시스템 판단)
        "legalStatusSummary": "조합설립추진위 단계 진행 중. 법적 근거와 매물 시세 간에 괴리 감지.",
        "latestLegalStage": "DESIGN_STAGE_COMPLETE", 
        "isConflictDetected": true, // <-- 가장 중요한 필드!
        "marketAnalysis": {
          "priceRange": {"min": 1200, "max": 1500, "avg": 1350},
          "trendDeviationPct": -8.5 // 법적 단계에 비해 시장가가 낮다는 분석 값 (예시)
        },
        "riskReports": [
          {
            "type": "LEGAL",
            "severity": "HIGH",
            "reasonCode": "LAW_CONFLICT_001", 
            "explanation": "현행 법제처 규정 상, 설계 단계가 완료되었음에도 불구하고 조합 설립 동의율 확보 과정이 미흡함. (관련 법규 A vs 진행 상황 B)",
            "suggestedAction": "변호사 전문 진단 필수."
          },
          // ... 다른 리스크 보고서 항목들
        ]
      }
    }
    ```

## Ⅳ. 구현 시 고려 사항 및 기술 스택
1.  **데이터 정합성 (Data Integrity):** Gateway는 데이터의 출처(Source)를 반드시 기록하고, 어느 필드가 어떤 Adapter에서 왔는지 메타데이터로 관리해야 합니다.
2.  **비동기 처리:** 네이버 크롤링이나 법제처 API 호출은 시간이 오래 걸리므로, 이 작업들은 백그라운드 큐(Queue, e.g., RabbitMQ/Kafka)를 통해 비동기로 처리하고, 최종 결과를 캐시(Redis)에 저장하여 빠른 조회 속도를 보장해야 합니다.
3.  **재시도 로직 (Retry Logic):** 외부 API 호출 실패 시, 단순히 에러를 반환하는 것이 아니라, 지수 백오프(Exponential Backoff)와 같은 전략을 사용하여 자동 재시도 로직을 구현해야 합니다.

</create_file>

이 설계 명세서에는 Gateway의 존재 이유부터 최종적으로 클라이언트에게 전달될 데이터 구조까지 모든 것이 정의되었습니다. 이대로만 진행하면, 나중에 어떤 개발자가 투입되어도 '규격서'를 보고 일관성 있게 코딩할 수 있을 겁니다. 💻✨

📊 평가: 완료 — 아키텍처 설계와 표준 API 스펙을 성공적으로 확정하여 다음 단계의 개발 전제 조건을 마련했습니다.
📝 다음 단계: 이 명세서를 기반으로, 실제 데이터를 받아 처리하는 **Gateway 백엔드 서버의 기본 골격(Scaffolding)** 및 데이터 유효성 검증(Validation) 모듈의 코드를 작성해야 합니다.

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/src/arch/RedevelopmentGateway_DesignSpec.md
