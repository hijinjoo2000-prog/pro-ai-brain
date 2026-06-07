# 🔍 Researcher — 리서처님: Developer가 구축한 실시간 API 연동 파이프라인을 검증하기 위해, Master Validation Schema V2.0에 정의된 모든 필드(Mandatory Field)별 데이터 유효성 검사 규칙(Validation Rule Set)과 예외 처리 로직(Error Handling Flow)을 최종적으로 재점검하고 문서화해 주세요. 특히 네이버/법제처 등 외부 소스 간의 불일치 데이터를 어떻게 리스크 점수에 반영할지 가이드라인을 명확히 합니다.

🔍 Researcher: 작업 시작합니다.

CEO 지시사항은 현재 아키텍처의 핵심인 '데이터 신뢰성'과 '리스크 점수 산출의 공신력'을 완성하는 가장 중요한 단계입니다. 코다리 에이전트가 `DataIngestionGateway`라는 훌륭한 파이프라인 구조를 설계했으므로, 이제 이 게이트웨이가 어떤 규칙(Rule)에 따라 데이터를 걸러내고 처리해야 하는지 **규칙서**가 필요합니다.

이는 순수한 데이터 분석 및 도메인 지식 기반의 작업이므로, 저(Researcher)가 주도적으로 수행하고 그 산출물은 개발팀과 비즈니스팀 모두가 참조할 수 있는 최종 가이드라인 형태여야 합니다. 다른 에이전트에게 작업을 분배하기보다는, 제가 종합적인 분석을 통해 **'데이터 검증 및 충돌 해결 규약집(Data Validation & Conflict Resolution Protocol)'**이라는 단일 산출물을 만들어 시스템에 주입하는 것이 가장 가치가 높습니다.

---

### 📘 Master Validation Schema V2.0 기반: 데이터 유효성 검사 및 충돌 해결 프로토콜 (최종 버전)

<create_file path="Master_Validation_Schema_V2.1_Protocol.md">
# 📜 대한민국 재개발 전문 플랫폼: 데이터 무결성 확보 규약집 (V2.1)

**작성 목적:** 네이버, 법제처 API, 정보몽땅 등 이질적인 외부 소스(Heterogeneous Sources)를 통합하는 `DataIngestionGateway`가 데이터를 정규화하고 리스크 점수를 산출하기 위한 최종 유효성 검사 및 충돌 해결 기준을 정의합니다.

**적용 범위:** 모든 신규/개선 매물 데이터의 백엔드 처리 과정 (Pre-Processing & Validation Layer).
***

## Ⅰ. 필드별 필수 값(Mandatory Field) 검증 규칙 세트 (Validation Rule Set)

각 필드의 **데이터 타입(Data Type)**과 **유효성 규칙(Rule)**을 정의합니다. 유효하지 않은 데이터는 즉시 `[Warning]` 또는 `[Error]` 플래그가 지정되어야 합니다.

| 필드명 | 소스 (Source) | 필수 여부 | 데이터 타입 | 검증 규칙 (Validation Rule) | 실패 시 처리 로직 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **① 주소(Address)** | All | Mandatory | String | **[Regex]** 표준 우편번호 형식 및 법정동 단위 검증. (예: `\d{5}`) | `Error` - 매물 데이터 처리 중단. 수작업 개입 필요. |
| **② 필지 코드 (Parcel ID)** | All | Mandatory | String | **[Format]** 고유 식별자 유무 및 형식 일치 여부. | `Warning` - 리스크 점수 산출 시 가중치 하락 (-1점). |
| **③ 법적 상태 코드 (Legal Status)** | InfoMongdang / LawMinistry API | Mandatory | Enum | **[Enum Check]** {사업 진행 중, 구역 지정 완료, 초기 단계, 미지정} 중 하나여야 함. | `Error` - 가장 높은 리스크 점수 부여 (+10점). 처리 불가. |
| **④ 매매가 (Price)** | Naver / User Input | Conditional | Number | **[Range]** 0 초과 값이어야 하며, 단위 통일성 검증 (만 원/원). | `Warning` - 가격 정보의 신뢰도 하락 (-2점). |
| **⑤ 공시지가 (Official Price)** | 법제처 API | Conditional | Number | **[Date Check]** 기준 시점이 현재 날짜로부터 1년 이내여야 함. | `Warning` - 데이터 최신성 부족 (-3점). |
| **⑥ 개발 계획 요약 (Plan Summary)** | All | Optional | Text | **[Length/Keywords]** 최소 50자 이상, '재개발', '정비사업' 키워드 포함 여부. | 없음. 정보의 깊이만 반영. |

***

## Ⅱ. 데이터 충돌 해결 프로토콜 (Conflict Resolution Protocol)

외부 소스 간에 동일 필드의 값이 다를 경우(예: 네이버 매물은 '진행 중', 법제처는 '미지정'), 어느 값을 최종 기준으로 삼을지 결정하는 **계층적 우선순위**가 필요합니다. 이는 리스크 점수 산출의 근거가 됩니다.

### 🥇 충돌 해결 우선순위 (Trust Hierarchy)

1.  **Tier 1: 법률 공공 데이터 (Legal Authority)**
    *   **소스:** 법제처 API, 정보몽땅 API (정부/지자체 공식 발표 자료).
    *   **규칙:** 이 소스가 제공하는 모든 값은 **절대적인 진실(Ground Truth)**로 간주합니다. 다른 소스와 충돌하더라도 Tier 1의 값을 무조건 채택합니다.
2.  **Tier 2: 전문 DB/유료 데이터 (Premium Source)**
    *   **소스:** 자체 구축된 정비사업 전용 데이터베이스, 유료 법률 자문 네트워크 결과.
    *   **규칙:** Tier 1의 정보가 '미지정' 또는 '불확실'할 경우에 한하여 보조 자료로 활용합니다. (Tier 1을 대체하는 절대적인 근거는 될 수 없습니다.)
3.  **Tier 3: 일반 상업 데이터 (General Listing)**
    *   **소스:** 네이버 부동산, 직방 등 일반 매물 플랫폼.
    *   **규칙:** 오직 **참고 자료(Reference Only)**로만 활용합니다. 법적 상태나 진행 상황 판단의 근거가 될 수 없으며, 해당 정보에 대해서는 리스크 점수 산출 시 가장 큰 감점 요인으로 작용합니다.

### ⚖️ 충돌 발생 시 리스크 점수 반영 가이드라인 (Conflict Scoring)

| 충돌 필드 | 예시 (A 소스 vs B 소스) | 우선순위 결정값 | 리스크 점수 영향 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **법적 상태** | Naver: '진행 중' / LawMinistry: '미지정' | `LawMinistry`의 '미지정' 채택. | **-5점 (불일치 Penalty)** + 법률 리스크 점수 최대값 반영. | 일반 매물이 공신력을 떨어뜨림을 명시적으로 표시. |
| **필지 코드** | Naver: A123 / InfoMongdang: A123-B | `InfoMongdang`의 'A123-B' 채택. | 0점 (일치하면 무효화). 다르면 경고 메시지만 출력. | 필지 코드는 고유성을 최우선으로 함. |
| **매매가** | Naver: 5억 / User Input: 4.8억 | `Naver` 값 채택 (최신성/공개 가격 우선). | 없음. 금액 차이는 단순 비교 정보로 제공. | 법적 리스크와 무관한 경제적 변수는 충돌해도 큰 패널티 부여하지 않음. |

***

## Ⅲ. 시스템 에러 및 예외 처리 플로우 (Error Handling Flow)

| 발생 유형 | 원인 (Cause) | 시스템 액션 (System Action) | 사용자(중개사)에게 노출 방식 |
| :--- | :--- | :--- | :--- |
| **데이터 누락 (Missing Data)** | 필수 필드(예: 주소, 법적 상태)가 공백일 경우. | `[Warning]` 플래그 지정 및 해당 필드는 리스크 계산에서 제외함. | "🚨 경고: [필드명] 정보가 누락되어 관련 점수 산출에 어려움이 있습니다." (노란색 경고창) |
| **데이터 오류 (Invalid Data)** | Regex 불일치, Enum 범위 초과 등 규칙 위반 시. | `[Error]` 플래그 지정 및 해당 매물은 임시 대기(Pending Review) 처리됨. | "❌ 치명적 오류: [필드명]의 형식이 잘못되었습니다. 데이터 수정이 필요합니다." (빨간색 에러 메시지) |
| **소스 충돌 (Conflict)** | Tier 1과 Tier 3 간 법적 상태 불일치 시. | `[Warning]` 플래그 지정 및 내부 로직에 따라 점수 조정(위의 가이드라인 적용). | "⚠️ 참고: 본 매물은 공공 기록과 상업 정보가 충돌합니다. **법제처 기준**으로 리스크를 산정했습니다." (주황색 주의 메시지) |

</create_file>

### 📝 분석 요약 및 다음 단계 계획

1.  **산출물의 가치:** 이 `Master_Validation_Schema_V2.1_Protocol.md`는 단순히 문서를 넘어서, 코다리 에이전트가 구축한 `DataIngestionGateway`의 **운영 매뉴얼이자 핵심 로직 정의서** 역할을 합니다.
2.  **개발 연관성:** 개발자는 이 규칙집을 기반으로 실제 데이터 검증(Validation) 및 충돌 해결(Conflict Resolution) 코드를 작성해야 합니다.
3.  **다음 단계:** 이제 '규칙'이 확정되었으므로, 이를 실제로 구현할 차례입니다.

---

📊 평가: 완료 — CEO 지시사항인 필드별 유효성 검사 규칙과 외부 소스 간 불일치 데이터를 리스크 점수에 반영하는 가이드라인을 체계적인 프로토콜 형태로 완성하여 다음 개발 단계의 설계도를 제시했습니다.
📝 다음 단계: 코다리 에이전트에게 이 **'규약집(Master_Validation_Schema_V2.1_Protocol.md)'**를 최우선 기준으로 삼아, `DataIngestionGateway` 내부의 실제 검증 로직(`Validator Module`)을 구현하도록 지시해야 합니다.

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/Master_Validation_Schema_V2.1_Protocol.md
