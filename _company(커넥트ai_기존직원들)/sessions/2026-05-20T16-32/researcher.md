# 🔍 Researcher — Researcher: Developer가 코딩할 핵심 '법적 충돌 자동 진단 로직'의 예시 케이스 5개를 추가적으로 정의해 주십시오. 특히, 데이터 출처(네이버 vs 법제처) 간에 정보가 상충하는 상황(예: 매물 등록일과 구역 지정 가능 시점의 불일치 등)을 명확히 설명하고, 이 경우 어떤 필드가 'Conflict_Flag'를 켜야 하는지 대한 상세한 규칙 목록을 제공하여 Developer의 코딩 가이드를 완성해 주세요.

🔍 Researcher: 작업 시작합니다.

요청하신 대로 '법적 충돌 자동 진단 로직'의 가이드라인을 완성하기 위해, 실제 데이터 출처 간에 발생할 수 있는 고유하고 전문적인 리스크 케이스 5가지와 이에 따른 상세 규칙 목록을 정의했습니다. 이 내용은 개발자가 코딩할 때 단순한 논리 구조를 넘어 **플랫폼만이 발견할 수 있는 '법률적 불확실성'**이라는 가치를 담보하는 핵심 로직이 될 것입니다.

---

## 📜 재개발 정보 통합 게이트웨이: 법적 충돌 진단 규칙서 V1.1
**(Developer 코딩 가이드용)**

### I. 충돌 케이스 상세 정의 (5가지 Critical Risk Scenarios)

본 섹션의 각 케이스는 데이터 소스 간의 **논리적, 시간적, 범위적 불일치**를 의미합니다. 이 중 하나라도 감지되면 즉시 `Conflict_Flag`가 활성화되어야 합니다.

#### ⚠️ Case 1: 시점 오류 충돌 (Listing Date vs. Legal Readiness)
*   **상황:** 매물 정보(네이버 등)에 등록된 '매물 등록일'이 법적 절차 진행의 최소 시간 간격이나 필수 사전 동의를 얻을 수 있는 공식적인 지자체 공지 시점보다 **선행**하는 경우. (예: 아직 구역 지정 자체가 확정되지 않았는데, 매물이 "즉시 거래 가능"으로 광고됨).
*   **충돌 포인트:** 매물 정보가 법적 현실을 반영하지 못하고 시간적으로 앞서나가는 위험(Misleading Timing Risk).
*   **핵심 비교 필드:** `Matter.ListingDate` vs. `LawStatus.MinDesignationDate`

#### ⚠️ Case 2: 용도 지역 및 개발 목적 불일치 충돌 (Scope Conflict)
*   **상황:** 정보몽땅에서 해당 구역이 '주거지역 A'로 분류되어 있고, 법제처 API를 통해 '단독 주택 위주의 재개발 가능 구역'으로 확인되었음에도 불구하고, 네이버 매물 설명에만 '오피스텔/상가 혼합 용도'라는 내용이 강조되는 경우.
*   **충돌 포인트:** 공식적인 법적 분류(Law)와 개별 매물의 실제 사용 계획(Usage) 간의 구조적 모순. 개발 목적 자체가 상충하는 리스크.
*   **핵심 비교 필드:** `Matter.PrimaryUse` vs. `InfoMongttang.DesignationType`

#### ⚠️ Case 3: 법규 우선순위 충돌 (Hierarchy Conflict)
*   **상황:** 국토계획법(최상위 법규) 상 해당 지역이 '보전녹지지역'으로 지정되어 개발 행위 자체가 극도로 제한됨에도 불구하고, 개별 매물 필지에 대한 *개별 건축 심의 통과 가능성* 등의 정보가 존재하거나 광고되는 경우.
*   **충돌 포인트:** 최상위 법규(Law)가 하위 단계의 특수 권한 주장보다 우선해야 함을 위반하는 논리적 충돌. (가장 높은 레벨의 리스크).
*   **핵심 비교 필드:** `NationalPlan.Designation` vs. `Matter.PotentialApprovalStatus`

#### ⚠️ Case 4: 물리적 경계 불일치 충돌 (Boundary Mismatch)
*   **상황:** 등기부등본(네이버 연동의 근거가 되는 문서) 상의 필지 면적이 명확함에도 불구하고, 법제처 API를 통해 조회되는 '정비 계획상 건축 허용 최대 범위'와 해당 경계가 1m 이상 불일치하는 경우.
*   **충돌 포인트:** 소유권 기록(Legal Ownership)과 공적 개발 계획(Public Plan) 간의 물리적/법률적 오차 발생. (실제 매매 불가 리스크).
*   **핵심 비교 필드:** `Matter.RegisteredBoundary` vs. `LawStatus.PlanLimitArea`

#### ⚠️ Case 5: 정보 누락으로 인한 불확실성 충돌 (Data Gap Conflict)
*   **상황:** 세 소스(네이버, 법제처, 정보몽땅) 모두에서 매물의 **핵심 필수 필드 중 하나가 완전히 비어있거나(Null)**, 또는 조회 시마다 값이 상이하여 데이터의 신뢰도를 판별할 수 없는 경우. (예: 전유건물 면적은 있지만, 건물의 실제 건축 연도가 누락되어 리모델링 가능 여부를 판단할 수 없음).
*   **충돌 포인트:** 정보가 부족해서 발생하는 '불확실성(Uncertainty)' 그 자체가 가장 큰 리스크임.
*   **핵심 비교 필드:** 모든 소스의 `CoreDataSchema`의 필수 필드 (예: `ConstructionYear`, `OwnershipType`) 존재 여부 및 값 일치 여부

### II. 개발자용 Conflict_Flag 규칙 목록 (Coding Rulebook)

| 충돌 유형 | 감지 조건 (IF Condition) | 체크해야 할 데이터 쌍 | Flagging Field | 리스크 설명 (Report Text Snippet) |
| :---: | :--- | :--- | :---: | :--- |
| **시간성 불일치** | `Matter.ListingDate` < `LawStatus.MinDesignationDate` $\text{OR}$ `Matter.ListingDate` < $T_{\text{minimum legal lead time}}$ | 매물 등록일 vs 법적 최소 준비 기간 | `Conflict_Time` (High) | **경고:** 해당 매물의 정보가 공식적인 재개발 절차 시작 시점보다 앞서 노출된 것으로, 법률적 검토가 선행되어야 합니다. |
| **용도 불일치** | $\text{Mismatch}(\text{Matter.PrimaryUse}, \text{InfoMongttang.DesignationType})$ AND $\text{Difference} > 0$ | 매물 사용 용도 vs 공공 구역 지정 용도 | `Conflict_Scope` (Critical) | **경고:** 등록된 용도가 해당 지역의 법적 기본 계획과 상충합니다. 개발 목적 변경 가능 여부를 재확인해야 합니다. |
| **법규 위반** | $\text{NationalPlan.Designation}$ = '보전 녹지' AND `Matter.PotentialApprovalStatus` = '허가 예정' | 최고 법규 지정 vs 개별 허가 가능성 주장 | `Conflict_LawLevel` (Critical) | **경고:** 해당 매물의 개발 행위는 상위법(국토계획법 등)의 보전 원칙에 위배될 소지가 높습니다. |
| **물리적 경계** | $|\text{Matter.RegisteredBoundary} - \text{LawStatus.PlanLimitArea}| > 1\text{m}$ | 등기부상 면적 vs 계획 허용 범위 | `Conflict_Boundary` (High) | **경고:** 매물의 물리적 경계가 공공 개발 계획의 최대 인정 범위를 초과하거나 미달합니다. 실질적인 건축 가능 면적에 제한이 있습니다. |
| **정보 불확실성** | $\text{Null}(\text{CoreDataSchema}_{\text{Mandatory Field}})$ OR $\text{Inconsistent}(\text{Source}_1, \text{Source}_2)$ (for mandatory fields) | 필수 핵심 필드 셋의 누락 또는 값 상이 | `Conflict_Gap` (Medium/High) | **주의:** 핵심 정보(예: 건물의 정확한 건축 연도)가 여러 출처에서 불명확하거나 누락되어, 리모델링 가능성 진단에 어려움이 있습니다. |

---
📊 평가: 완료 — 요청된 모든 조건과 가이드라인을 포함하여 개발 로직의 완성도를 높일 수 있는 구체적인 산출물을 정의했습니다.
📝 다음 단계: 💻 코다리에게 위의 **'Conflict_Flag 규칙 목록 및 상세 케이스'**를 기반으로 `CoreDataProcessor.ts` 파일 내의 스코어링 함수를 구현하도록 지시하고, 테스트 시나리오 실행을 요청해야 합니다.
