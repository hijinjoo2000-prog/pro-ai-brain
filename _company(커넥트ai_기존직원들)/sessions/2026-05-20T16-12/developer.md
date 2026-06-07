# 💻 코다리 — Researcher가 정의한 공통 핵심 필드 그룹을 기반으로, '재개발 정보 게이트웨이'의 테스트용 API 엔드포인트(Mockup) 스펙 v2.0을 작성해주세요. 이 스펙에는 요청 파라미터 검증 로직과 함께, 데이터 통합 과정에서 발생하는 오류 처리 방안(Error Handling)까지 포함해야 합니다. 핵심은 '법적 리스크 판단'에 필요한 특정 필드가 누락되거나 충돌할 때의 응답 포맷을 정의하는 것입니다.

💻 코다리: 작업 시작합니다.
CEO님의 지시와 Researcher가 정의한 핵심 데이터 스키마를 바탕으로, 재개발 정보 게이트웨이의 API 명세서 v2.0을 작성하겠습니다.

일단요, 단순히 필드 목록만 나열하는 건 설계 단계에서나 유효해요. 실제 운영 환경에서는 데이터 소스 간의 **논리적 모순(Logical Conflict)**이나 **누락된 전제 조건** 때문에 요청이 실패하거나 잘못된 데이터를 받을 확률이 훨씬 높습니다.

따라서 이 스펙은 단순한 '데이터를 가져오는 방법'을 넘어, 게이트웨이가 내부적으로 어떤 검증 로직과 오류 처리를 수행해야 하는지에 초점을 맞춰서 정의하겠습니다. 모든 응답 포맷은 일관성 있게 `status`와 상세한 `details`를 포함하도록 표준화했습니다.

---

## ⚙️ 재개발 정보 통합 게이트웨이 API 명세서 (v2.0)

### 1. 목표 및 전제
*   **API 목적:** 세 이질적 데이터 소스(네이버, 법제처, 정보몽땅)를 단일화된 `Core Data Schema`로 병합하고, 통합 과정에서 발생하는 논리적 모순을 검증하여 최종 '법률 리스크 스코어'를 산출하는 것.
*   **기술 아키텍처 관점:** 게이트웨이는 모든 요청을 받고, 각 소스별 어댑터(Adapter)로 라우팅한 뒤, 결과를 받아 **데이터 변환 레이어 (Transformation Layer)**에서 통합 검증 및 스코어링을 수행해야 합니다.

### 2. 핵심 데이터 모델 (Core Data Schema - Reconfirm)
Researcher가 정의한 필드는 그대로 사용하며, 리스크 판단에 필요한 `Risk_Score`와 그 근거를 추가합니다.

| 필드명 | 유형 | 필수 여부 | 설명/포함 내용 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| `Matter_ID` | String | 필수 | 통합을 위한 고유 식별자 (UUID) | Primary Key. |
| `Standard_Address` | String | 필수 | 법적 주소 표기 | Input validation 필요. |
| `Parcel_Code` | String | 필수 | 필지 고유 식별 코드 (Lot ID) | **최우선 매칭 키.** 형식 검증 필수. |
| `Zoning_Status` | Code | 필수 | 용도지역 및 지구 지정 상태 코드 | 법제처 API 연동 결과. |
| `Development_Stage` | Enum | 필수 | 재개발 진행 단계 (초기검토~관리처분인가) | **데이터 충돌 검증 핵심 필드.** |
| `Market_Price_Range`| Tuple | 선택 | 현재 매물 기준 시세 범위 | 네이버 크롤링 결과. |
| `Legal_Conflict_Flag`| Boolean | 필수 | 법적 정보의 모순이 발견되었는지 여부 (True/False) | **Gateway 자체 검증 필드.** |
| `Risk_Score` | Float | 필수 | 0.0 (안전) ~ 10.0 (위험). 총 리스크 스코어. | 최종 산출물. |
| `Last_Update_Date` | Date | 필수 | 데이터 수집 및 통합 완료 시간 | 신뢰성 확보. |

### 3. API 엔드포인트 명세 (Mockup Specification)

#### A. 주 거주지 정보 조회 (Matter Information Retrieval)
*   **엔드포인트:** `GET /v1/matter-info`
*   **목적:** 주어진 필지 코드와 주소를 기반으로 모든 데이터를 통합하고 리스크 스코어를 산출한다.
*   **요청 파라미터 (Request Parameters):**
    | 이름 | 타입 | 필수 | 설명 | 검증 로직 |
    | :--- | :--- | :--- | :--- | :--- |
    | `parcel_code` | String | Yes | 필지 고유 식별 코드. | **정규식 검사:** `^[A-Z]{2}\\d{4}$` 형식 필수. |
    | `standard_address` | String | Yes | 표준화된 주소. | 공백 및 특수문자 이스케이프 처리. |

*   **요청 Body (Query Parameters):** (GET 방식이므로 Query Params만 사용)

#### B. 법적 진행 상태 조회 (Law Status Check)
*   **엔드포인트:** `GET /v1/law-status`
*   **목적:** 특정 필지 코드에 대해 최신 법제처 정보를 가져와 개발 단계의 유효성을 검증한다.
*   **요청 파라미터 (Query Parameters):**
    | 이름 | 타입 | 필수 | 설명 | 검증 로직 |
    | :--- | :--- | :--- | :--- | :--- |
    | `parcel_code` | String | Yes | 필지 고유 식별 코드. | A와 동일한 정규식 검사. |

#### C. 처리 과정 질의 (Process Query - Lead Event/Kakao API 연동)
*   **엔드포인트:** `POST /v1/process-query`
*   **목적:** 매수자의 특정 액션(예: 카톡 보내기)을 기록하고 리드를 추적하는 요청.
*   **요청 Body (JSON):**
    ```json
    {
      "matter_id": "uuid-string",
      "user_event_type": "KAKAO_CHAT_LEAD", // 액션 타입 정의 필수
      "metadata": {
        "client_ip_hashed": "sha256-hash",
        "timestamp_utc": "ISO 8601 Date String",
        "source_page": "/v1/matter-info?parcel_code=..." // 추적 경로 기록
      }
    }
    ```

### 4. 응답 포맷 정의 (Standard Response Format)

#### A. 성공 응답 (`HTTP Status: 200 OK`)
데이터가 정상적으로 통합되었으며, 모든 검증이 완료된 경우의 표준 응답 구조입니다.

```json
{
  "status": "SUCCESS",
  "message": "재개발 정보 통합 및 리스크 스코어링을 완료했습니다.",
  "data": {
    "Matter_ID": "uuid-string",
    "Standard_Address": "서울시 강남구 역삼동 OOO-O",
    "Parcel_Code": "GN1234",
    "Zoning_Status": "Residential High Density (RHD)", // 법제처 출처 명시 권장
    "Development_Stage": "Combination Establishment Preparation", 
    "Market_Price_Range": {
      "min": 800,
      "max": 1200,
      "unit": "만원/평"
    },
    "Last_Update_Date": "2026-05-21T10:30:00Z",
    // --- 핵심 가치 추가 필드 ---
    "Legal_Conflict_Flag": false, // False일 경우 안전함.
    "Risk_Score": 2.5, // (Low/Medium/High) 리스크 점수.
    "Validation_Report": {
      "conflict_details": "법제처와 정보몽땅 간의 용도지역 변경 시점 불일치 발견됨.", // 충돌이 없으면 null
      "recommendation": "추가적인 현장 실측 또는 법무사 자문 권고." 
    }
  }
}
```

#### B. 오류 응답 (Error Handling Strategy)
모든 실패 케이스는 표준화된 에러 코드를 반환해야 합니다. 게이트웨이는 단순히 '데이터를 못 가져왔다'가 아니라 **'어떤 종류의 검증에 실패했는지'** 알려줘야 합니다.

```json
{
  "status": "ERROR",
  "error_code": "GATEWAY_VALIDATION_FAIL", // 표준화된 에러 코드 (ex: INVALID_PARCEL_CODE, DATA_CONFLICT)
  "message": "요청 파라미터 검증에 실패했거나 데이터 통합 중 논리적 오류가 발생했습니다.",
  "details": {
    "failed_field": "parcel_code",
    "required_format": "^[A-Z]{2}\\d{4}$",
    "user_input": "GN123", // 실제로 사용자에게 잘못 입력된 값
    "action_required": "필지 코드는 반드시 두 글자 영문과 네 자리 숫자여야 합니다."
  }
}
```

### 5. 검증 로직 및 오류 처리 상세 (The Core Logic)

가장 중요한 것은 `GET /v1/matter-info` 요청 시 게이트웨이가 수행해야 할 내부 워크플로우입니다.

#### 🔍 A. 필수 파라미터 검증 (Pre-flight Check)
1.  **파라미터 유효성:** `parcel_code`와 `standard_address`가 누락되거나, `parcel_code`의 형식이 틀리면 즉시 **HTTP 400 Bad Request + `INVALID_PARCEL_CODE` 에러 반환**.
2.  **존재 여부 확인:** 요청된 조합이 실제로 존재하는 필지인지 (API 호출 전) 최소한의 조회로 검증합니다.

#### 🔍 B. 데이터 소스 통합 및 충돌 감지 (Integration & Conflict Detection)
게이트웨이는 다음 로직을 순차적으로 수행하며, 모순 발견 시 `Legal_Conflict_Flag`를 **True**로 설정하고 `Validation_Report`에 상세 내용을 기록해야 합니다.

1.  **단계 동기화 검증:** 법제처 API가 제공하는 '법적 지정 상태'와 정보몽땅 API가 제공하는 '공식 진행 단계'가 논리적으로 모순되는지 확인합니다.
    *   *(예시 충돌)*: `Zoning_Status`는 아직 '초기검토'인데, `Development_Stage`가 이미 '관리처분인가'로 되어 있다면 🔴 **논리적 오류 발생**.
2.  **정보 최신성 검증:** 각 소스별 데이터의 `Last_Update_Date`를 비교하여 가장 오래된 데이터를 사용했거나(데이터 신뢰도 하락), 너무 오랜 기간 업데이트가 없다면 경고(`Warning`) 레벨을 부여합니다.

#### 🔍 C. 리스크 스코어링 (Risk Scoring)
모든 검증이 완료된 후, 다음과 같은 가중치 기반으로 최종 `Risk_Score`를 산출해야 합니다.

*   **필수 점수:** 법적 충돌 발견 (`Legal_Conflict_Flag=True`) -> **+4점**.
*   **경고 점수:** 주거 용도지역이 급격히 변경된 경우 (법제처) -> **+2점**.
*   **불명확 점수:** 특정 데이터(예: 시세 범위)가 너무 넓거나, 업데이트 간격이 긴 경우 -> **+1점**.

---
📊 평가: 완료 — 요청받은 핵심 기능(Validation, Error Handling, Risk Focus)을 모두 포함한 v2.0 스펙 문서를 완성했습니다.
📝 다음 단계: 이 명세를 기반으로 백엔드 서버의 실제 API 구현 스캐폴딩 및 테스트 코드를 작성하겠습니다. (예: FastAPI/Python Mockup)
