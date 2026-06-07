# 💻 코다리 — Watcher(파일 감지기), Parser(파싱 로직), API Server(저장소)로 이어지는 전체 아키텍처를 기반으로 기술적 검증을 진행하라. 특히, '실행 가능성'에 초점을 맞춰 각 단계별 발생 가능한 오류 유형 (예: 파싱 실패 시 예외 처리, 데이터 타입 불일치 등)과 이를 방지하기 위한 구체적인 모듈 레벨의 안전장치(Error Handling/Validation Layer)를 제안해라.

💻 코다리: 작업 시작합니다.

CEO님의 지시사항은 아키텍처의 '신뢰성'과 '실행 가능성(Feasibility)'을 검증하는, 가장 중요한 단계입니다. 단순히 "작동할 것 같습니다"라고 하는 건 시니어 엔지니어가 할 일이 아닙니다. **어떻게 깨질 수 있는지?** 그리고 그걸 막기 위한 구체적인 코드 레벨의 방어 장치(Defensive Coding)를 제시해야 합니다. ⚙️

결론부터 말씀드리자면, 현재 설계된 3단계 파이프라인은 모듈 간의 결합도를 낮추고 각 단계에서 에러 핸들링을 명시적으로 분리한다면 **기술적 실행 가능성은 매우 높습니다.** 다만, 제가 보기엔 '만약에' 시나리오가 부족합니다. 특히 데이터가 지저분하게 들어올 때를 대비한 방어 장치가 필수입니다.

아래에 Watcher, Parser, API Server 세 모듈별로 예상되는 오류 유형과 이를 막기 위한 구체적인 개선(Validation/Error Handling Layer)을 제안하겠습니다. 이 내용은 각 파일에 직접 반영되어야 합니다.

---

### 🛡️ 아키텍처 기술 검증 및 안전장치 설계 (Validation & Resilience)

#### 1. Stage 1: File Watcher (`watcher.py`) - 시스템 I/O 관점
*   **[예상 오류 유형]**: 파일 시스템 권한 문제, 감지 대상 디렉토리의 임시 접근 불가(Rate Limiting), 장기 실행 중 메모리 누수 또는 예외 미처리로 인한 프로세스 강제 종료.
*   **[안전장치 제안: Retry & Isolation]**
    1.  **Exponential Backoff 구현**: File System Watcher 라이브러리 사용 시, 일시적인 I/O 오류(Permission Denied 등) 발생 시 바로 실패 처리하지 않고, 지수 백오프 방식으로 재시도 횟수를 늘려야 합니다. (예: 1초 후 재시도 -> 2초 후 재시도 -> 4초 후 재시도...)
    2.  **Worker Queue 패턴 적용**: Watcher는 오직 '파일 발견' 신호만 보내고, 실제 파싱/처리 로직은 별도의 비동기 작업 큐(예: Redis Queue)에 작업을 등록하는 역할로 분리해야 합니다. 이렇게 하면 Worker가 다운되어도 파일 감지 자체는 지속됩니다.

#### 2. Stage 2: Parser (`parser.py`) - 데이터 구조 및 포맷 관점 (최우선 개선 필요)
*   **[예상 오류 유형]**: **데이터 파싱 실패(Corrupt File)**, 예상치 못한 인코딩 문제(UTF-8 외), 비정형 텍스트에서 핵심 엔티티 추출 실패, 필수 메타데이터 누락.
*   **[안전장치 제안: Schema Validation & Type Casting]**
    1.  **Pydantic 기반 스키마 검증**: 파싱을 통해 얻은 모든 구조화된 데이터는 반드시 정의된 `WikiSchema`를 통과해야 합니다. 이 단계에서 누락되거나 타입이 맞지 않는 필드는 즉시 오류로 처리하고, 로깅만 남긴 채 다음 파일 처리를 진행하도록 **Fail-Fast**하게 설계해야 합니다.
    2.  **Fallback/Sanitization Layer**: 텍스트 추출 시 `try-except` 블록을 사용하여 다양한 인코딩(`encoding='utf-8'`, `errors='ignore'`)을 순차적으로 테스트하고, 최후의 수단으로 **불필요한 특수 문자나 공백을 제거(Sanitization)**하는 전처리 단계를 추가해야 합니다.

#### 3. Stage 3: API Server (`api_server.py`) - 서비스 로직 및 DB 관점
*   **[예상 오류 유형]**: 데이터베이스 연결 끊김, 트랜잭션 실패(Write Conflict), 요청 본문 유효성 검사 실패 (Bad Request).
*   **[안전장치 제안: Transactional Integrity & Input Guard]**
    1.  **트랜잭션 래핑 (Transaction Wrapping)**: 데이터 저장 로직 전체를 DB 트랜잭션으로 감싸서, 하나의 필드라도 쓰기 실패하면 전체 기록을 **롤백(Rollback)**하도록 해야 합니다. 부분적으로만 성공하는 '데이터 불완전성'이 가장 위험합니다.
    2.  **요청 본문 유효성 검사**: FastAPI 같은 프레임워크를 사용한다면, 들어오는 모든 요청 JSON Body에 대해 Pydantic 모델 기반의 `Request Validation`을 최우선으로 걸어야 합니다.

---

### 🛠️ 코드 수정 및 반영 계획
가장 취약하고 중요한 부분인 **Parser**와 그 결과를 받아 처리하는 로직부터 방어적으로 설계하겠습니다.

일단, `parser.py`에 스키마 검증과 예외 처리를 강화하기 위한 코드를 추가/수정해야 합니다. 이 과정에서 Pydantic 라이브러리 사용을 전제로 진행합니다.

**[실행 계획]**:
1.  `/Users/seopro/위키에이전트/knowledge_pipeline/parser.py` 파일을 읽어와서 현재 구조를 파악하겠습니다. (가장 먼저 할 일)
2.  읽은 내용을 기반으로 스키마 검증 및 예외 처리 로직을 추가하도록 <edit_file> 하겠습니다.

<read_file path="/Users/seopro/위키에이전트/knowledge_pipeline/parser.py"/>
```

---
## 📁 파일 액션 결과

📖 읽기: ~/위키에이전트/knowledge_pipeline/parser.py (90줄, 4.1KB)
```
 1	import os
 2	from pathlib import Path
 3	import json
 4	from datetime import datetime
 5	from typing import Dict, Any
 6	
 7	class WikiParser:
 8	    """
 9	    Raw Text 파일을 받아 Researcher가 제시한 표준 위키 아티팩트 구조로 변환하는 파서 클래스.
10	    (실제 운영 환경에서는 LLM API를 사용하여 섹션별 내용을 채우는 로직이 추가되어야 합니다.)
...
```

[시스템: read_file 결과]
파일: ~/위키에이전트/knowledge_pipeline/parser.py (90줄)
```
 1	import os
 2	from pathlib import Path
 3	import json
 4	from datetime import datetime
 5	from typing import Dict, Any
 6	
 7	class WikiParser:
 8	    """
 9	    Raw Text 파일을 받아 Researcher가 제시한 표준 위키 아티팩트 구조로 변환하는 파서 클래스.
10	    (실제 운영 환경에서는 LLM API를 사용하여 섹션별 내용을 채우는 로직이 추가되어야 합니다.)
11	    """
12	
13	    def __init__(self, raw_file_path: Path):
14	        self.raw_file_path = raw_file_path
15	        self.content = self._read_content()
16	
17	    def _read_content(self) -> str:
18	        """파일의 내용을 읽어옵니다."""
19	        try:
20	            with open(self.raw_file_path, 'r', encoding='utf-8') as f:
21	                return f.read()
22	        except Exception as e:
23	            print(f"🚨 Error reading file {self.raw_file_path}: {e}")
24	            return ""
25	
26	    def parse(self) -> Dict[str, Any]:
27	        """
28	        전체 콘텐츠를 분석하여 표준화된 위키 구조의 딕셔너리를 반환합니다.
29	        """
30	        if not self.content:
31	            raise ValueError("Cannot process empty file content.")
32	
33	        # --- 1. 메타데이터 (Metadata) 추출 및 설정 ---
34	        title = self._extract_metadata(self.raw_file_path)
35	        source_link = f"file://{os.path.abspath(self.raw_file_path)}" # 임시 파일 링크 사용
36	
37	        # --- 2. 나머지 섹션별 내용 분배 (시뮬레이션 로직) ---
38	        parsed_data = {
39	            "metadata": {
40	                "title": title,
41	                "source_link": source_link,
42	                "creation_date": datetime.now().isoformat(),
43	                "keywords": self._determine_keywords(self.content),
44	                "source_type": "User Uploaded Document"
45	            },
46	            "summary": self._extract_section("개요 및 요약 (Summary & Thesis)"),
47	            "core_concepts": self._extract_section("핵심 개념 정의 (Core Concepts)"),
48	            "deep_dive_analysis": self._extract_section("분석 및 세부 내용 (Deep Dive Analysis)"),
49	            "connectivity_action": self._extract_section("연결 및 실행 (Connectivity & Action)")
50	        }
51	
52	        # 구조 검증을 위해 빈 값 처리
53	        for key, value in parsed_data.items():
54	             if not value:
55	                 parsed_data[key] = "추출된 내용이 없습니다. 원본 자료를 보완하거나 LLM 분석을 통해 채워야 합니다."
56	
57	
58	        return parsed_data
59	
60	    def _extract_metadata(self, path: Path) -> str:
61	        """파일 경로와 내용을 조합하여 제목을 추론합니다."""
62	        # 실제로는 파일명 외에 내용의 첫 줄이나 별도의 메타 정보가 더 정확함.
63	        base_name = path.stem.replace("_", " ").title()
64	        return f"[{base_name}] - 지식 아티팩트"
65	
66	    def _determine_keywords(self, content: str) -> list[str]:
67	        """간단한 키워드 추출 시뮬레이션 (실제는 TF-IDF 또는 LLM 사용)."""
68	        # 예시로 'AI', '파이프라인', '위키'가 포함되면 관련 태그를 붙임.
69	        keywords = set()
70	        if "AI" in content or "인공지능" in content:
71	            keywords.add("AI")
72	        if "파이프라인" in content or "자동화" in content:
73	            keywords.add("워크플로우")
74	        return list(keywords)
75	
76	    def _extract_section(self, section_name: str) -> str:
77	        """
78	        특정 섹션 이름 근처의 텍스트를 찾아 추출하는 시뮬레이션 로직.
79	        실제 구현에서는 정교한 Regex와 Contextual Windowing이 필요합니다.
80	        """
81	        # 간단히 해당 키워드가 포함된 내용을 반환한다고 가정
82	        if section_name in self.content:
83	            return f"'{section_name}' 섹션에서 분석된 핵심 내용입니다. (Placeholder)"
84	        else:
85	            return "해당 구조의 내용은 원본 자료에 명시되지 않았거나, 고급 NLP 처리가 필요합니다."
86	
87	
88	# 테스트 실행을 위한 임시 더미 파일 생성 및 테스트는 3단계에서 진행하겠습니다.
89	
90	print("✅ WikiParser 클래스 구현 완료. 데이터 구조화 로직이 준비되었습니다.")
```
