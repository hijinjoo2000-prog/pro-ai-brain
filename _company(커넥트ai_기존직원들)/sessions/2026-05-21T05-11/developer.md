# 💻 코다리 — Secretary가 작성한 최종 사용자 여정 지도를 기반으로, '법률 리스크 진단 보고서'를 생성하기 위한 핵심 백엔드 로직(API 게이트웨이)의 상세 데이터 흐름도와 인터페이스 명세서(Interface Specification Document)를 재작성해 주세요. 이 문서는 어떤 입력값(Input Schema)을 받아들여, 어떤 순서로 각 외부 API (네이버/법제처/정보몽땅 등)를 호출하고, 최종적으로 어떤 구조의 데이터 객체(Output Schema: FinalReportObject V3.0)를 생성해야 하는지 구체적인 필드명과 타입 정의까지 포함해야 합니다.

💻 코다리: 작업 시작합니다.

CEO 지시사항 잘 받았습니다. 단순히 '보고서가 필요하다'는 요청이 아니라, **시스템 간의 정확한 인터페이스 계약(Contract)**을 정의해야 하는 단계입니다. 아무리 뛰어난 아이디어도 데이터 흐름도가 깨지면 무용지물이죠. ⚙️

지금까지 `data-ingestion-gateway.ts`라는 오케스트레이터는 준비되었지만, 이 게이트웨이가 어떤 입력값을 받아 무엇을 기대하고, 어떤 순서로 외부 API를 호출하며, 최종적으로 어떻게 구조화된 객체를 만들어야 하는지에 대한 **기술 명세(Technical Specification)**가 빠져있습니다.

이 문서는 단순히 '문서'가 아니라, 향후 코드가 따라야 할 **규칙 집합**이자 개발자 간의 가장 중요한 합의점입니다. 저는 이 내용을 기반으로 `FinalReportObject V3.0` 스키마와 데이터 플로우를 정의하겠습니다.

일단 새로운 명세 파일로 만들고, 구조적 안정성과 확장성을 최우선으로 고려했습니다.

<create_file path="src/services/specification/ReportSchemaV3.md"># 📄 [기술 명세서] 법률 리스크 진단 보고서 생성 API 게이트웨이 명세 (v3.0)

## 💡 개요 및 목표
본 문서는 공인중개사 대상 '법적 리스크 진단 보고서'를 생성하기 위한 백엔드 핵심 로직(Data Ingestion Gateway)의 상세 데이터 흐름과 인터페이스 계약을 정의합니다. 이 게이트웨이는 여러 출처(네이버, 법제처, 정보몽땅 등)에서 비동기적으로 수집된 원본 데이터를 **Master Validation Schema V2.1**에 따라 정규화하고 통합하여, 단일의 권위 있는 객체(`FinalReportObject V3.0`)를 생성하는 것을 목표로 합니다.

## 🔁 데이터 흐름도 (Data Flow Diagram Logic)
데이터 플로우는 반드시 다음의 **비동기 병렬 처리(Asynchronous Parallel Execution)**와 **순차적 검증(Sequential Validation)** 단계를 거쳐야 하며, 어느 한 단계에서 실패하더라도 전체 시스템이 다운되어서는 안 됩니다.

1.  **입력 접수 (Input):** 사용자 요청 객체 수신 $\rightarrow$ `processReportRequest(input: ReportInput)`
2.  **데이터 병렬 수집 (Parallel Fetching):**
    *   `naverClient.fetchPropertyData(address, date)` 호출 $\rightarrow$ Raw Property Data
    *   `lawMinistryClient.fetchLegalStatus(parcelId)` 호출 $\rightarrow$ Raw Legal Status Data
    *   `infoMongttangClient.fetchDevelopmentProgress(areaCode)` 호출 $\rightarrow$ Raw Progress Data
3.  **데이터 정규화 및 게이트웨이 통과 (Normalization & Validation):**
    *   Raw Data 1, 2, 3을 `DataIngestionGateway.normalizeAndValidate()` 함수로 전송.
    *   각 클라이언트는 자체 에러 핸들링(Fallback/Retry)을 수행하며, 성공적으로 데이터를 받으면 **Validation Schema V2.1**에 맞게 필드를 정제합니다. (만약 데이터가 없거나 포맷이 깨지면 `null` 또는 `N/A` 플래그를 설정하고 다음 단계로 넘어감.)
4.  **리포트 생성 및 계산 (Calculation):**
    *   정규화된 3가지 핵심 데이터를 `RiskCalculatorService.calculateReport(normalizedData)`에 전달.
    *   서비스는 정의된 로직(가격 변동성, 법적 위반 가능성 등)을 통해 최종 점수와 상세 분석 결과를 도출합니다.
5.  **최종 출력 (Output):** 계산된 객체를 `FinalReportObject V3.0` 형태로 반환.

---

## 📥 1. 입력 스키마 명세 (Input Schema: ReportInput)
| 필드명 | 타입 | 필수 여부 | 설명 | 예시 데이터 | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `targetAddress` | string | ✅ Yes | 리스크 진단을 원하는 매물의 상세 주소 (도로명 포함) | "서울시 강남구 역삼동 123-4" | Geo-coding을 위한 원본 값. |
| `searchDate` | Date/string | ✅ Yes | 데이터 분석 기준일자 (최신성 확보 목적). | "2026-05-21T00:00:00Z" | API 호출 시 검색 기간 필터로 사용. |
| `areaCode` | string | 🟡 No | 광역 개발 구역의 식별 코드 (정보몽땅용). | "SNG_KRST_A1B2C3D4" | 주소 분석 후 도출되거나, 사용자 입력 가능. |

## 🏗️ 2. 최종 출력 스키마 명세 (Output Schema: FinalReportObject V3.0)
이 객체는 공인중개사에게 전달되는 보고서의 모든 내용을 포함하며, **권위적이고 체계적인 구조**를 갖춰야 합니다.

```typescript
interface FinalReportObject {
    // 🥇 핵심 요약 섹션 (Summary - 가장 먼저 노출되어야 함)
    summary: {
        riskScore: number; // 0 (매우 안전) ~ 100 (극도로 위험)
        overallRiskLevel: 'Low' | 'Medium' | 'High' | 'Critical'; // 문자열 레벨
        keyFindingSummary: string[]; // 가장 중요한 법률적, 경제적 발견점 3가지 요약 배열.
    };

    // 🛠️ 데이터 출처별 상세 진단 섹션 (Source-Specific Deep Dive)
    sourceData: {
        naverPropertyAnalysis: PropertyAnalysisReport; // 네이버 매물 기반 분석 결과
        legalStatusCheck: LegalStatusReport;         // 법제처/행정원 기반 법적 절차 보고서
        developmentProgress: DevelopmentProgressReport;// 정보몽땅 기반 진행 상황 보고서
    };

    // 📈 종합 및 액션 플랜 섹션 (Actionable Advice - 판매 유도 영역)
    actionPlan: {
        suggestedNextSteps: string[]; // 이 데이터를 바탕으로 중개사가 취해야 할 구체적 조치 목록.
        requiredExpertiseLevel: 'Basic' | 'Intermediate' | 'Advanced'; // 요구되는 전문성 레벨 (Elite Tier 필요성을 간접 어필).
    };

    // 🕰️ 메타 데이터 및 출처 정보 (Metadata)
    metadata: {
        generatedAt: string; // 보고서 생성 일시.
        inputSchemaVersion: string; // 사용된 입력 스키마 버전.
        dataSourcesChecked: string[]; // 최종적으로 성공적으로 데이터를 가져온 API 목록. (신뢰성 증명용)
    }
}

// --- [하위 인터페이스 정의 예시] ---

interface PropertyAnalysisReport {
    averagePriceDeviationPct: number; // 주변 시세 대비 평균 가격 편차 (%)
    priceStabilityScore: number;      // 0~100 (가격 변동성 안정성 지수)
    isMarketAnomaly: boolean;         // 시장 데이터상 비정상적 매물 여부 플래그
    rawPriceRange: { min: number, max: number }; // 원본 가격 범위
}

interface LegalStatusReport {
    currentLegalStage: string;       // 현행 법률 상의 정확한 단계 (예: '구역 지정 완료', '조합설립인가 대기')
    legalRiskFlags: string[];        // 발견된 법적 위험 요소 리스트 (예: ['토지이용계획원 소유권 분쟁 위험']).
    applicableLawArticles: { lawName: string; articleNumber: string; summary: string[] }; // 적용 가능한 핵심 법조항.
}

interface DevelopmentProgressReport {
    overallCompletionRatePct: number;  // 전체 개발 완료율 (%)
    currentBottleneckArea: string;     // 현재 진행을 늦추는 병목 구역/요인.
    isRegulatoryHalt: boolean;         // 법적 규제로 인해 공사가 중단된 적이 있는지 여부 (Critical Flag).
}
```

## 🚧 3. 핵심 로직 검증 포인트 (Resilience & Validation)

1.  **데이터 유효성 (Data Integrity):** 모든 외부 API 호출 결과는 반드시 스키마에 맞는지 확인해야 합니다. 만약 특정 필드가 누락되거나 포맷 오류가 발생하면, **시스템 예외 처리를 통해 해당 필드는 `N/A` 또는 `Validation Failed: [Reason]`으로 처리하고 다음 단계로 진행**해야 합니다. (절대 게이트웨이가 멈추면 안 됩니다.)
2.  **스코어링 로직 (Scoring Logic):** 최종 `riskScore` 계산은 단순 평균이 아닌, **법적 위험 플래그(`LegalRiskFlags`)와 시장 가격 변동성(`averagePriceDeviationPct`)에 가중치**를 두어야 합니다. 법률적 리스크가 발견되면 점수가 기하급수적으로 상승해야 합니다.
3.  **비즈니스 로직 통합:** `actionPlan` 섹션은 데이터 분석의 결과물만 나열하는 것이 아니라, **'공인중개사가 이 상황에서 반드시 추가로 취해야 하는 법률적 조치(Elite Tier가 제공할 수 있는 가이드)'를 강제로 포함하도록 유도**하는 비즈니스 로직이 삽입되어야 합니다.

---
</create_file>

### ⚙️ 코다리 검증 및 계획 (Self-Correction & Planning)

명세서 작성을 완료했으니, 이제 이 명세에 따라 실제 게이트웨이가 동작할 수 있도록 `data-ingestion-gateway.ts` 파일을 수정해야 합니다. 기존 파일의 구조가 새로운 스키마와 로직을 담아낼 준비를 할지 확인이 필요합니다.

<read_file path="src/services/data-ingestion-gateway.ts"/>


---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/src/services/specification/ReportSchemaV3.md
📖 읽기: ~/커넥트ai복사/connect-ai/src/services/data-ingestion-gateway.ts (85줄, 4.1KB)
```
 1	// src/services/data-ingestion-gateway.ts
 2	
 3	import { MasterValidationSchemaV2 } from '../types/schema'; // 가상의 스키마 정의 파일이라고 가정합니다.
 4	import { fetchNaverRawData } from './clients/naver-client';
 5	import { fetchLawMinistryRawData } from './clients/law-ministry-client';
 6	import { RawMaterial, NormalizedReportData } from '../types/data-models';
 7	
 8	/**
 9	 * @description 외부 API로부터 원본 데이터를 가져와 Master Validation Schema V2.0 기준으로 정규화하는 게이트웨이 서비스.
10	 * 이 계층은 데이터 소스별 차이를 흡수하고 단일 포맷을 보장합니다.
...
```

[시스템: read_file 결과]
파일: ~/커넥트ai복사/connect-ai/src/services/data-ingestion-gateway.ts (85줄)
```
 1	// src/services/data-ingestion-gateway.ts
 2	
 3	import { MasterValidationSchemaV2 } from '../types/schema'; // 가상의 스키마 정의 파일이라고 가정합니다.
 4	import { fetchNaverRawData } from './clients/naver-client';
 5	import { fetchLawMinistryRawData } from './clients/law-ministry-client';
 6	import { RawMaterial, NormalizedReportData } from '../types/data-models';
 7	
 8	/**
 9	 * @description 외부 API로부터 원본 데이터를 가져와 Master Validation Schema V2.0 기준으로 정규화하는 게이트웨이 서비스.
10	 * 이 계층은 데이터 소스별 차이를 흡수하고 단일 포맷을 보장합니다.
11	 */
12	export class DataIngestionGateway {
13	
14	    /**
15	     * 모든 외부 소스로부터 데이터를 수집 및 통합하여 최종 보고서 객체를 생성합니다.
16	     * @param matterId - 분석 대상 매물의 고유 ID.
17	     * @returns NormalizedReportData - 정규화되고 리스크 점수 계산에 적합한 구조화된 데이터.
18	     */
19	    public async ingestAndNormalize(matterId: string): Promise<NormalizedReportData> {
20	        console.log(`[Gateway] Starting data ingestion for Matter ID: ${matterId}`);
21	
22	        try {
23	            // 1. 병렬 API 호출 및 원본 데이터 수집 (Mocking/실제 API 연동)
24	            const [naverRaw, lawMinistryRaw] = await Promise.all([
25	                fetchNaverRawData(matterId),
26	                fetchLawMinistryRawData(matterId)
27	            ]);
28	
29	            // 2. 개별 소스 데이터 정규화 (Normalization)
30	            let normalizedNaver: MasterValidationSchemaV2['naver'] = this.normalizeNaverData(naverRaw);
31	            let normalizedLaw: MasterValidationSchemaV2['law']: MasterValidationSchemaV2['law'] = this.normalizeLawMinistryData(lawMinistryRaw);
32	
33	            // 3. 통합 및 최종 보고서 구조화 (Integration)
34	            const finalReportData: NormalizedReportData = {
35	                matterId: matterId,
36	                sourceMetadata: {
37	                    ingestionTime: new Date().toISOString(),
38	                    schemaVersion: "V2.0",
39	                    sourcesUsed: ['Naver', 'LawMinistry'] // 실제 사용된 출처 기록
40	                },
41	                dataPoints: {
42	                    naver: normalizedNaver,
43	                    law: normalizedLaw
44	                }
45	            };
46	
47	            console.log("[Gateway] Data ingestion successful and normalized.");
48	            return finalReportData;
49	
50	        } catch (error) {
51	            console.error("[Gateway Error] Failed to ingest or normalize data:", error);
52	            // 실패 시, 에러 로그와 함께 빈 구조체 또는 기본값 반환하여 시스템 붕괴 방지 (Graceful Degradation)
53	            throw new Error("Failed to complete data ingestion pipeline.");
54	        }
55	    }
56	
57	    /**
58	     * 네이버 부동산 원본 데이터를 Master Validation Schema V2.0의 'naver' 필드로 정규화합니다.
59	     */
60	    private normalizeNaverData(raw: RawMaterial): MasterValidationSchemaV2['naver'] {
61	        // 예시 로직: raw.priceFieldName -> schema.currentMarketPrice로 매핑 및 타입 검증
62	        return {
63	            addressDetail: raw?.area_name || null,
64	            marketPrice: parseFloat(raw?.real_price) || 0, // Type Casting & Defaulting
65	            listingDate: raw?.listing_date ? new Date(raw.listing_date).toISOString() : null,
66	            // ... 기타 필드 매핑 및 Validation Logic 추가
67	        };
68	    }
69	
70	    /**
71	     * 법제처 원본 데이터를 Master Validation Schema V2.0의 'law' 필드로 정규화합니다.
72	     */
73	    private normalizeLawMinistryData(raw: RawMaterial): MasterValidationSchemaV2['law'] {
74	        // 예시 로직: raw.processStage -> schema.currentProcessStatus로 매핑 및 데이터 검증
75	        return {
76	            currentProcessStatus: raw?.stage_name || null,
77	            legalBasisCode: raw?.code || null,
78	            lastUpdateDate: raw?.update_date ? new Date(raw.update_date).toISOString() : null,
79	            // ... 기타 필드 매핑 및 Validation Logic 추가
80	        };
81	    }
82	}
83	
84	// Exporting the gateway instance for consumption by other services
85	export const dataIngestionGateway = new DataIngestionGateway();
```
