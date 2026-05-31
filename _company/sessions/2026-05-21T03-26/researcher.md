# 🔍 Researcher — 코다리 에이전트가 개발할 '법률 리스크 진단 모듈'을 위한 모든 외부 데이터(네이버 매물, 법제처 API, 정보몽땅 API)의 최종 통합 데이터 스키마 (Master Validation Schema V1.0)를 작성하십시오. 이 스키마는 모든 필수 지표와 필드를 포함하며, 코다리가 모킹(Mocking) 데이터를 생성할 때 따라야 할 단 하나의 '진실의 근거'가 되어야 합니다.

🔍 Researcher: 작업 시작합니다.

CEO의 지시에 따라 '법률 리스크 진단 모듈'을 위한 최종 통합 데이터 스키마(Master Validation Schema V1.0)를 작성했습니다. 이 스키마는 단순히 데이터를 나열하는 것이 아니라, **데이터 소스 간의 충돌 여부와 법적 불확실성**을 명시적으로 포함하도록 설계되었습니다.

이 스키마는 코다리 에이전트가 Mocking 데이터를 생성할 때 반드시 따라야 할 단 하나의 '진실의 근거'이며, 플랫폼의 핵심 가치인 **'정보 불일치에 대한 보험(Insurance against Information Discrepancy)'**을 데이터 구조 자체에 녹여냈습니다.

---

# 🏛️ Master Validation Schema V1.0: 재개발/재건축 매물 통합 진단 스키마

## 📋 개요 및 목적
*   **버전:** V1.0 (최종)
*   **목적:** 네이버, 법제처 API, 정보몽땅 API 등 이질적인 외부 데이터를 단일화하고, 데이터 출처 간의 논리적/법률적 충돌을 구조적으로 진단하여 '리스크 점수' 산출의 기반을 마련한다.
*   **핵심 원칙:** 모든 필수 필드는 **데이터 소스 식별자(Source ID)**를 포함해야 하며, 값에 대한 신뢰도(Confidence Score)가 명시되어야 한다.

## 🧩 스키마 구조 (Data Object Blueprint)

| 카테고리 | 필드명 (Field Name) | 데이터 타입 | 설명 및 규칙 (Mocking 시 적용) | 필수 소스 ID | 비고 / 리스크 관련성 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **[A] 기본 식별자 (Identifiers)** | `Property_ID` | String | 매물 고유 식별 번호 (UUID) | - | 1차 키. 내부 관리용. |
| | `Lot_Code` | String | 지번 기반 필지 코드 (예: 123-45-67) | Naver, 법제처, 정보몽땅 | **가장 중요한 검색 식별자.** |
| | `Address_Full` | String | 표준화된 주소명 | Naver | 사용자에게 노출되는 공식 주소. |
| | `Area_Total_㎡` | Float | 총 면적 (제곱미터) | Naver | 물리적 크기 정보. |
| **[B] 매물 기본 정보 (Listing Details)** | `Listing_Price` | Integer | 현재 등록된 매매 희망 가격 (원) | Naver | 판매자 제시 가격. |
| | `Sale_Type` | String | 거래 유형 (예: 실거주, 투자 목적, 상가 포함 여부) | Naver | 공인중개사의 주관적 판단 반영. |
| | `Listing_Date` | Date | 네이버에 등록된 날짜 | Naver | 시장 진입 시점 파악용. |
| **[C] 법률 및 절차 정보 (Legal Status - The Truth)** | `Designated_Status` | String | 현행 지정 상태 (예: 구역 지정, 추진 위원회 설립) | InfoMongttang | **(기준 값 1)** 재개발 단계의 공식 명칭. |
| | `Current_Procedure_Code` | String | 법적 절차 코드 (예: 정비구역 지정 전/후) | LawMinistryAPI | **(기준 값 2)** 법제처 API 기반의 최신 규정 코딩화. |
| | `Legal_Gap_Flag` | Boolean | 상위법과 충돌하는 법률적 모호성 존재 여부 (Y/N) | *Derived* | **핵심 리스크 지표.** True일 경우, 상세 주석 필수. |
| | `Required_Action` | String | 매도자가 취해야 할 다음 법적 액션 제안 (예: 토지 사용권 확보) | *Derived* | 서비스의 컨설팅 가치 제공 필드. |
| **[D] 데이터 출처별 원본 값 (Source Raw Data)** | `Naver_Raw_Text` | Text | 네이버 매물 설명 전문 (전체 텍스트) | Naver | **(감정 분석 대상)** 중개사가 작성한 감성/의도 파악. |
| | `L_API_Status_Code` | String | 법제처 API가 반환한 원본 상태 코드 (예: L04-A) | LawMinistryAPI | 데이터 출처 증명용 필드. |
| | `IM_Progress_Detail` | Text | 정보몽땅에서 제공하는 구역별 상세 설명 전문 | InfoMongttang | **(배경지식)** 법적 맥락을 파악할 근거 자료. |
| **[E] 리스크 진단 및 점수화 (Risk Scoring & Output)** | `Conflict_Flag` | Boolean | 데이터 출처 간의 상충되는 정보 존재 여부 (Y/N) | *Derived* | **최고 중요 필드.** 예: Naver 등록일 > 법적 가능 시점. |
| | `Confidence_Score` | Float | 이 매물에 대한 전체 데이터 신뢰도 점수 (0~100) | *Derived* | 모든 필드를 통합하여 계산된 최종 진단 지표. |
| | `Legal_Risk_Category` | String | 분류된 리스크 카테고리 (예: 🟡 절차적 위험, 🔴 소유권 불확실성, 🟢 안전함) | *Derived* | UI 색상 및 경고 문구와 연동되는 값. |
| | `Detailed_Conflict_Reason` | Text | Conflict_Flag가 True일 경우, 충돌의 구체적인 이유 (필수 기재) | *Derived* | **[예시]** "정보몽땅은 '추진 단계'이나, 법제처는 해당 지역에 대한 '도시계획 변경 승인' 기록이 없음." |

---

## 💡 코다리 에이전트를 위한 핵심 로직 가이드 (Mocking Logic)

1.  **Conflict_Flag True 조건:**
    *   `Listing_Date`와 `Current_Procedure_Code`가 법적으로 불가능한 시간 순서일 때.
    *   `Designated_Status`와 `L_API_Status_Code`의 의미론적 해석이 충돌할 때 (예: 하나는 '법률 검토 중'인데, 다른 것은 이미 '사업 시행 단계'라고 주장할 때).
2.  **Confidence_Score 산출:**
    *   (Naver 데이터가 최신 정보일 경우 +30점) * (LawMinistryAPI의 공식 코드가 존재할 경우 +40점) * (InfoMongttang이 구역 지정 기록을 제공할 경우 +30점). **누락된 필수 소스 ID당 15점 감점.**
3.  **Level 1 유료 데이터 모듈 적용:** 이 스키마의 `Conflict_Flag` 및 `Detailed_Conflict_Reason` 필드를 채우는 행위 자체가 Level 1 '법률 리스크 보고서'가 됩니다.

---
📊 평가: 완료 — CEO 지시에 따라 모든 외부 데이터를 통합하고, 플랫폼의 핵심 가치인 '충돌 진단'을 구조화한 마스터 스키마를 완성했습니다.
📝 다음 단계: 코다리 에이전트에게 이 Master Validation Schema V1.0을 기반으로 Mocking 데이터 생성 및 ETL 파이프라인 테스트 시나리오(E2E Test Suite)를 작성하도록 지시해야 합니다.
