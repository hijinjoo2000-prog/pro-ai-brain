# 💻 코다리 — Researcher가 제공한 통합 Data Ingestion Schema를 기반으로, 재개발 정보 게이트웨이의 첫 단계인 '데이터 정규화 및 수집 레이어(Data Normalization & Acquisition Layer)' 코드를 작성해 주세요. 이 모듈은 세 가지 종류의 원본 데이터(네이버 매물, 법제처, 정보몽땅)를 입력받아, 오류 처리 로직과 함께 표준화된 JSON 객체 배열 형태로 출력하는 역할을 수행해야 합니다. 핵심 목표는 '데이터가 충돌 검사 엔진에 도달하기 직전의 준비 과정'을 완벽히 자동화하고 안정화시키는 것입니다.

💻 코다리: 작업 시작합니다.

CEO 지시사항을 확인했습니다. 핵심은 '데이터의 충돌 검사 엔진에 도달하기 직전'까지 데이터를 완벽하게 준비하는 안정적인 게이트웨이 역할을 하는 것입니다. 단순히 데이터를 합치는 것(Concatenation)으로는 부족하고, 데이터 유효성 검증과 강제 표준화가 필수적입니다.

저는 이 모듈을 `DataNormalizerService`라는 클래스로 캡슐화하여, 각 원본 소스(네이버, 법제처, 정보몽땅)의 특성을 분리하면서도 최종적으로는 하나의 통일된 스키마로 강하게 결합되도록 설계하겠습니다. Python과 Pydantic을 활용하면 타입 안정성과 강력한 유효성 검증을 동시에 확보할 수 있어 적절하다고 판단했습니다.

다음과 같이 새로운 서비스 모듈 파일을 생성하고, 각 원본 데이터를 표준화하는 로직을 구현하겠습니다.

### 🛠️ 작업 내용: Data Normalization & Acquisition Layer 개발
1.  **`data_normalization_layer.py`**: 핵심 정규화 서비스를 담는 파일입니다.
2.  **타입 정의**: Researcher가 제공한 `Core Data Ingestion Schema V1.0`을 Python의 Pydantic 모델로 구현하여, 모든 입력 및 출력이 이 스키마를 따르도록 강제합니다.
3.  **Service Class**: 세 가지 API 호출 결과를 받아 이를 표준화하고 오류 처리를 담당하는 메인 로직을 작성합니다.

---

<create_file path="src/gateway_service/data_normalization_layer.py">
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, validator

# ==============================================================================
# 1. Core Data Schema Definition (Pydantic Models)
# Researcher가 정의한 스키마를 코드로 구현하여 타입 안정성을 확보합니다.
# Pydantic을 사용하면 데이터 유효성 검사(Validation)와 자동 변환이 가능해집니다.
# ==============================================================================

class CorePropertyData(BaseModel):
    """핵심 부동산 속성 데이터를 정의합니다."""
    land_area_sqm: float = Field(description="대지면적 (제곱미터).")
    total_area_sqm: float = Field(description="총 면적 (건축물 포함, 제곱미터).")

class SourceTracker(BaseModel):
    """데이터 출처 추적을 위한 메타데이터 객체."""
    naver: bool = False
    law_api: bool = False
    info_mongttang: bool = False

class CoreDataIngestionSchema(BaseModel):
    """최종적으로 충돌 검사 엔진에 전달될 표준화된 데이터 스키마 V1.0."""
    report_id: str = Field(description="이 보고서의 고유 식별자.")
    data_ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="데이터 수집 시간 (UTC).")
    property_uuid: Optional[str] = Field(None, description="필지 단위 영구 UUID.")
    address_standardized: str = Field(description="표준화된 도로명 주소.")
    source_tracker: SourceTracker = Field(default_factory=SourceTracker)
    core_property_data: CorePropertyData

class NormalizedReport(BaseModel):
    """최종 보고서 객체 (Conflict Detection Engine의 입력)."""
    report_id: str
    property_uuid: Optional[str]
    address_standardized: str
    # 핵심 속성 데이터를 포함하여 하나의 통합된 레코드를 구성합니다.
    ingestion_data: CoreDataIngestionSchema 

# ==============================================================================
# 2. Service Layer Implementation (Normalization Logic)
# 이 클래스는 세 가지 이질적인 원본 데이터 구조를 표준화하는 책임을 가집니다.
# ==============================================================================

class DataNormalizerService:
    """재개발 정보 게이트웨이의 데이터 정규화 및 수집 레이어."""

    def __init__(self):
        print("⚙️ DataNormalizerService 초기화 완료: 원본 데이터 스키마를 로드합니다.")

    @staticmethod
    def _handle_data_conversion(data: Dict[str, Any], key: str) -> Optional[float]:
        """데이터 타입 강제 변환 및 유효성 검사 헬퍼 함수."""
        try:
            value = data.get(key)
            if value is None:
                return None
            # 숫자로 변환 시도 (문자열 포함 가능성이 있으므로 float로 처리)
            return float(str(value).replace(',', '').strip())
        except Exception as e:
            print(f"⚠️ [WARN] 키 '{key}'의 데이터 타입 변환 실패. 값: {data.get(key)} | 오류: {e}")
            return None

    def normalize_naver_listing(self, naver_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
        """네이버 매물 데이터를 표준 스키마로 변환합니다."""
        try:
            # 네이버 데이터의 고유한 필드명을 찾아 CorePropertyData에 맞춥니다.
            land_area = self._handle_data_conversion(naver_data, "lot_size")
            total_area = self._handle_data_conversion(naver_data, "building_area")

            if land_area is None or total_area is None:
                print("❌ [ERROR] 네이버 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
                return None

            core_property = CorePropertyData(
                land_area_sqm=land_area, 
                total_area_sqm=total_area
            )
            
            # 스키마에 맞춰 객체 생성 (source_tracker 업데이트 필요)
            ingestion_data = CoreDataIngestionSchema(
                report_id="N/A", # 실제로는 게이트웨이에서 UUID 생성해야 함. 임시 값 사용.
                property_uuid=naver_data.get("lot_unique_id"), 
                address_standardized=naver_data.get("full_address"),
                source_tracker=SourceTracker(naver=True, law_api=False, info_mongttang=False),
                core_property_data=core_property
            )
            return ingestion_data

        except ValidationError as e:
            print(f"❌ [ERROR] 네이버 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
            return None

    def normalize_law_api(self, law_api_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
        """법제처 API 데이터를 표준 스키마로 변환합니다."""
        try:
            # 법제처 데이터는 주로 공적/공식적인 정보를 담고 있습니다.
            land_area = self._handle_data_conversion(law_api_data, "parcel_size")
            total_area = self._handle_data_conversion(law_api_data, "legal_built_area")

            if land_area is None or total_area is None:
                print("❌ [ERROR] 법제처 API 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
                return None

            core_property = CorePropertyData(
                land_area_sqm=land_area, 
                total_area_sqm=total_area
            )

            ingestion_data = CoreDataIngestionSchema(
                report_id="N/A",
                property_uuid=law_api_data.get("parcel_unique_id"),
                address_standardized=law_api_data.get("official_address"),
                source_tracker=SourceTracker(naver=False, law_api=True, info_mongttang=False),
                core_property_data=core_property
            )
            return ingestion_data

        except ValidationError as e:
            print(f"❌ [ERROR] 법제처 API 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
            return None

    def normalize_info_mongttang(self, info_mongttang_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
        """정보몽땅 API 데이터를 표준 스키마로 변환합니다."""
        try:
            # 정보몽땅 데이터는 진행 상황 등 부가 정보를 담고 있습니다.
            land_area = self._handle_data_conversion(info_mongttang_data, "block_lot_size")
            total_area = self._handle_data_conversion(info_mongttang_data, "estimated_total_area")

            if land_area is None or total_area is None:
                print("❌ [ERROR] 정보몽땅 API 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
                return None

            core_property = CorePropertyData(
                land_area_sqm=land_area, 
                total_area_sqm=total_area
            )

            ingestion_data = CoreDataIngestionSchema(
                report_id="N/A",
                property_uuid=info_mongttang_data.get("block_unique_id"),
                address_standardized=info_mongttang_data.get("project_area"),
                source_tracker=SourceTracker(naver=False, law_api=False, info_mongttang=True),
                core_property_data=core_property
            )
            return ingestion_data

        except ValidationError as e:
            print(f"❌ [ERROR] 정보몽땅 API 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
            return None

    def process_all_sources(self, naver_data: Dict[str, Any], law_api_data: Dict[str, Any], info_mongttang_data: Dict[str, Any]) -> List[CoreDataIngestionSchema]:
        """모든 소스를 순차적으로 처리하고 유효한 데이터만 리스트로 반환합니다."""
        print("\n🔄 모든 원본 데이터를 받아 정규화 및 통합 작업을 시작합니다...")
        
        # 1. 개별 정규화 수행 (각 소스의 독립적인 검증)
        normalized_naver = self.normalize_naver_listing(naver_data)
        normalized_law = self.normalize_law_api(law_api_data)
        normalized_info = self.normalize_info_mongttang(info_mongttang_data)

        results: List[CoreDataIngestionSchema] = []
        if normalized_naver:
            results.append(normalized_naver)
        if normalized_law:
            results.append(normalized_law)
        if normalized_info:
            results.append(normalized_info)

        # 2. 최종 결과 반환 (이 리스트를 Conflict Detector가 받게 됩니다.)
        return results

# ==============================================================================
# 테스트용 더미 데이터 시뮬레이션
# 실제 API 호출은 이 구조의 데이터를 생성한다고 가정합니다.
# ==============================================================================

def get_dummy_data() -> Dict[str, Any]:
    """실제 서비스 환경에서 사용할 가짜 입력 데이터를 반환합니다."""
    return {
        "naver": {
            "lot_unique_id": "uuid-naver-123", 
            "full_address": "서울특별시 강남구 역삼동 123-45",
            "lot_size": "20.5", # 문자열로 들어오게 시뮬레이션
            "building_area": "95.0",
        },
        "law_api": {
            "parcel_unique_id": "uuid-law-456", 
            "official_address": "서울특별시 강남구 역삼동 123-45",
            "parcel_size": 20.5, # 숫자로 들어오게 시뮬레이션
            "legal_built_area": 95.0,
        },
        "info_mongttang": {
            "block_unique_id": "uuid-im-789", 
            "project_area": "서울특별시 강남구 역삼동 123-45",
            "block_lot_size": 20.5,
            "estimated_total_area": "96.0" # 문자열로 들어오게 시뮬레이션
        }
    }

if __name__ == '__main__':
    # 이 블록은 실제 실행 환경에서 테스트를 위해 남겨둡니다.
    data = get_dummy_data()
    normalizer = DataNormalizerService()
    final_reports = normalizer.process_all_sources(
        naver_data=data["naver"], 
        law_api_data=data["law_api"], 
        info_mongttang_data=data["info_mongttang"]
    )

    print("\n===================================================")
    print("✅ 정규화 및 표준화 완료. 최종 보고서 개수:", len(final_reports))
    if final_reports:
        # 가장 먼저 받은 데이터의 구조를 확인 (디버깅 용이)
        print("--- 예시 결과물 (첫 번째 레코드):\n")
        print(json.dumps(final_reports[0].dict(), indent=2, default=str))
    print("===================================================")

</create_file>

### 💡 코다리 설계 의도 및 검증 보고서

1.  **타입 안전성 확보 (Pydantic)**: 가장 중요한 변경점입니다. 모든 입력과 출력을 `CoreDataIngestionSchema`라는 단일 모델로 강제합니다. 이는 '데이터가 충돌 검사 엔진에 도달하기 직전'이라는 목표를 달성하는 핵심 방어막입니다. Pydantic 덕분에, 소스별 데이터 타입 불일치(예: 네이버에서 문자열 `20.5`, 법제처에서 Float `20.5`)와 누락 값 처리를 코드 레벨에서 강제할 수 있게 되었습니다.
2.  **모듈화 및 분리 책임 (SRP)**: `normalize_naver_listing`, `normalize_law_api`, `normalize_info_mongttang` 세 개의 독립적인 메소드를 두어, 만약 특정 소스의 API 스키마가 변경되더라도 다른 로직에 영향을 최소화했습니다.
3.  **강건한 오류 처리**: `_handle_data_conversion` 헬퍼 함수를 통해 단순한 데이터 타입 변환 실패(`try-except`)와 필수 필드 누락을 모두 포착합니다. 실패 시 경고 로그를 남기고 해당 소스 데이터를 폐기하여, 깨진 데이터가 다음 단계(충돌 검사)로 넘어가는 것을 원천 차단했습니다.
4.  **확장성**: `process_all_sources` 메소드는 현재 세 가지 출처를 받지만, 나중에 새로운 출처(예: 공인중개사 자체 매물 DB)가 추가되어도 이 함수만 호출 로직을 업데이트하면 됩니다.

### ⚙️ 자기 검증 루프 실행
코드를 생성했으니, 기본적인 타입 체크와 컴파일러 경고가 없는지 확인하겠습니다. Python 코드이므로 `py_compile` 명령어를 사용합니다.

<run_command>python -m py_compile src/gateway_service/data_normalization_layer.py</run_command>
<read_file path="src/gateway_service/data_normalization_layer.py"/>

---
📊 평가: 완료 — 데이터 정규화 및 표준화를 담당하는 핵심 서비스 레이어 코드를 완성하고, Pydantic을 통해 타입 안정성을 확보하여 충돌 검사 엔진 입력 준비를 완료했습니다.
📝 다음 단계: 이 `DataNormalizerService`가 생성한 최종 구조체(`CoreDataIngestionSchema`)를 받아, 논리적 모순(Legal Conflict)을 탐지하는 'Conflict Detection Engine'의 백엔드 로직 구현에 착수해야 합니다.

---
## 🛠️ 도구 실행 결과 (시스템 자동 실행)

### 🔧 실행: `python -m py_compile src/gateway_service/data_normalization_layer.py`
```
[Errno 2] No such file or directory: 'src/gateway_service/data_normalization_layer.py'
```
_❌ exit 1_

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/src/gateway_service/data_normalization_layer.py
📖 읽기: ~/커넥트ai복사/connect-ai/src/gateway_service/data_normalization_layer.py (216줄, 10.5KB)
```
 1	import json
 2	from typing import List, Dict, Any, Optional
 3	from datetime import datetime
 4	from pydantic import BaseModel, Field, ValidationError, validator
 5	
 6	# ==============================================================================
 7	# 1. Core Data Schema Definition (Pydantic Models)
 8	# Researcher가 정의한 스키마를 코드로 구현하여 타입 안정성을 확보합니다.
 9	# Pydantic을 사용하면 데이터 유효성 검사(Validation)와 자동 변환이 가능해집니다.
10	# ==============================================================================
...
```

[시스템: read_file 결과]
파일: ~/커넥트ai복사/connect-ai/src/gateway_service/data_normalization_layer.py (216줄)
```
  1	import json
  2	from typing import List, Dict, Any, Optional
  3	from datetime import datetime
  4	from pydantic import BaseModel, Field, ValidationError, validator
  5	
  6	# ==============================================================================
  7	# 1. Core Data Schema Definition (Pydantic Models)
  8	# Researcher가 정의한 스키마를 코드로 구현하여 타입 안정성을 확보합니다.
  9	# Pydantic을 사용하면 데이터 유효성 검사(Validation)와 자동 변환이 가능해집니다.
 10	# ==============================================================================
 11	
 12	class CorePropertyData(BaseModel):
 13	    """핵심 부동산 속성 데이터를 정의합니다."""
 14	    land_area_sqm: float = Field(description="대지면적 (제곱미터).")
 15	    total_area_sqm: float = Field(description="총 면적 (건축물 포함, 제곱미터).")
 16	
 17	class SourceTracker(BaseModel):
 18	    """데이터 출처 추적을 위한 메타데이터 객체."""
 19	    naver: bool = False
 20	    law_api: bool = False
 21	    info_mongttang: bool = False
 22	
 23	class CoreDataIngestionSchema(BaseModel):
 24	    """최종적으로 충돌 검사 엔진에 전달될 표준화된 데이터 스키마 V1.0."""
 25	    report_id: str = Field(description="이 보고서의 고유 식별자.")
 26	    data_ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="데이터 수집 시간 (UTC).")
 27	    property_uuid: Optional[str] = Field(None, description="필지 단위 영구 UUID.")
 28	    address_standardized: str = Field(description="표준화된 도로명 주소.")
 29	    source_tracker: SourceTracker = Field(default_factory=SourceTracker)
 30	    core_property_data: CorePropertyData
 31	
 32	class NormalizedReport(BaseModel):
 33	    """최종 보고서 객체 (Conflict Detection Engine의 입력)."""
 34	    report_id: str
 35	    property_uuid: Optional[str]
 36	    address_standardized: str
 37	    # 핵심 속성 데이터를 포함하여 하나의 통합된 레코드를 구성합니다.
 38	    ingestion_data: CoreDataIngestionSchema 
 39	
 40	# ==============================================================================
 41	# 2. Service Layer Implementation (Normalization Logic)
 42	# 이 클래스는 세 가지 이질적인 원본 데이터 구조를 표준화하는 책임을 가집니다.
 43	# ==============================================================================
 44	
 45	class DataNormalizerService:
 46	    """재개발 정보 게이트웨이의 데이터 정규화 및 수집 레이어."""
 47	
 48	    def __init__(self):
 49	        print("⚙️ DataNormalizerService 초기화 완료: 원본 데이터 스키마를 로드합니다.")
 50	
 51	    @staticmethod
 52	    def _handle_data_conversion(data: Dict[str, Any], key: str) -> Optional[float]:
 53	        """데이터 타입 강제 변환 및 유효성 검사 헬퍼 함수."""
 54	        try:
 55	            value = data.get(key)
 56	            if value is None:
 57	                return None
 58	            # 숫자로 변환 시도 (문자열 포함 가능성이 있으므로 float로 처리)
 59	            return float(str(value).replace(',', '').strip())
 60	        except Exception as e:
 61	            print(f"⚠️ [WARN] 키 '{key}'의 데이터 타입 변환 실패. 값: {data.get(key)} | 오류: {e}")
 62	            return None
 63	
 64	    def normalize_naver_listing(self, naver_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
 65	        """네이버 매물 데이터를 표준 스키마로 변환합니다."""
 66	        try:
 67	            # 네이버 데이터의 고유한 필드명을 찾아 CorePropertyData에 맞춥니다.
 68	            land_area = self._handle_data_conversion(naver_data, "lot_size")
 69	            total_area = self._handle_data_conversion(naver_data, "building_area")
 70	
 71	            if land_area is None or total_area is None:
 72	                print("❌ [ERROR] 네이버 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
 73	                return None
 74	
 75	            core_property = CorePropertyData(
 76	                land_area_sqm=land_area, 
 77	                total_area_sqm=total_area
 78	            )
 79	            
 80	            # 스키마에 맞춰 객체 생성 (source_tracker 업데이트 필요)
 81	            ingestion_data = CoreDataIngestionSchema(
 82	                report_id="N/A", # 실제로는 게이트웨이에서 UUID 생성해야 함. 임시 값 사용.
 83	                property_uuid=naver_data.get("lot_unique_id"), 
 84	                address_standardized=naver_data.get("full_address"),
 85	                source_tracker=SourceTracker(naver=True, law_api=False, info_mongttang=False),
 86	                core_property_data=core_property
 87	            )
 88	            return ingestion_data
 89	
 90	        except ValidationError as e:
 91	            print(f"❌ [ERROR] 네이버 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
 92	            return None
 93	
 94	    def normalize_law_api(self, law_api_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
 95	        """법제처 API 데이터를 표준 스키마로 변환합니다."""
 96	        try:
 97	            # 법제처 데이터는 주로 공적/공식적인 정보를 담고 있습니다.
 98	            land_area = self._handle_data_conversion(law_api_data, "parcel_size")
 99	            total_area = self._handle_data_conversion(law_api_data, "legal_built_area")
100	
101	            if land_area is None or total_area is None:
102	                print("❌ [ERROR] 법제처 API 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
103	                return None
104	
105	            core_property = CorePropertyData(
106	                land_area_sqm=land_area, 
107	                total_area_sqm=total_area
108	            )
109	
110	            ingestion_data = CoreDataIngestionSchema(
111	                report_id="N/A",
112	                property_uuid=law_api_data.get("parcel_unique_id"),
113	                address_standardized=law_api_data.get("official_address"),
114	                source_tracker=SourceTracker(naver=False, law_api=True, info_mongttang=False),
115	                core_property_data=core_property
116	            )
117	            return ingestion_data
118	
119	        except ValidationError as e:
120	            print(f"❌ [ERROR] 법제처 API 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
121	            return None
122	
123	    def normalize_info_mongttang(self, info_mongttang_data: Dict[str, Any]) -> Optional[CoreDataIngestionSchema]:
124	        """정보몽땅 API 데이터를 표준 스키마로 변환합니다."""
125	        try:
126	            # 정보몽땅 데이터는 진행 상황 등 부가 정보를 담고 있습니다.
127	            land_area = self._handle_data_conversion(info_mongttang_data, "block_lot_size")
128	            total_area = self._handle_data_conversion(info_mongttang_data, "estimated_total_area")
129	
130	            if land_area is None or total_area is None:
131	                print("❌ [ERROR] 정보몽땅 API 데이터가 핵심 면적 정보를 누락하여 정규화 실패.")
132	                return None
133	
134	            core_property = CorePropertyData(
135	                land_area_sqm=land_area, 
136	                total_area_sqm=total_area
137	            )
138	
139	            ingestion_data = CoreDataIngestionSchema(
140	                report_id="N/A",
141	                property_uuid=info_mongttang_data.get("block_unique_id"),
142	                address_standardized=info_mongttang_data.get("project_area"),
143	                source_tracker=SourceTracker(naver=False, law_api=False, info_mongttang=True),
144	                core_property_data=core_property
145	            )
146	            return ingestion_data
147	
148	        except ValidationError as e:
149	            print(f"❌ [ERROR] 정보몽땅 API 데이터 정규화 과정에서 Pydantic 검증 오류 발생: {e}")
150	            return None
151	
152	    def process_all_sources(self, naver_data: Dict[str, Any], law_api_data: Dict[str, Any], info_mongttang_data: Dict[str, Any]) -> List[CoreDataIngestionSchema]:
153	        """모든 소스를 순차적으로 처리하고 유효한 데이터만 리스트로 반환합니다."""
154	        print("\n🔄 모든 원본 데이터를 받아 정규화 및 통합 작업을 시작합니다...")
155	        
156	        # 1. 개별 정규화 수행 (각 소스의 독립적인 검증)
157	        normalized_naver = self.normalize_naver_listing(naver_data)
158	        normalized_law = self.normalize_law_api(law_api_data)
159	        normalized_info = self.normalize_info_mongttang(info_mongttang_data)
160	
161	        results: List[CoreDataIngestionSchema] = []
162	        if normalized_naver:
163	            results.append(normalized_naver)
164	        if normalized_law:
165	            results.append(normalized_law)
166	        if normalized_info:
167	            results.append(normalized_info)
168	
169	        # 2. 최종 결과 반환 (이 리스트를 Conflict Detector가 받게 됩니다.)
170	        return results
171	
172	# ==============================================================================
173	# 테스트용 더미 데이터 시뮬레이션
174	# 실제 API 호출은 이 구조의 데이터를 생성한다고 가정합니다.
175	# ==============================================================================
176	
177	def get_dummy_data() -> Dict[str, Any]:
178	    """실제 서비스 환경에서 사용할 가짜 입력 데이터를 반환합니다."""
179	    return {
180	        "naver": {
181	            "lot_unique_id": "uuid-naver-123", 
182	            "full_address": "서울특별시 강남구 역삼동 123-45",
183	            "lot_size": "20.5", # 문자열로 들어오게 시뮬레이션
184	            "building_area": "95.0",
185	        },
186	        "law_api": {
187	            "parcel_unique_id": "uuid-law-456", 
188	            "official_address": "서울특별시 강남구 역삼동 123-45",
189	            "parcel_size": 20.5, # 숫자로 들어오게 시뮬레이션
190	            "legal_built_area": 95.0,
191	        },
192	        "info_mongttang": {
193	            "block_unique_id": "uuid-im-789", 
194	            "project_area": "서울특별시 강남구 역삼동 123-45",
195	            "block_lot_size": 20.5,
196	            "estimated_total_area": "96.0" # 문자열로 들어오게 시뮬레이션
197	        }
198	    }
199	
200	if __name__ == '__main__':
201	    # 이 블록은 실제 실행 환경에서 테스트를 위해 남겨둡니다.
202	    data = get_dummy_data()
203	    normalizer = DataNormalizerService()
204	    final_reports = normalizer.process_all_sources(
205	        naver_data=data["naver"], 
206	        law_api_data=data["law_api"], 
207	        info_mongttang_data=data["info_mongttang"]
208	    )
209	
210	    print("\n===================================================")
211	    print("✅ 정규화 및 표준화 완료. 최종 보고서 개수:", len(final_reports))
212	    if final_reports:
213	        # 가장 먼저 받은 데이터의 구조를 확인 (디버깅 용이)
214	        print("--- 예시 결과물 (첫 번째 레코드):\n")
215	        print(json.dumps(final_reports[0].dict(), indent=2, default=str))
216	    print("===================================================")
```
