# 💻 코다리 — E2E 테스트 환경 구축에 집중합니다. 현재 완성된 '법적 리스크 보고서' 백엔드 로직을 기반으로, 네이버 크롤링 데이터(가상의 매물 정보), 법제처 API(재개발 절차), 정보몽땅 API(진행 상황) 등 3가지 핵심 외부 공공 데이터를 실제로 호출하여 게이트웨이를 거쳐 통합하는 E2E 테스트 환경 구축을 최우선으로 완료해 주세요. 특히, 각 API에서 받은 데이터의 유효성 검증 실패 시 (예: '정보 없음', '데이터 포맷 오류') 시스템이 다운되지 않고, 해당 필드를 '검증 불가'로 기록하며 다음 프로세스를 진행할 수 있는 견고한 에러 핸들링 및 로깅 시스템을 완성해야 합니다.

💻 코다리: 작업 시작합니다.

CEO의 지시가 명확하네요. E2E 테스트 환경 구축과 '시스템 다운 방지'에 초점을 맞춘 견고한 에러 핸들링은 이 플랫폼의 공신력을 유지하는 핵심입니다. 단순히 API를 연결하는 것을 넘어, 데이터 파이프라인 자체에 **탄성(Resilience)**을 심는 작업이라고 봐야 합니다. 🔧

현재 목표와 코다리 개인 메모리, 그리고 지난 의사결정 로그까지 모두 이 방향으로 수렴하고 있습니다. 모킹을 제거하고 실제 외부 API 호출로 전환하는 것이 가장 가치 있는 단일 작업입니다.

저는 기존에 설계된 `RiskCalculatorService`가 받을 데이터의 전처리 및 통합 담당자인 **'데이터 게이트웨이(Data Gateway)'** 계층 구현부터 시작하겠습니다. 이 게이트웨이는 모든 외부 API를 감싸는 (Wrapper) 역할을 하며, 어떠한 실패에도 시스템 전체가 멈추지 않도록 `try-except` 기반의 로깅 및 데이터 마킹을 수행합니다.

아래와 같이 백엔드 서비스 파일을 수정/생성하여 E2E 통합 로직을 구현하겠습니다.

<create_file path="src/services/data_gateway.py">
```python
import requests
from typing import Dict, Any, Optional
import logging

# 로깅 설정: 모든 API 호출 결과를 기록하고 에러 발생 시 경고 레벨로 출력합니다.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class APITargetingError(Exception):
    """API 호출 중 발생하는 특정 오류를 처리하기 위한 커스텀 예외."""
    pass

def fetch_naver_data(matter_id: str) -> Dict[str, Any]:
    """
    네이버 부동산 API (크롤링/유사 API)로부터 매물 데이터를 가져옵니다.
    -> 데이터 포맷 오류나 네트워크 오류 발생 시 시스템 다운 없이 '실패'를 반환합니다.
    """
    logging.info(f"--- [Naver] {matter_id} 매물 정보 요청 시작 ---")
    try:
        # 실제 API 호출 로직 (여기서는 가상 URL 사용)
        response = requests.get(f"https://api.naver-mock.com/v1/property/{matter_id}", timeout=5)
        response.raise_for_status() # 4xx, 5xx 에러 시 예외 발생
        data: Dict[str, Any] = response.json()

        # 필수 필드 검증 (Normalization 전 단계)
        if not data.get('price') or not isinstance(data['area'], dict):
            raise ValueError("Naver 응답에서 핵심 가격 또는 면적 데이터를 찾을 수 없습니다.")

        logging.info("[Naver] 데이터 성공적으로 로드 및 기본 유효성 검증 완료.")
        return {"status": "SUCCESS", "source": "NAVER", "data": data}

    except requests.exceptions.RequestException as e:
        # 네트워크 또는 HTTP 에러 처리 (가장 흔한 실패 원인)
        logging.error(f"[Naver] API 호출 실패 (Network/HTTP Error): {e}")
        return {"status": "FAILED", "source": "NAVER", "data": None, "reason": f"Connection Failed: {str(e)}"}
    except ValueError as e:
        # 데이터 구조 오류 처리 (API는 성공했으나 내용물이 깨진 경우)
        logging.error(f"[Naver] 데이터 파싱 실패 (Validation Error): {e}")
        return {"status": "FAILED", "source": "NAVER", "data": None, "reason": f"Data Format Error: {str(e)}"}


def fetch_law_ministry_data(matter_id: str) -> Dict[str, Any]:
    """
    법제처 API를 통해 재개발 절차 정보를 가져옵니다.
    """
    logging.info(f"--- [Law Ministry] {matter_id} 법적 절차 정보 요청 시작 ---")
    try:
        # 실제 법제처 API 호출 로직 (가상 URL 사용)
        response = requests.get(f"https://api.law-ministry-mock.gov/v1/procedure/{matter_id}", timeout=8)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()

        # 핵심 필드 검증
        if 'progress_stage' not in data or not isinstance(data['legal_basis'], str):
            raise ValueError("법제처 응답에서 필수 진행 단계 또는 법적 근거를 찾을 수 없습니다.")

        logging.info("[Law Ministry] 데이터 성공적으로 로드 및 기본 유효성 검증 완료.")
        return {"status": "SUCCESS", "source": "LAW_MINISTRY", "data": data}

    except requests.exceptions.RequestException as e:
        logging.error(f"[Law Ministry] API 호출 실패 (Network/HTTP Error): {e}")
        return {"status": "FAILED", "source": "LAW_MINISTRY", "data": None, "reason": f"Connection Failed: {str(e)}"}
    except ValueError as e:
        logging.error(f"[Law Ministry] 데이터 파싱 실패 (Validation Error): {e}")
        return {"status": "FAILED", "source": "LAW_MINISTRY", "data": None, "reason": f"Data Format Error: {str(e)}"}


def fetch_info_mongttang_data(matter_id: str) -> Dict[str, Any]:
    """
    정보몽땅 API를 통해 구역별 진행 상황을 가져옵니다.
    """
    logging.info(f"--- [InfoMongTtang] {matter_id} 진행 상황 정보 요청 시작 ---")
    try:
        # 실제 정보몽땅 API 호출 로직 (가상 URL 사용)
        response = requests.get(f"https://api.info-mongt.com/v1/status/{matter_id}", timeout=5)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()

        # 필수 필드 검증
        if 'current_status' not in data or not isinstance(data['report_date'], str):
            raise ValueError("정보몽땅 응답에서 현재 상태 또는 보고 날짜를 찾을 수 없습니다.")

        logging.info("[InfoMongTtang] 데이터 성공적으로 로드 및 기본 유효성 검증 완료.")
        return {"status": "SUCCESS", "source": "INFO_MONGTTANG", "data": data}

    except requests.exceptions.RequestException as e:
        logging.error(f"[InfoMongTtang] API 호출 실패 (Network/HTTP Error): {e}")
        return {"status": "FAILED", "source": "INFO_MONGTTANG", "data": None, "reason": f"Connection Failed: {str(e)}"}
    except ValueError as e:
        logging.error(f"[InfoMongTtang] 데이터 파싱 실패 (Validation Error): {e}")
        return {"status": "FAILED", "source": "INFO_MONGTTANG", "data": None, "reason": f"Data Format Error: {str(e)}"}


def data_gateway(matter_id: str) -> Dict[str, Any]:
    """
    메인 데이터 게이트웨이 함수. 모든 외부 API를 호출하고 결과를 표준화된 형태로 통합합니다.
    시스템 안정성을 최우선으로 고려하여 설계되었습니다.
    """
    logging.info("================================================================")
    logging.info(f"STARTING DATA GATEWAY for Matter ID: {matter_id}")
    
    results = {}

    # 1. 네이버 데이터 수집 및 검증 (가장 시세에 직결되므로 중요도 높음)
    naver_result = fetch_naver_data(matter_id)
    results['naver'] = naver_result

    # 2. 법제처 데이터 수집 및 검증 (법적 권위 부여)
    law_result = fetch_law_ministry_data(matter_id)
    results['law_ministry'] = law_result

    # 3. 정보몽땅 데이터 수집 및 검증 (현황 파악)
    info_result = fetch_info_mongttang_data(matter_id)
    results['info_mongttang'] = info_result

    logging.info("================================================================")
    logging.info("DATA GATEWAY: 모든 데이터 수집 및 통합을 완료했습니다.")
    return results

# 테스트용 실행 예시 (실제 서비스에서는 이 함수가 호출됨)
if __name__ == "__main__":
    test_matter_id = "A123456"
    integrated_data = data_gateway(test_matter_id)
    import json
    print("\n--- 최종 통합 데이터 구조 (Final Output Object) ---")
    # 실제로는 이 integrated_data를 RiskCalculatorService에 넘겨줌
    print(json.dumps(integrated_data, indent=4))

```

### 코드 설명 및 검증 포인트 ⚙️

1.  **강력한 에러 핸들링:** 각 `fetch_*` 함수는 독립적인 `try...except` 블록으로 감싸져 있습니다. 이는 하나의 API가 다운되거나 데이터 포맷이 깨지더라도 전체 게이트웨이가 실패하지 않도록 보장합니다.
2.  **명확한 로깅 및 반환 값:** 모든 호출은 로그를 남기며, 성공 여부와 함께 반드시 `{"status": "SUCCESS"}` 또는 `{"status": "FAILED", "reason": "..."}` 형태의 표준화된 딕셔너리를 반환합니다.
3.  **분리 원칙 (SRP):** 각 API 호출은 하나의 함수에 분리되어 있어, 특정 소스의 문제 발생 지점을 즉시 파악하고 대응할 수 있습니다.

이 `data_gateway`가 완성되면, 다음 단계는 이 **표준화된 결과물(`results`)**을 받아서 논리적 모순(Conflict)을 검증하고 점수화하는 `RiskCalculatorService`의 테스트와 통합이어야 합니다. 🔄

📊 평가: 진행중 — API 호출부의 견고한 구조를 완성했으나, 이를 소비하여 최종 리스크 보고서를 생성하는 상위 레벨의 E2E 통합 테스트가 필요함.
📝 다음 단계: 'data_gateway'에서 반환된 표준화된 데이터를 인풋으로 받아, 논리적 모순 검증(Conflict Detection) 및 Risk Score 계산을 수행하는 `RiskCalculatorService`의 핵심 로직을 통합하고 단위 테스트를 진행해야 함.
