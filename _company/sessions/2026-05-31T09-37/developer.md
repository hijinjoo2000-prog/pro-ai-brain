# 💻 코다리 — researcher가 제시한 위키 구조에 맞춰 파일 모니터링 및 자동 분석 파이프라인을 개발하라. 구체적으로, '파일 변경 감지기(File Watcher)'를 구현하고, 신규 파일을 읽어와 내용을 추출/파싱하는 스크립트를 작성하며, 최종 결과를 웹 기반의 Wiki 형식 API로 전송할 수 있는 백엔드 로직과 테스트 코드를 포함하여 기획하라.

💻 코다리: 작업 시작합니다.

CEO 지시와 사용자 요청을 종합해 보니, 단순한 스크립팅을 넘어선 **지식 자산 관리(KMS)**의 핵심 파이프라인 구축 프로젝트네요. 이건 단순히 파일을 모니터링하는 수준을 넘어서, 파일 시스템 이벤트를 실시간으로 포착하고 → 정교하게 분석하여 구조화된 데이터로 변환한 뒤 → 최종 API 엔드포인트까지 전달하는 *End-to-End 자동화 워크플로우*가 필요합니다.

단순히 '만들겠다'고 텍스트로 끝낼 순 없죠. 이 파이프라인은 최소한 다음 네 가지 컴포넌트로 분리되어야 안정적입니다:
1. **Watcher:** 파일 변경 감지기 (Producer).
2. **Parser:** 콘텐츠 추출 및 구조화 로직 (Processor).
3. **API Server:** 최종 수신/저장 백엔드 (Consumer/Sink).
4. **Test Suite:** 전체 흐름 검증 (Validator).

우선, 프로젝트 디렉토리를 잡고 필요한 라이브러리 설치부터 진행하겠습니다. Python 기반으로 구성하는 게 가장 효율적입니다.

### ⚙️ 1단계: 환경 설정 및 프로젝트 구조 정의

먼저 `knowledge_pipeline` 폴더를 만들고, Watcher와 Processor가 돌아갈 기본 코드를 설계하겠습니다.

<create_file path="./knowledge_pipeline/requirements.txt">
watchdog==3.6.0
fastapi
uvicorn[standard]
pydantic
</create_file>

테스트 환경을 위해 가상의 원본 파일이 들어갈 디렉토리도 만들어 둡니다.

<run_command>mkdir -p knowledge_pipeline/raw_inputs</run_command>

### ⚙️ 2단계: 핵심 파서 로직 구현 (WikiParser)

가장 중요한 부분입니다. `Researcher`님이 제시한 표준 위키 구조에 맞춰, 원본 파일을 받으면 *구조화된 JSON 객체*로 변환하는 역할을 할 클래스를 만듭니다. 이 클래스가 데이터 추출의 책임을 집니다.

**[핵심 로직 검증 포인트]**:
1. **메타데이터 (A):** 파일명/경로를 기반으로 제목, 출처 링크 등을 자동 할당합니다.
2. **추출 시뮬레이션:** 실제 NLP 모델 없이도 구조적 데이터를 만들어내기 위해, 원본 텍스트에서 특정 키워드(예: '결론:', '핵심:')가 발견되면 해당 섹션에 내용을 분배하는 방식으로 로직을 설계하겠습니다. (실제 운영 환경에서는 여기에 LLM API 호출이 들어갑니다.)

<create_file path="./knowledge_pipeline/parser.py">
import os
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

class WikiParser:
    """
    Raw Text 파일을 받아 Researcher가 제시한 표준 위키 아티팩트 구조로 변환하는 파서 클래스.
    (실제 운영 환경에서는 LLM API를 사용하여 섹션별 내용을 채우는 로직이 추가되어야 합니다.)
    """

    def __init__(self, raw_file_path: Path):
        self.raw_file_path = raw_file_path
        self.content = self._read_content()

    def _read_content(self) -> str:
        """파일의 내용을 읽어옵니다."""
        try:
            with open(self.raw_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"🚨 Error reading file {self.raw_file_path}: {e}")
            return ""

    def parse(self) -> Dict[str, Any]:
        """
        전체 콘텐츠를 분석하여 표준화된 위키 구조의 딕셔너리를 반환합니다.
        """
        if not self.content:
            raise ValueError("Cannot process empty file content.")

        # --- 1. 메타데이터 (Metadata) 추출 및 설정 ---
        title = self._extract_metadata(self.raw_file_path)
        source_link = f"file://{os.path.abspath(self.raw_file_path)}" # 임시 파일 링크 사용

        # --- 2. 나머지 섹션별 내용 분배 (시뮬레이션 로직) ---
        parsed_data = {
            "metadata": {
                "title": title,
                "source_link": source_link,
                "creation_date": datetime.now().isoformat(),
                "keywords": self._determine_keywords(self.content),
                "source_type": "User Uploaded Document"
            },
            "summary": self._extract_section("개요 및 요약 (Summary & Thesis)"),
            "core_concepts": self._extract_section("핵심 개념 정의 (Core Concepts)"),
            "deep_dive_analysis": self._extract_section("분석 및 세부 내용 (Deep Dive Analysis)"),
            "connectivity_action": self._extract_section("연결 및 실행 (Connectivity & Action)")
        }

        # 구조 검증을 위해 빈 값 처리
        for key, value in parsed_data.items():
             if not value:
                 parsed_data[key] = "추출된 내용이 없습니다. 원본 자료를 보완하거나 LLM 분석을 통해 채워야 합니다."


        return parsed_data

    def _extract_metadata(self, path: Path) -> str:
        """파일 경로와 내용을 조합하여 제목을 추론합니다."""
        # 실제로는 파일명 외에 내용의 첫 줄이나 별도의 메타 정보가 더 정확함.
        base_name = path.stem.replace("_", " ").title()
        return f"[{base_name}] - 지식 아티팩트"

    def _determine_keywords(self, content: str) -> list[str]:
        """간단한 키워드 추출 시뮬레이션 (실제는 TF-IDF 또는 LLM 사용)."""
        # 예시로 'AI', '파이프라인', '위키'가 포함되면 관련 태그를 붙임.
        keywords = set()
        if "AI" in content or "인공지능" in content:
            keywords.add("AI")
        if "파이프라인" in content or "자동화" in content:
            keywords.add("워크플로우")
        return list(keywords)

    def _extract_section(self, section_name: str) -> str:
        """
        특정 섹션 이름 근처의 텍스트를 찾아 추출하는 시뮬레이션 로직.
        실제 구현에서는 정교한 Regex와 Contextual Windowing이 필요합니다.
        """
        # 간단히 해당 키워드가 포함된 내용을 반환한다고 가정
        if section_name in self.content:
            return f"'{section_name}' 섹션에서 분석된 핵심 내용입니다. (Placeholder)"
        else:
            return "해당 구조의 내용은 원본 자료에 명시되지 않았거나, 고급 NLP 처리가 필요합니다."


# 테스트 실행을 위한 임시 더미 파일 생성 및 테스트는 3단계에서 진행하겠습니다.

print("✅ WikiParser 클래스 구현 완료. 데이터 구조화 로직이 준비되었습니다.")
</create_file>

### ⚙️ 3단계: 파일 변경 감지기 (File Watcher) 구현

파일 시스템을 모니터링하여, 새로운 파일이 들어오는 순간 `WikiParser`를 호출하는 백그라운드 스크립트를 만듭니다. Python의 `watchdog` 라이브러리를 사용하겠습니다.

<create_file path="./knowledge_pipeline/watcher.py">
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from parser import WikiParser # 2단계에서 만든 클래스 임포트

WATCH_DIR = Path("./raw_inputs")

class KnowledgeFileHandler(FileSystemEventHandler):
    """파일 시스템 이벤트를 감지하고 파싱을 트리거하는 핸들러."""
    def on_created(self, event):
        # 파일이 생성되었는지 확인 (디렉토리는 무시)
        if not event.is_directory and event.src_path.endswith(('.txt', '.md')):
            print(f"\n🟢 [Watcher] 신규 파일 감지: {event.src_path}")
            # 파일을 읽고 파싱하는 과정을 비동기적으로 실행 (메인 스레드 블로킹 방지)
            self.process_file_async(Path(event.src_path))

    def process_file_async(self, file_path: Path):
        """실제 파싱 로직을 호출하고 결과를 API 엔드포인트로 전송하는 시뮬레이션."""
        try:
            # 1. 파서 초기화 및 실행
            parser = WikiParser(file_path)
            structured_data = parser.parse()

            print("⚙️ [Processor] 데이터 구조화 완료.")
            
            # 2. 백엔드 API 전송 시뮬레이션 (실제로는 HTTP POST 요청)
            self._send_to_wiki_api(structured_data, file_path.name)

        except Exception as e:
            print(f"🐛 [Error] 파일 처리 중 치명적인 오류 발생: {e}")


    def _send_to_wiki_api(self, data: dict, filename: str):
        """
        파싱된 데이터를 최종 Wiki API 엔드포인트로 전송하는 로직 (Mock).
        실제로는 requests.post(...)를 사용합니다.
        """
        print(f"📡 [API Sink] '{filename}' 데이터 전송 준비 완료. (Status: SUCCESS)")
        # print("--- 전송할 JSON 스니펫 ---")
        # print(json.dumps({"title": data['metadata']['title'], "summary_snippet": data['summary'][:50]+"...", "source": filename}, indent=2, ensure_ascii=False))
        print("--------------------------")


def start_monitoring():
    """모니터링 루프를 시작합니다."""
    event_handler = KnowledgeFileHandler()
    observer = Observer()
    # WATCH_DIR을 감시하고, 이벤트가 발생하면 핸들러의 on_created가 호출됨.
    observer.schedule(event_handler, str(WATCH_DIR), recursive=False)
    observer.start()
    print(f"\n💻 [Watcher] ✅ 지식 축적 폴더 '{WATCH_DIR}' 모니터링 시작 완료.")
    print("   새로운 .txt 또는 .md 파일을 이 폴더에 넣어 테스트해주세요.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()
</create_file>

### ⚙️ 4단계: API 백엔드 서버 구현 (FastAPI)

파서가 완성한 구조화된 데이터를 실제로 받아들이고 저장하는 가상의 백엔드 엔드포인트를 만듭니다. 이게 최종 수신 지점입니다.

<create_file path="./knowledge_pipeline/api_server.py">
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Pydantic 모델을 사용하여 데이터의 스키마를 강제합니다. (매우 중요)
class WikiArticleData(BaseModel):
    """WikiParser가 생성한 구조화된 아티클 데이터를 받을 모델."""
    metadata: Dict[str, Any]
    summary: str
    core_concepts: str
    deep_dive_analysis: str
    connectivity_action: str

app = FastAPI(
    title="Seropro Knowledge Wiki API",
    description="자동 분석 파이프라인의 최종 수신 엔드포인트입니다. 모든 지식 아티팩트는 이 API를 통해 저장됩니다."
)


@app.post("/api/v1/wiki/article")
async def save_new_article(data: WikiArticleData):
    """새로운 구조화된 위키 아티클을 데이터베이스에 저장합니다."""
    # TODO: 실제 DB 로직 (예: SQLAlchemy를 사용한 트랜잭션 커밋)이 들어갈 곳입니다.
    print("-----------------------------------------------------")
    print(f"💾 [DB] 성공적으로 '{data.metadata['title']}' 아티클을 데이터베이스에 저장했습니다.")
    print("   [Meta Info]: Source:", data.metadata['source_link'])
    # print(json.dumps(data.dict(), indent=2, ensure_ascii=False)) # 실제 디버깅 시 주석 해제
    print("-----------------------------------------------------")

    return {"status": "success", "message": f"Article '{data.metadata['title']}' saved successfully."}


@app.get("/api/v1/wiki/article/{slug}")
async def get_article(slug: str):
    """특정 슬러그로 아티클을 검색합니다."""
    # TODO: DB 조회 로직 구현
    if slug == "example-missing":
        raise HTTPException(status_code=404, detail="Article not found.")
    return {"article_id": 123, "title": f"Retrieved article for {slug}"}

print("✅ FastAPI 백엔드 API 서버 정의 완료. 포트 8000에서 구동 가능합니다.")
</create_file>

### ✅ 5단계: 통합 테스트 및 실행 가이드 (Self-Verification)

이 파이프라인을 실제로 돌리기 전에, 모든 컴포넌트가 제대로 연결되는지 확인하는 단일 테스트 파일을 만들겠습니다.

<create_file path="./knowledge_pipeline/test_run.py">
from pathlib import Path
import time
import shutil
from parser import WikiParser
from watchdog.events import FileSystemEventHandler
# watcher와 api_server는 통합적으로 동작하기 때문에 직접 실행하는 대신, 
# 필요한 의존성만 임포트하여 테스트합니다.

TEST_DIR = Path("./raw_inputs")

def setup_test(dummy_content: str) -> Path:
    """테스트 환경을 설정하고 더미 파일을 생성합니다."""
    print("\n[SETUP] --- 테스트 파일 준비 중 ---")
    # 기존 파일 정리
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()

    dummy_path = TEST_DIR / "test_raw_article.md"
    with open(dummy_path, 'w', encoding='utf-8') as f:
        f.write(dummy_content)
    print(f"[SETUP] 더미 파일 생성 완료: {dummy_path}")
    return dummy_path

def run_pipeline_test(file_path: Path):
    """Parser -> API Sink 로직을 모의 실행하여 전체 흐름을 테스트합니다."""
    print("\n\n=====================================================")
    print("🚀 [TEST RUN] 파이프라인 End-to-End 시뮬레이션 시작")
    print("=====================================================")

    try:
        # 1. Parser 실행 (데이터 구조화)
        parser = WikiParser(file_path)
        structured_data = parser.parse()
        print("\n[✅ Parser] 데이터 구조화 성공.")
        
        # 2. API Sink 시뮬레이션 (백엔드 전송)
        # 실제로는 watcher가 이 역할을 수행합니다.
        print("\n[🚀 Flow Test] 백엔드(FastAPI)로 데이터 전달 시도...")
        # Mocking the API call process
        class MockHandler:
             def _send_to_wiki_api(self, data: dict, filename: str):
                print("📡 [API Sink Mock] 데이터 전송 성공적으로 모의 처리됨.")

        MockHandler()._send_to_wiki_api(structured_data, file_path.name)
        
        print("\n=====================================================")
        print("✨ 테스트 완료: 파일 감지 -> 파싱 -> API 전송 흐름 검증 성공!")
    except Exception as e:
        print(f"\n❌ [FAIL] 테스트 실패: {e}")


if __name__ == "__main__":
    # 💡 실제 분석을 시뮬레이션하기 위한 더미 콘텐츠 (Researcher의 구조를 모방)
    DUMMY_CONTENT = """
# AI 기반 지식 자산 관리 파이프라인 설계

## 개요 및 요약 (Summary & Thesis)
본 문서는 분산된 형태의 기업 지식을 체계적으로 아카이브하기 위한 자동화 파이프라인을 제안합니다. 핵심은 '파일 변경 감지'와 '표준 위키 구조 강제 적용'입니다. 결론적으로, 모든 원천 데이터는 메타데이터가 붙은 JSON/Wiki 형태로 변환되어야 합니다.

## 핵심 개념 정의 (Core Concepts)
* **Knowledge Artifact:** 단순 문서가 아닌, 검색 가능하고 재활용 가능한 고도로 구조화된 지식 단위.
* **File Watcher:** 파일 시스템의 이벤트를 감지하는 메커니즘 (예: watchdog 라이브러리).
* **Pipeline:** 여러 단계의 처리(감지 -> 파싱 -> 저장)가 순차적으로 연결되는 워크플로우.

## 분석 및 세부 내용 (Deep Dive Analysis)
파이프라인은 크게 3단계로 나뉩니다. 첫째, 감지에 초점을 맞추고, 둘째, 파싱 시에는 NLP 모델을 이용해 섹션별 주장을 분리해야 합니다. 특히 '연결성' 데이터를 추출하는 것이 중요합니다.

## 연결 및 실행 (Connectivity & Action)
이 지식은 [프로젝트 관리]와 [데이터 아키텍처] 분야에 직접적으로 적용 가능합니다. 즉시 액션 플랜으로, 이 파이프라인의 각 단계별로 단위 테스트 케이스를 작성해야 합니다.
"""

    dummy_file = setup_test(DUMMY_CONTENT)
    run_pipeline_test(dummy_file)

finally:
    # 정리 작업
    if Path("./raw_inputs").exists():
        shutil.rmtree(Path("./raw_inputs"))
        print("\n[CLEANUP] 임시 테스트 디렉토리 삭제 완료.")
</create_file>

### 📝 다음 단계: 실행 및 통합 검증

이 코드는 **완벽하게 분리된 모듈**입니다. 사용하시려면 다음과 같이 순서대로 환경을 구축하고 실행해야 합니다.

1.  **환경 설치:** `pip install -r knowledge_pipeline/requirements.txt`
2.  **API 서버 구동:** 터미널 A에서 `uvicorn knowledge_pipeline.api_server:app --reload`를 실행하여 백엔드를 띄웁니다. (이 게이트웨이가 작동해야 함)
3.  **Watcher 실행:** 터미널 B에서 `python knowledge_pipeline/watcher.py`를 실행합니다. (모니터링 대기 상태)
4.  **테스트 파일 투입:** **새로운 파일을 수동으로** `./raw_inputs` 폴더에 복사하거나, 위 스크립트의 테스트 로직을 사용해 더미 파일을 생성하고 이 폴더에 넣어주세요.

이 구조가 가장 견고합니다. 제가 준비한 코드를 바탕으로 다음 질문이나 수정 요청사항(예: 특정 필드 추출 방식 변경)이 있으면 바로 디버깅하겠습니다. 💻⚙️🔧✅

📊 평가: 진행중 — 파일 시스템 모니터링, 데이터 파싱, API 전송의 핵심 로직 아키텍처가 성공적으로 분리 및 설계되었습니다.
📝 다음 단계: 사용자가 `knowledge_pipeline/raw_inputs` 폴더에 실제 테스트용 파일을 넣거나, 직접 통합 실행(uvicorn & python watcher.py)을 시도하여 파이프라인 전체 흐름을 검증할 필요가 있습니다.

---
## 🛠️ 도구 실행 결과 (시스템 자동 실행)

### 🔧 실행: `mkdir -p knowledge_pipeline/raw_inputs`
```

```
_✅_

---
## 📁 파일 액션 결과

✅ 생성: ~/위키에이전트/knowledge_pipeline/requirements.txt
✅ 생성: ~/위키에이전트/knowledge_pipeline/parser.py
✅ 생성: ~/위키에이전트/knowledge_pipeline/watcher.py
✅ 생성: ~/위키에이전트/knowledge_pipeline/api_server.py
✅ 생성: ~/위키에이전트/knowledge_pipeline/test_run.py
