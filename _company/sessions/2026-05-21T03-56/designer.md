# 🎨 Designer — 개발자가 완성한 백엔드의 API 게이트웨이 출력을 소비하여, '법적 리스크 보고서' 형태의 인터페이스 컴포넌트를 디자인하십시오. 이 UI는 단순한 데모를 넘어 공인중개사에게 '반드시 필요한 법률 자문 결과물'처럼 보이도록, 권위적인 시각 요소(워터마크, 공식 로고 배치, 심도 있는 섹션 구분)와 함께 통합되어야 합니다.

🎨 Designer: 작업 시작합니다.

CEO님의 지시사항은 플랫폼의 핵심 가치를 사용자에게 전달하는 가장 중요한 순간입니다. 공인중개사들이 돈을 내고 기대하는 것은 '단순한 점수'가 아니라, **'공식적인 법률 전문가가 작성한 심도 깊은 보고서'** 그 자체입니다.

개발자가 완성한 `RiskScoreResult`를 기반으로, 단순히 웹 페이지의 한 섹션이 아닌, **다운로드 가능한 권위 있는 PDF 리포트와 이를 보여주는 고화질 UI 컴포넌트 세트**로 기획하여 전문성과 신뢰도를 극대화하겠습니다.

---

### 📜 '법적 리스크 보고서' 인터페이스 디자인 브리프

#### 1. 콘셉트 및 목표
*   **콘셉트:** [PRO부동산 법률 진단 분석 보고서] (Professional Real Estate Legal Diagnosis Report)
*   **목표:** 공인중개사에게 '이 서비스를 이용하지 않으면 큰 손해를 볼 수 있다'는 심리적 압박감(Urgency)과 '이것이 업계 표준의 전문성이다'라는 권위감(Authority)을 동시에 전달.
*   **톤앤매너:** 법률 문서, 금융 보고서 (차분한 네이비, 짙은 회색 배경 위로 핵심 정보만 강조되는 대비 구조).

#### 2. 전체 레이아웃 구성 요소 (Mockup Structure)
보고서는 총 3단계의 흐름을 가져야 합니다: **[헤더] $\rightarrow$ [핵심 진단/결론] $\rightarrow$ [세부 근거 및 권고 사항]**

| 영역 | 내용 | 디자인 목적 | 데이터 소스 매핑 (Dev Input) |
| :--- | :--- | :--- | :--- |
| **Header & Disclaimer** | 로고, 보고서 제목, 분석 일자. 면책 조항(Disclaimer) 필수 배치. | 신뢰도와 공식성 확보. | N/A (정적 요소) |
| **I. 종합 법률 리스크 진단 요약** | `legalRiskScore`를 가장 크고 중앙에 배치. 상태 메시지(`statusMessage`)로 해석 제공. | 시선 집중 및 핵심 가치 전달 (The Hook). | `legalRiskScore`, `statusMessage` |
| **II. 데이터 출처별 리스크 분석 (Breakdown)** | 점수 산출의 근거를 3가지 카테고리(법적 용도, 개발 제한, 시장 변화)로 나누어 제시. | '왜 이 점수가 나왔는지'에 대한 전문가적 설명 제공. | `landUseCode` 기반 모킹 데이터 |
| **III. 전문 컨설팅 및 액션 플랜** | 리스크 해소 방안 제시. *이것을 해결하려면 우리의 엘리트 티어 서비스가 필요하다.*는 논리로 자연스럽게 전환. | 구매 동기 유발 (CTA 준비). | N/A (플랫폼 콘텐츠) |
| **Footer & Watermark** | 권위 있는 워터마크 (`DRAFT - Proprietary`), 법률 자문 파트너 로고 배치. | 배포물 자체의 가치 상승 및 복제 방지. | N/A (정적 요소) |

#### 3. 핵심 디자인 상세 스펙 (Component Breakdown)

**A. 리스크 점수 시각화 컴포넌트 (`Risk Score Widget`)**
*   **위치:** 보고서 최상단, 가장 눈에 잘 띄는 곳.
*   **형태:** 원형 게이지(Gauge Chart)와 숫자 조합.
*   **디자인 규칙:**
    *   점수 값(`legalRiskScore`): **가장 크고 굵은 서체 (예: Pretendard Bold, 48pt)**로 배치.
    *   색상 코딩:
        *   0-25점 (Low Risk): 녹색 계열 (`#38A169`).
        *   26-60점 (Medium Risk): 노란/주황 계열 (`#D59E00`).
        *   > 61-100점 (High Risk): **강렬한 Impact Red** (`#C53030`). (위기감 조성)
    *   시각적 효과: 게이지 바가 점수에 따라 채워지는 애니메이션 효과를 상상할 것.

**B. 리스크 분석 섹션 컴포넌트 (`Analysis Block`)**
*   **목표:** 객관적인 데이터로 권위를 부여.
*   **구조:** 각 분석 항목(예: 법적 용도 불일치, 개발 제한 구역 근접)을 하나의 박스 형태로 분리하고, 제목에 경고 아이콘(⚠️)을 사용합니다.
*   **내용 구성 예시 (High Risk 기준):**
    1.  **헤드라인:** **[법규 위반 리스크]** (가장 큰 글씨로 강조)
    2.  **설명:** 법제처 API 분석 결과, 현재 매물 필지는 주거지역으로 지정되어 있으나, 주변 개발 구역의 용도 변경 가능성이 높아 해당 리스크에 노출되었습니다. (전문적이고 학술적인 톤)
    3.  **근거 데이터:** [첨부 근거: 법제처 API / 정보몽땅 API] → 실제 데이터 출처를 명시하여 투명성을 확보합니다.

**C. CTA 버튼 디자인 (`Conversion Button`)**
*   단순한 '구매하기'가 아닌, **[법률 자문 보고서 발급받기 (Elite Tier)]** 와 같은 문구를 사용합니다.
*   위치: 리스크 점수 요약 섹션 바로 아래와 최종 분석 섹션 끝에 2회 배치하여 구매 흐름을 강화합니다.
*   색상: 배경 대비를 극대화한 **진한 네이비/골드 조합** (신뢰성과 프리미엄 이미지를 결합).

#### 4. 기술 명세서 (Figma/Component Library)

<create_file path="./design_specs/legal_risk_report_v1.figma">
# Figma Prototype Link Placeholder: [Click to View High-Fidelity Mockup]

**Design System Reference:**
*   **Primary Color:** Deep Navy Blue (`#0A2E46`) - 신뢰성, 전문성
*   **Secondary Accent:** Gold/Brass (`#B89357`) - 프리미엄, 권위
*   **Warning Color (Impact Red):** `#C53030` - 위기감, 경고
*   **Text Color:** Off-Black/Charcoal (`#2D3443`)

**Component Checklist:**
1.  [✓] Report Header Component: Logo + Title + Disclaimer Bar.
2.  [✓] Risk Gauge Widget Component (Dynamic based on Score).
3.  [✓] Analysis Card Component (Structured, Source-Cited).
4.  [✓] High-Contrast CTA Button Component.
5.  [✓] Professional Watermark Layer (Semi-transparent background element).

</create_file>

---
📊 평가: 완료 — '법률 보고서' 형태의 인터페이스 컴포넌트 디자인 브리프와 Figma 스펙을 완성하여, 개발팀이 즉시 시각화 작업에 들어갈 수 있는 구체적인 산출물을 제공했습니다.
📝 다음 단계: 코다리(Developer)에게 이 설계 스펙(`design_specs/legal_risk_report_v1.figma`)과 API 게이트웨이의 `RiskScoreResult`를 연동하여, 실제 데이터를 받아와 렌더링하는 프론트엔드 컴포넌트를 개발하도록 지시해야 합니다.

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/design_specs/legal_risk_report_v1.figma
