# 🔍 Researcher — 최종 'Core Data Schema'를 재정의하고, 이 스키마에 맞춰 네이버 매물 데이터(텍스트/필드), 법제처 API 결과, 정보몽땅 API 결과를 모두 포괄할 수 있는 통합된 표준 입력 데이터를 정의해 주세요. 단순히 필드를 나열하는 것을 넘어, 각 원본 소스에서 누락되거나 형태가 달라 들어올 수 있는 필수 메타데이터 (예: 크롤링 시점, 데이터 출처 식별자)를 포함하여 최종 'Data Ingestion Schema'를 작성해야 합니다.

🔍 Researcher: 작업 시작합니다.

[CEO 지시]를 수용하여 재개발 정보 게이트웨이의 **최종 데이터 통합 표준 스키마(Data Ingestion Schema)**를 정의했습니다. 이 스키마는 네이버 매물, 법제처 API, 정보몽땅 API 등 세 가지 이질적인 소스에서 들어오는 데이터를 단일하고 구조화된 객체로 변환하기 위한 청사진 역할을 할 것입니다.

단순히 필드를 나열하는 것을 넘어, 데이터의 신뢰성 확보를 위해 **메타데이터 레이어**와 각 원본 출처별 **Source Identification Tag**를 필수적으로 포함했습니다.

### 💾 최종 데이터 통합 표준 입력 스키마 (Core Data Ingestion Schema V1.0)

이 스키마는 모든 재개발 매물 정보를 담을 단일 JSON/객체 구조로 정의되었으며, 각 필드에 `[Type]`과 `[Source Ownership]`를 명시하여 개발자가 어느 소스의 데이터를 우선 참조하고 어떤 타입 변환 로직이 필요한지 직관적으로 파악할 수 있게 했습니다.

---
#### 📂 I. 필수 메타데이터 및 식별자 (Mandatory Metadata & Identifiers)
*   **목적:** 데이터의 출처, 신뢰도, 처리 시점을 명시하여 법률 자문 과정에서 추적 가능하게 함.
| 필드명 | [Type] | [Source Ownership] | 필수 여부 | 설명 및 규칙 |
| :--- | :--- | :--- | :--- | :--- |
| `report_id` | String (UUID) | System | O | 이 보고서에 부여된 고유 식별자. |
| `data_ingestion_timestamp` | DateTime | System | O | 데이터가 게이트웨이에 진입한 시간 (UTC). |
| `property_uuid` | String | Combined | O | 필지(Lot) 단위의 영구적 UUID (최우선 식별자). |
| `address_standardized` | String | All | O | 표준화된 도로명 주소 (예: 서울시 강남구 역삼동 123-45). |
| `source_tracker` | Object | System | O | `{ "naver": Bool, "law_api": Bool, "info_mongttang": Bool }`. 어떤 소스에서 데이터를 받았는지 플래그. |

#### 🏘️ II. 핵심 부동산 속성 데이터 (Core Property Data)
*   **목적:** 매물의 물리적/법률적 기초 정보를 통합.
| 필드명 | [Type] | [Source Ownership] | 필수 여부 | 설명 및 규칙 |
| :--- | :--- | :--- | :--- | :--- |
| `land_area_sqm` | Float | Combined | O | 대지면적 (제곱미터). 네이버/법제처 통합. |
| `total_area_sqm` | Float | Combined | O | 총 면적 (건축물 포함, 제곱미터). |
| `zoning_status` | Enum | InfoMongttang | O | 법정 구역 지정 여부 및 단계 (`미지정`, `구역설정`, `조성계획`, etc.). |
| `initial_legal_risk_score` | Float | System | O | 초기 리스크 점수 (0.0 ~ 10.0). **[Impact Red]** 시각화의 기준점. |

#### 📜 III. 법적/행정 절차 데이터 (Legal & Procedural Data)
*   **목적:** 가장 전문성이 요구되는 부분. 시간 순서와 법규 위반 근거를 구조화.
| 필드명 | [Type] | [Source Ownership] | 필수 여부 | 설명 및 규칙 |
| :--- | :--- | :--- | :--- | :--- |
| `legal_conflict_count` | Integer | System | O | 충돌 지점의 개수 (가장 중요한 KPI). |
| `dispute_details[]` | Array<Object> | Combined | Conditional | **충돌 상세 목록.** 각 객체는 `{ "field": String, "source1_value": Any, "source2_value": Any, "legal_reasoning": String }` 구조를 가짐. (예: 매물 등록일 vs 법정 구역 지정 가능 시점) |
| `applicable_laws[]` | Array<String> | LawAPI | O | 해당 필지에 적용되는 주요 상위 법규 리스트. |
| `development_timeline` | Object | InfoMongttang | O | `{ "designation_date": Date, "plan_completion_date": Date, "estimated_completion_date": Date }`. 시간 순서가 중요함. |

#### 💰 IV. 시장/거래 정보 (Market & Transaction Data)
*   **목적:** 매수자의 의사결정에 필요한 실제 시세 및 거래 정보를 통합.
| 필드명 | [Type] | [Source Ownership] | 필수 여부 | 설명 및 규칙 |
| :--- | :--- | :--- | :--- | :--- |
| `current_asking_price` | Integer | Naver | O | 현재 네이버에 등록된 매매가. (최신 가격) |
| `historical_price_avg[]` | Array<Float> | Naver | X | 과거 유사 거래 또는 동호회 기록 기반 평균 시세. |
| `transaction_risk_assessment` | String | System | O | 통합 분석을 통한 최종 리스크 판단 (예: '주의 필요', '법적 검토 필수'). |

---

### 🚀 실행 계획 및 에이전트 분배

**[최종 목표 달성 여부]**
*   **진행중:** 데이터의 입력(Input) 표준은 정의되었으나, 이 표준을 실제로 코드로 구현하는 단계가 남아있습니다. (Schema 설계 완료)

**[다음 스텝 결정 근거]**
이 스키마는 개발자가 **'데이터 변환 레이어(Adapter)'**를 구축할 때 필요한 완벽한 계약서(Contract)입니다. 이제 Researcher의 역할은 끝났고, 이 스펙을 코드로 구현하는 것이 최우선 과제입니다.

**[에이전트 분배 및 액션]**
1.  **💻 코다리 (Developer):** 가장 시급합니다. Researcher가 정의한 `Core Data Ingestion Schema V1.0`를 기반으로, 세 가지 이질적 소스를 받아 최종 객체로 변환하는 **'데이터 변환 레이어(Adapter) API 엔드포인트'의 초기 스캐폴딩 및 핵심 로직 구현**에 착수해야 합니다.
2.  **🎨 Designer:** 데이터 구조가 확정되었으므로, 디자인 측면에서 가장 중요한 '리스크 보고서'의 UI/UX 목업을 고도화할 수 있습니다. 특히 `dispute_details[]` 배열이 화면에 어떻게 시각적으로 구현되어야 하는지에 대한 **와이어프레임 세부 가이드**를 추가로 요청하여 개발자에게 전달해야 합니다.

<create_file path="sessions/2026-05-21T00-41/DataIngestionSchema_V1.0.md"># 대한민국 재개발 Core Data Ingestion Schema V1.0
## 개요 및 목적
본 스키마는 네이버 매물, 법제처 API(LawAPI), 정보몽땅 API를 통해 수집되는 모든 이질적인 부동산 데이터를 단일한 '법률 리스크 분석 객체'로 변환하기 위한 최종 청사진입니다. 데이터의 신뢰성 확보와 개발 안정성을 최우선 목표로 합니다.

## 📄 스키마 구조: Core Data Ingestion Schema V1.0
**(아래 내용을 복사하여 사용하세요)**
```json
{
  "report_id": "String (UUID)", // 필수 메타데이터: 보고서 고유 ID
  "data_ingestion_timestamp": "DateTime", // 필수 메타데이터: 데이터 수집 시간 (UTC)
  "property_uuid": "String", // 핵심 식별자: 필지(Lot) 단위 UUID
  "address_standardized": "String", // 표준화된 도로명 주소

  // --- I. 핵심 속성 (Core Property Data) ---
  "land_area_sqm": "Float", 
  "total_area_sqm": "Float", 
  "zoning_status": "Enum (미지정, 구역설정, 조성계획...)", 

  // --- II. 법적 리스크 및 절차 (Legal & Procedural Data) ---
  "initial_legal_risk_score": "Float (0.0 - 10.0)", // 초기 점수 (Impact Red 기준점)
  "legal_conflict_count": "Integer", // 충돌 지점 개수 (가장 중요 KPI)
  "dispute_details": [
    {
      "field": "String", // 충돌이 발생한 필드 이름 (예: '지정 가능 시점')
      "source1_value": "Any", // 소스 1의 값과 데이터 타입 명시
      "source2_value": "Any", // 소스 2의 값과 데이터 타입 명시
      "legal_reasoning": "String" // 충돌을 판단한 법률적 근거 (핵심)
    }
  ],
  "applicable_laws": ["String"], // 적용되는 상위 법규 배열
  "development_timeline": {
    "designation_date": "Date", 
    "plan_completion_date": "Date", 
    "estimated_completion_date": "Date"
  },

  // --- III. 시장/거래 정보 (Market & Transaction Data) ---
  "current_asking_price": "Integer", // 현재 매매가 (네이버 소스 우선)
  "historical_price_avg": ["Float"], 
  "transaction_risk_assessment": "String" // 최종 리스크 판단문
}
```

## 💡 데이터 수집 출처별 가이드라인
*   **네이버 매물:** `current_asking_price`, `historical_price_avg` 등 시장 데이터를 주로 채움. (신뢰도: Low, 변동성: High)
*   **법제처 API:** `applicable_laws[]` 등의 법규 준거를 검증하는 데 활용. (신뢰도: Very High, 변동성: Low)
*   **정보몽땅 API:** `zoning_status`, `development_timeline` 등 절차적 시간을 제공. (신뢰도: Medium, 변동성: Medium)

## 🎯 다음 개발 목표 (Coder에게 전달)
이 스키마를 기준으로 **데이터 통합 게이트웨이(Adapter Layer)**의 초기 구현 및 단위 테스트 케이스 작성에 착수해야 합니다.
</create_file>

📊 평가: 완료 — 핵심 데이터 구조 설계가 완성되었으며, 이는 후속 개발 단계 진입을 위한 완벽한 기반 자료입니다.
📝 다음 단계: 💻 코다리에게 위 스키마를 바탕으로 **데이터 변환 레이어(Adapter)의 초기 백엔드 로직 구현**을 지시하고, 🎨 Designer에게는 이 데이터를 시각화할 와이어프레임 세부 가이드를 요청해야 합니다.

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/sessions/2026-05-21T00-41/DataIngestionSchema_V1.0.md
