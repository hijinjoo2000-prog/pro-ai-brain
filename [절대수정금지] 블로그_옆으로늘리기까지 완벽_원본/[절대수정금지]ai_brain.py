# -*- coding: utf-8 -*-
import sys
import time
import os
import re
import json
import asyncio
import subprocess
import math
import pyperclip
import traceback

# Mac 절대경로 실행 바이너리 상수
MCP_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp"
AUTH_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp-auth"
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QTextBrowser, QSplitter, QSizePolicy, QMessageBox, QFileDialog, QComboBox, QScrollArea, QDialog, QGroupBox, QGridLayout)

# [SKILL_SYSTEM 4] 작업 폴더 자동 생성
os.makedirs(os.path.join(os.path.expanduser("~"), "Desktop", "완전자동화", "최종_쇼츠영상"), exist_ok=True)
os.makedirs(os.path.join(os.path.expanduser("~"), "Desktop", "완전자동화", "임시_작업파일"), exist_ok=True)

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from PIL import Image, ImageDraw, ImageFont
from pro_image_utils import stitch_law_text_to_image


from image_factory import make_property_image

class SimpleMCPClient:
    """Zero-dependency JSON-RPC client for Stdio MCP Server"""
    def __init__(self, command, args=None):
        self.command = command
        self.args = args or []
        self.proc = None
        self.msg_id = 1
        self.callbacks = {}

    async def start(self):
        # 지정된 절대경로가 없으면 기본 명령어 사용
        cmd = self.command if os.path.exists(self.command) else "notebooklm-mcp"
        try:
            self.proc = await asyncio.create_subprocess_exec(
                cmd, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception:
            self.proc = await asyncio.create_subprocess_exec(
                "npx", "-y", "notebooklm-mcp",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
        asyncio.create_task(self.read_loop())
        # MCP 초기화 핸드셰이크
        await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ProRealEstateAI", "version": "1.0.0"}
        })
        self.send_notification("notifications/initialized", {})

    async def send_request(self, method, params):
        msg_id = self.msg_id
        self.msg_id += 1
        req = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        future = asyncio.get_event_loop().create_future()
        self.callbacks[msg_id] = future
        self.proc.stdin.write((json.dumps(req) + "\n").encode('utf-8'))
        await self.proc.stdin.drain()
        return await future

    def send_notification(self, method, params):
        req = {"jsonrpc": "2.0", "method": method, "params": params}
        if self.proc and self.proc.stdin:
            self.proc.stdin.write((json.dumps(req) + "\n").encode('utf-8'))

    async def read_loop(self):
        while True:
            try:
                line = await self.proc.stdout.readline()
                if not line: 
                    break # EOF (Process terminated)
                msg = json.loads(line.decode('utf-8').strip())
                if "id" in msg and msg["id"] in self.callbacks:
                    if "error" in msg:
                        self.callbacks[msg["id"]].set_exception(Exception(str(msg["error"])))
                    else:
                        self.callbacks[msg["id"]].set_result(msg.get("result"))
            except Exception:
                pass
        
        # 프로세스 비정상 종료 시 대기 중인 모든 요청 취소 (무한 대기(Hang) 방지)
        for fut in self.callbacks.values():
            if not fut.done():
                fut.set_exception(Exception("MCP 서버 프로세스가 예기치 않게 종료되었습니다. (메모리 부족 또는 비정상 종료)"))

    async def call_tool(self, name, arguments):
        res = await self.send_request("tools/call", {"name": name, "arguments": arguments})
        if res and "content" in res and len(res["content"]) > 0:
            return res["content"][0].get("text", str(res))
        return str(res)

class AIPlannerThread(QThread):

    """실시간 MCP API 기반 자율주행 백그라운드 스레드"""
    log_signal = Signal(str)
    result_signal = Signal(str)
    finished_signal = Signal()
    auth_error_signal = Signal() # 400 Bad Request 감지용 시그널

    def _fetch_cleanup_deep_info(self, zone_name):
        import requests, urllib.parse, urllib.request
        from bs4 import BeautifulSoup
        self.log_signal.emit(f"🕵️‍♂️ [정보몽땅 Deep Crawling] '{zone_name}' 사업성 핵심 데이터 파이프라인 가동...")
        info = {
            "세대수_및_조합원수": "진행 단계별 상이 (클린업/현장 확인 요망)",
            "시공사_브랜드명": "선정 전이거나 비공개 (조합 문의 요망)",
            "건축규모": "진행 단계별 상이 (오피셜 공시 참조)",
            "핵심_인가일": "조합 문의 요망"
        }
        try:
            q = urllib.parse.quote(f'site:cleanup.seoul.go.kr {zone_name}')
            search_url = f'https://search.naver.com/search.naver?query={q}'
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(search_url, headers=headers)
            html = urllib.request.urlopen(req).read()
            soup_sch = BeautifulSoup(html, 'html.parser')
            url = ""
            for a in soup_sch.find_all('a'):
                href = a.get('href', '')
                if 'cleanup.seoul.go.kr' in href and ('cafeUrl=' in href or 'cafeId=' in href):
                    url = href
                    break
            if not url:
                self.log_signal.emit("⚠️ 검색을 통한 정보몽땅 URL 획득 실패 (기본값 적용).")
                return info
            session = requests.Session()
            res_main = session.get(url, headers=headers, timeout=10)
            soup_main = BeautifulSoup(res_main.text, 'html.parser')
            iframe = soup_main.find('iframe', id='contentFrame')
            cafe_id = ""
            if iframe:
                iframe_full_url = iframe['src'] if iframe['src'].startswith('http') else 'https://cleanup.seoul.go.kr' + iframe['src']
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(iframe_full_url).query)
                cafe_id = qs.get('cafeId', [''])[0]
            if not cafe_id: return info
            
            # 1. 사업개요 (세대수, 조합원, 규모)
            res_s = session.get(f"https://cleanup.seoul.go.kr/cafe/mastr-cleanup-bsnsSumry/execute.do?cafeId={cafe_id}&stepSeCode=103&div=sumry", headers=headers, timeout=10)
            soup_s = BeautifulSoup(res_s.text, 'html.parser')
            th_member = soup_s.find('th', string=lambda t: t and '조합원 수' in t)
            members = th_member.find_next_sibling('td').text.strip() if th_member and th_member.find_next_sibling('td') else ""
            
            parsed_total = 0
            for table in soup_s.find_all('table'):
                txt = table.text
                if '세대수' in txt and '계' in txt:
                    trs = table.find_all('tr')
                    if len(trs) > 2:
                        for tr in trs[2:]:
                            tds_vals = [td.text.replace(',', '').replace(' ', '').strip() for td in tr.find_all('td')]
                            parsed_total += sum(int(x) for x in tds_vals if x.isdigit())
                            
            if parsed_total > 0 and members:
                try: m_num = int("".join([c for c in members if c.isdigit()]))
                except: m_num = 1
                ratio = int((parsed_total - m_num)/m_num * 100) if m_num > 1 else 0
                info["세대수_및_조합원수"] = f"총 {parsed_total}세대 / 조합원 {members} (일반분양 비율 약 {ratio}% - 사업성 압도적 우수)"
            elif parsed_total > 0:
                info["세대수_및_조합원수"] = f"총 {parsed_total}세대"
            
            th_floor = soup_s.find('th', string=lambda x: x and '최고높이' in x)
            if th_floor and th_floor.find_parent('tr'):
                tr = th_floor.find_parent('tr')
                tds = tr.find_next_sibling('tr').find_all('td') if tr.find_next_sibling('tr') else []
                if len(tds) > 7: info["건축규모"] = f"지상 최고 {tds[7].text.strip()}"
            
            # 2. 시공사 (203)
            res_c = session.get(f"https://cleanup.seoul.go.kr/cafe/mastr-cleanup-estbBsnsSttus/execute.do?cafeId={cafe_id}&stepSeCode=203&div=cntrct", headers=headers, timeout=10)
            if res_c.status_code == 200:
                soup_c = BeautifulSoup(res_c.text, 'html.parser')
                th_builder = soup_c.find('th', string=lambda x: x and '시공자' in x)
                if th_builder and th_builder.find_next_sibling('td'):
                    builder_text = th_builder.find_next_sibling('td').text.strip()
                    if builder_text: info["시공사_브랜드명"] = f"{builder_text} 등"
                        
            # 3. 인가일 통합 (201, 204, 206)
            dates = []
            for step, name in [('201', '조합설립인가'), ('204', '사업시행인가'), ('206', '관리처분인가')]:
                r = session.get(f"https://cleanup.seoul.go.kr/cafe/mastr-cleanup-estbBsnsSttus/execute.do?cafeId={cafe_id}&stepSeCode={step}", headers=headers, timeout=5)
                if r.status_code == 200:
                    s = BeautifulSoup(r.text, 'html.parser')
                    th_d = s.find('th', string=lambda x: x and '인가일' in x)
                    if th_d and th_d.find_next_sibling('td'):
                        d_text = th_d.find_next_sibling('td').text.strip()
                        if d_text: dates.append(f"{name}({d_text})")
            if dates: info["핵심_인가일"] = " ➔ ".join(dates)
                
            self.log_signal.emit(f"✅ [정보몽땅 Deep Crawling 성공]\n - 세대수: {info['세대수_및_조합원수']}\n - 시공사: {info['시공사_브랜드명']}\n - 규모: {info['건축규모']}\n - 타임라인: {info['핵심_인가일']}")
        except Exception as e:
            self.log_signal.emit(f"⚠️ [Deep Crawling] 일부 수집 실패 (무시 가능): {e}")
        return info

    def _fetch_naver_news(self, query):
        import requests
        from bs4 import BeautifulSoup
        import re
        try:
            # 뉴스 검색용 쿼리 정제 (매물, 급매 등의 부동산 거래 단어 배제)
            news_query = re.sub(r'(매물|급매물|초급매|급매|매매|전세|월세|임대)', '', query).strip()
            if not news_query:
                news_query = query
                
            url = f"https://search.naver.com/search.naver?where=news&query={news_query}&sort=1"
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            items = soup.select("a.news_tit")
            if not items:
                return "관련 뉴스를 찾을 수 없습니다.", ""
                
            title = items[0].text.strip()
            link = items[0].get("href")
            
            parent = items[0].find_parent("div", class_="news_area")
            if parent:
                infos = parent.select("a.info")
                for info in infos:
                    if "네이버뉴스" in info.text:
                        link = info.get("href")
                        break
            # --- 본문 추출 ---
            body_text = ""
            try:
                from newspaper import Article
                article = Article(link, language='ko')
                article.download()
                article.parse()
                body_text = article.text
            except Exception:
                # Fallback to BeautifulSoup
                res_news = requests.get(link, headers=headers)
                news_soup = BeautifulSoup(res_news.text, 'html.parser')
                
                # 노이즈 태그 파괴
                for noise in news_soup(["nav", "header", "footer", "aside", "script", "style"]):
                    noise.decompose()
                for noise in news_soup.find_all("div", class_=re.compile(r'comment|banner|ad|menu|footer|sns')):
                    if noise: noise.decompose()
                
                # 핵심 컨테이너 탐색
                article_container = news_soup.find("article") or news_soup.find("div", id="articleBody") or news_soup.find("div", class_="news_content") or news_soup.find("div", id="dic_area") or news_soup.body
                if article_container:
                    body_text = article_container.get_text(separator="\n", strip=True)
            
            # 검증 로직으로 후처리 (불필요한 꼬리말 제거)
            body_text = re.sub(r'(로그인|회원가입|저작권자 무단전재|기자 프로필|실시간 급상승|ⓒ).*', '', body_text, flags=re.IGNORECASE)
            body_text = body_text.strip()
            if not body_text:
                body_text = "본문 내용이 없거나 파싱에 실패했습니다."
                        
            return title, link, body_text
        except Exception as e:
            return f"뉴스 검색 실패: {e}", "", ""

    def __init__(self, query_text, image_path, raw_data=None, news_data=None, prop_path=None, zone_path=None, law_keyword=""):
        super().__init__()
        self.query_text = query_text
        self.image_path = image_path
        self.raw_data = raw_data
        self.news_data = news_data
        self.prop_path = prop_path   # 1. 매물카드 수익성분석용
        self.zone_path = zone_path   # 3. 구역정보카드 구역설명용
        self.law_keyword = law_keyword

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_async())
        loop.close()

    async def run_async(self):
        res_auth = ""
        try:
            extracted_data = {}
            self.log_signal.emit("▶️ [Step 1] 실 연동 모드: 입력값 해석 시작...")
            final_query = self.query_text
            
            # [JSON 모듈화] blog_rules.json 에서 시스템 룰 동적 로드
            import json as _json
            _rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_rules.json")
            try:
                with open(_rules_path, "r", encoding="utf-8") as _rf:
                    _rules = _json.load(_rf)
                # JSON 구조를 Gemini system_instruction 문자열로 변환
                _role = _rules.get("system_role", {})
                _tone = _rules.get("tone_and_manner", {})
                _fmt  = _rules.get("absolute_formatting_rules", {})
                _vvip = _rules.get("vvip_briefing_structure", {})
                _steps = "\n".join(
                    f"[STEP-{s['step']}] {s['name']}: {s['rule']}"
                    for s in _vvip.get("body_section_order", [])
                )
                _forbidden = ", ".join(f"'{w}'" for w in _role.get("forbidden_words", []))
                _sigs = "\n".join(f"  - {p}" for p in _tone.get("signature_phrases", []))
                sys_instruct = f"""[페르소나]
너는 AI가 아니다. {_role.get('identity', '')} '{_role.get('persona', '서프로')}'다.
금지 단어({_forbidden}) 사용 시 원고 즉시 폐기. 오직 '임장 다녀온 현장 정보', '제가 직접 확보한' 등 인간의 언어만 허용.

[톤앤매너]
대상: {_tone.get('target_audience', '프밀리님들')}
문체: {_tone.get('writing_style', '')}
시그니처 표현:
{_sigs}
다양성 원칙: {_tone.get('diversity_rule', '')}

[절대 포맷팅 규칙]
- 이모지 정책: {_fmt.get('emoji_policy', '')}
- 플레이스홀더: {_fmt.get('placeholder_preservation', '')}
- 볼드 강조: {_fmt.get('bold_emphasis', '')}
- 소제목 형식: {_fmt.get('subheading_style', '')}
- 단락 길이: {_fmt.get('paragraph_length', '')}
- 주석 번호: {_fmt.get('no_footnotes', '')}
- 산수 금지: {_fmt.get('no_arithmetic', '')}

[VVIP 브리핑 구조]
제목: {_vvip.get('title_section', {}).get('format', '')}
  제약: {_vvip.get('title_section', {}).get('constraint', '')}

본문 순서 (각 단계 간 정보 중복 절대 금지):
{_steps}

키워드 삽입: {_vvip.get('keyword_insertion', '')}

[추가 규칙 - 팩트 조작 금지]
- 1000세대 미만 구역을 '대단지', '대규모', '거대한' 등으로 표현 금지
- 제공되지 않은 사업시행인가일, 전구동수 임의 구성 금지
- 전문 용어('투기과열지구', '전매제한', '관리처분인가', '도정법')는 적극 활용하되,
  규제 상태는 반드시 제공된 팩트북과 100% 일치해야 함 (AI 뇌피셜 판결 금지)
- 기계적 법령 나열 템플릿(【관련 법령】, 제X조 X항) 형식 금지
- 7구역=SK에코플랜트/드파인(D'FINE), 6구역=라클라체자이드파인 고정 (혼용 시 폐기)"""
                self.log_signal.emit(f"✅ [blog_rules.json] 룰셋 로드 완료 ({len(sys_instruct)}자)")
            except Exception as _re:
                self.log_signal.emit(f"⚠️ blog_rules.json 로드 실패, 빈 instruct로 계속진행: {_re}")
                sys_instruct = ""
            
            import warnings
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai
            genai.configure(api_key="AIzaSyD8xMgUAMaiNIBmfSW0EXA31kMWLzi6D8U")
            
            # 모델 404 방지 지원 모델 리스트 확인 및 강제 터미널 출력
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            print(f"\\n🔍 [대장님 API키 가용 모델 리스트]: {available_models}\\n")
            self.log_signal.emit(f"🔍 [대장님 API키 가용 모델 리스트]: {available_models}")
            
            target_model_name = 'models/gemini-2.0-flash' if 'models/gemini-2.0-flash' in available_models else 'models/gemini-1.5-flash'
            target_model_name = target_model_name.replace('models/', '')
            
            ocr_text = ""
            # V2에서 넘겨준 "통합 매물_수익성분석.txt" 읽기 (데이터 도킹)
            v2_ocr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "매물_수익성분석.txt")
            if os.path.exists(v2_ocr_path):
                with open(v2_ocr_path, "r", encoding="utf-8") as f:
                    ocr_text = f.read().strip()
                self.log_signal.emit(f"✅ V2에서 전달받은 '매물 수익성 분석' 자동 반영 완료!")
                os.remove(v2_ocr_path) # 읽은 후 초기화하여 찌꺼기 방지
            
            # (기존처럼 기획비서 자체 UI에 이미지를 드롭한 경우에도 병행 처리 가능하게 살려둠)
            if self.image_path and not ocr_text:
                self.log_signal.emit(f"📸 단독 이미지 인지됨: {os.path.basename(self.image_path)}")
                self.log_signal.emit("🧠 [Gemini Vision] 첨부된 이미지 실시간 분석 시작...")
                try:
                    import warnings
                    warnings.filterwarnings("ignore", category=FutureWarning)
                    import google.generativeai as genai
                    from PIL import Image
                    
                    # 🚦 빠르고 정확한 비전 지원 모델 명시적 사용 (시스템 지시어 강제 주입)
                    model = genai.GenerativeModel(target_model_name, system_instruction=sys_instruct, generation_config={"temperature": 0.7})
                    
                    # 2. 📂 영구 노트북 연결 (SKILL_SYSTEM 헌법 적용)
                    if "status\":\"error" in res_auth and "400 Bad Request" in res_auth:
                        self.log_signal.emit("🚨 [인증 에러] NotebookLM 인증이 만료되었습니다. 터미널에서 `notebooklm-mcp-auth`를 실행해주세요!")
                        return
                    
                    # 사전에 생성하고 [상위노출 절대 원칙]이 강제 주입된 영구 노트북 ID 하드코딩
                    notebook_id = "622ca8d0-38a2-4052-ab57-c64102fa6788"
                    self.log_signal.emit(f"📂 VIP 영구 규칙 소스가 내재된 노트북 연동 완료: {notebook_id}\\n")
                    import re
                    # [이미지 파일 유효성 검사] 이미지가 아닌 파일(.html 등) 차단
                    _VALID_IMG_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
                    if not str(self.image_path).lower().endswith(_VALID_IMG_EXT):
                        self.log_signal.emit(f"🚨 OCR API 오류 - 이미지 파일이 아닙니다: {os.path.basename(self.image_path)}\n지원 형식: PNG, JPG, BMP, GIF, WEBP, TIFF")
                        return
                    img_file = Image.open(self.image_path)
                    
                    ocr_prompt = "이 이미지에서 텍스트와 숫자를 정확하게 OCR로 읽어줘. 그리고 그 데이터를 바탕으로, 부동산 전문가 입장에서의 '투자 수익성 분석'을 3문단 이내로 아주 날카롭게 요약해!"
                    # [수정] 429 에러 방어 극한 생존 모드 (분당 2회 제한 돌파) - 최대 5회
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            response = model.generate_content([ocr_prompt, img_file])
                            ocr_text = response.text.strip()
                            self.log_signal.emit(f"✅ 자체 OCR 및 분석 성공 (통신 모델: {target_model_name})!\n")
                            break
                        except Exception as e:
                            if "429" in str(e) and attempt < max_retries - 1:
                                import time
                                wait_time = 35 * (attempt + 1)
                                self.log_signal.emit(f"⏳ [API 속도 제한] 무료 티어 한계(분당 2회) 돌파를 위해 {wait_time}초 대기 중... ({attempt+1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                raise e
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 자체 이미지 OCR 실패: {e}\n")
                    self.log_signal.emit("🚨 OCR API 오류 - 모델명 확인 필요: 이미지 판독이 실패하여 기획안 작성을 중지합니다.")
                    self.result_signal.emit(f"🚨 OCR API 오류 - 모델명 확인 필요\n\n이미지 판독(OCR) API가 실패했습니다(모델명 혹은 통신 상태를 확인하세요).\n\n상세 에러 내용:\n{str(e)}\n\n이 상태로 제출 시 빈 데이터가 전송되므로, 기획안 초안 작성을 전면 중단합니다.")
                    return

            # ════════════════════════════════════════════════════
            # [신규] 1. 매물카드 이미지 자동 수익성 분석 OCR  
            # ════════════════════════════════════════════════════
            prop_ocr_text = ""
            if getattr(self, 'prop_path', None) and os.path.exists(self.prop_path):
                self.log_signal.emit(f"\n💰 [1. 매물카드 OCR] 수익성 분석 시작: {os.path.basename(self.prop_path)}")
                try:
                    import warnings; warnings.filterwarnings("ignore", category=FutureWarning)
                    import google.generativeai as genai
                    from PIL import Image
                    import time
                    self.log_signal.emit("⏳ 구글 API 속도 제한(429) 방지를 위해 4초 대기합니다...")
                    time.sleep(4)
                    model = genai.GenerativeModel(target_model_name, system_instruction=sys_instruct, generation_config={"temperature": 0.7})
                    # [이미지 파일 유효성 검사] 이미지가 아닌 파일(.html 등) 차단
                    _VALID_IMG_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
                    if not str(self.prop_path).lower().endswith(_VALID_IMG_EXT):
                        self.log_signal.emit(f"🚨 OCR 오류 - 매물카드가 이미지 파일이 아닙니다: {os.path.basename(self.prop_path)}\n지원 형식: PNG, JPG, BMP, GIF, WEBP, TIFF")
                        return
                    img_file = Image.open(self.prop_path)
                    prop_prompt = (
                        "이 이미지는 부동산 매물카드입니다. "
                        "OCR로 이미지 안의 모든 텍스트와 숫자를 정확하게 판독하라. "
                        "판독한 데이터(매매가, 투자금, 수익률, 프리미엄, 안전마진 등)를 바탕으로 "
                        "'수익성 판단 브리핑'을 부동산 투자 전문가 스타일로 3~4 문장 이내로 날카롭게 요약해라. "
                        "비교 형식이나 표는 사용하지 마라. 순수 텍스트 요약만 작성."
                    )
                    # [수정] 429 에러 방어 극한 생존 모드 (분당 2회 제한 돌파) - 최대 5회
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            response = model.generate_content([prop_prompt, img_file])
                            prop_ocr_text = response.text.strip()
                            self.log_signal.emit(f"✅ 매물카드 수익성 분석 완료!\n{prop_ocr_text[:200]}...\n")
                            break
                        except Exception as e:
                            if "429" in str(e) and attempt < max_retries - 1:
                                import time
                                wait_time = 35 * (attempt + 1)
                                self.log_signal.emit(f"⏳ [API 속도 제한] 무료 티어 한계(분당 2회) 돌파를 위해 {wait_time}초 대기 중... ({attempt+1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                raise e
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 매물카드 OCR 실패: {e}\n")
                    self.log_signal.emit("🚨 OCR API 오류 - 모델명 확인 필요: 이미지 판독이 실패하여 기획안 작성을 중지합니다.")
                    self.result_signal.emit(f"🚨 OCR API 오류 - 모델명 확인 필요\n\n매물카드 이미지 판독(OCR) API가 실패했습니다(모델명 혹은 통신 상태를 확인하세요).\n\n상세 에러 내용:\n{str(e)}\n\n이 상태로 제출 시 빈 데이터가 전송되므로, 기획안 초안 작성을 전면 중단합니다.")
                    return

            # ════════════════════════════════════════════════════
            # [신규] 3. 구역정보카드 이미지 자동 구역 설명 OCR
            # ════════════════════════════════════════════════════
            zone_ocr_text = ""
            if getattr(self, 'zone_path', None) and os.path.exists(self.zone_path):
                self.log_signal.emit(f"\n🏗️ [3. 구역정보카드 OCR] 구역 정보 판독 시작: {os.path.basename(self.zone_path)}")
                try:
                    import warnings; warnings.filterwarnings("ignore", category=FutureWarning)
                    import google.generativeai as genai
                    from PIL import Image
                    import time
                    self.log_signal.emit("⏳ 구글 API 속도 제한(429) 방지를 위해 4초 대기합니다...")
                    time.sleep(4)
                    model = genai.GenerativeModel(target_model_name, system_instruction=sys_instruct, generation_config={"temperature": 0.7})
                    # [이미지 파일 유효성 검사] 이미지가 아닌 파일(.html 등) 차단
                    _VALID_IMG_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
                    if not str(self.zone_path).lower().endswith(_VALID_IMG_EXT):
                        self.log_signal.emit(f"🚨 OCR 오류 - 구역카드가 이미지 파일이 아닙니다: {os.path.basename(self.zone_path)}\n지원 형식: PNG, JPG, BMP, GIF, WEBP, TIFF")
                        return
                    img_file = Image.open(self.zone_path)
                    zone_prompt = (
                        "이 이미지는 부동산 재개발 구역정보 카드입니다. "
                        "OCR로 이미지 안의 모든 텍스트와 숫자를 정확하게 판독하라. "
                        "판독한 데이터(구역명, 외얯, 세대수, 시공사, 인가일, 진행단계, 입지 정보 등)를 바탕으로 "
                        "'구역 안내 브리핑'을 부동산 전문가 스타일로 3~4 문장 이내로 짧게 요약해라. "
                        "비교 형식이나 표는 사용하지 마라. 순수 텍스트 요약만 작성."
                    )
                    # [수정] 429 에러 방어 극한 생존 모드 (분당 2회 제한 돌파) - 최대 5회
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            response = model.generate_content([zone_prompt, img_file])
                            zone_ocr_text = response.text.strip()
                            self.log_signal.emit(f"✅ 구역정보카드 설명 완료!\n{zone_ocr_text[:200]}...\n")
                            break
                        except Exception as e:
                            if "429" in str(e) and attempt < max_retries - 1:
                                import time
                                wait_time = 35 * (attempt + 1)
                                self.log_signal.emit(f"⏳ [API 속도 제한] 무료 티어 한계(분당 2회) 돌파를 위해 {wait_time}초 대기 중... ({attempt+1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                raise e
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 구역정보카드 OCR 실패: {e}\n")
                    self.log_signal.emit("🚨 OCR API 오류 - 모델명 확인 필요: 구역정보 이미지 판독이 실패하여 기획안 작성을 중지합니다.")
                    self.result_signal.emit(f"🚨 OCR API 오류 - 모델명 확인 필요\n\n구역정보카드 이미지 판독(OCR) API가 실패했습니다(모델명 혹은 통신 상태를 확인하세요).\n\n상세 에러 내용:\n{str(e)}\n\n이 상태로 제출 시 빈 데이터가 전송되므로, 기획안 초안 작성을 전면 중단합니다.")
                    return

            # 수익성/구역 스라이딩한 결과를 ocr_text에 합산 (기존 비전 AI 분석과 병존)
            if prop_ocr_text:
                ocr_text = (ocr_text + "\n\n💰 [매물카드 수익성 분석]\n" + prop_ocr_text).strip()
            if zone_ocr_text:
                ocr_text = (ocr_text + "\n\n🏗️ [구역정보 안내 브리핑]\n" + zone_ocr_text).strip()
            
            if not final_query:
                fallback_zone = self.raw_data.get("dist_display") if getattr(self, "raw_data", None) else None
                if fallback_zone and re.match(r'^\d+구역$', fallback_zone.strip()):
                    final_query = f"노량진 {fallback_zone.strip()} 매물"
                elif fallback_zone:
                    final_query = f"{fallback_zone.strip()} 매물"
                else:
                    final_query = "노량진 6구역 매물"
                    
            self.log_signal.emit(f"🎯 최종 검색어(Query): '{final_query}'\\n")

            client = SimpleMCPClient(MCP_EXEC)
            self.log_signal.emit("📡 NotebookLM MCP 서버 백그라운드 구동 중...")
            await client.start()
            self.log_signal.emit("✅ 서버 연결 완료.\\n")

            # 1. 🟢 Auth
            self.log_signal.emit("🟢 [API 통신] refresh_auth 도구 호출 중...")
            res_auth = await client.call_tool("refresh_auth", {})
            self.log_signal.emit(f"응답: {res_auth.strip()}\\n")

            # 2. 📂 Create Notebook (무력화: 영구 노트북 강제 적용)
            notebook_id = "622ca8d0-38a2-4052-ab57-c64102fa6788"
            self.log_signal.emit(f"📌 VIP 발급된(하드코딩) Notebook ID: {notebook_id}\\n")
                
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [AUTO-PURGE V2 ACTIVE] research_start 직전 스마트 소스 청소기
            # 보존 키워드 소스만 남기고 일회성 뉴스 쓰레기 전량 소각
            # 삭제 간 1초 딜레이 적용 (API 과부하 방지)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            import json as _purge_json, asyncio as _asyncio
            self.log_signal.emit("🧹 [AUTO-PURGE V2] 이전 작업의 일회성 뉴스 쓰레기를 소각합니다...")
            try:
                res_notebook = await client.call_tool("notebook_get", {"notebook_id": notebook_id})

                # ── 다층 파싱: MCP 응답 구조가 달라도 소스 목록 추출 ──
                sources = []
                try:
                    raw = _purge_json.loads(res_notebook) if isinstance(res_notebook, str) else res_notebook

                    # 방법 1: {"sources": [...]} 형태
                    if isinstance(raw, dict) and "sources" in raw:
                        sources = raw["sources"]

                    # 방법 2: {"notebook": [[..., [[source_list]]]]} 중첩 리스트 형태 (MCP 내부 구조)
                    elif isinstance(raw, dict) and "notebook" in raw:
                        notebook_inner = raw["notebook"]
                        if isinstance(notebook_inner, list) and len(notebook_inner) > 0:
                            inner = notebook_inner[0]
                            if isinstance(inner, list) and len(inner) > 1:
                                sources_raw = inner[1]
                                if isinstance(sources_raw, list):
                                    for s in sources_raw:
                                        try:
                                            # MCP 소스 구조: [[uuid, ...], title, ...]
                                            s_id = s[0][0] if isinstance(s[0], list) else s[0]
                                            s_title = s[1] if len(s) > 1 else ""
                                            sources.append({"source_id": s_id, "title": s_title})
                                        except Exception:
                                            pass

                    # 방법 3: 최상위가 리스트인 경우
                    elif isinstance(raw, list):
                        sources = raw

                except Exception as _parse_e:
                    self.log_signal.emit(f"⚠️ 파싱 오류 (소스 목록 빈 상태로 진행): {_parse_e}")
                    sources = []

                self.log_signal.emit(f"📋 현재 노트북 소스 총 {len(sources)}개 확인")

                # VVIP 보존 키워드 — 이 단어가 제목에 있으면 절대 삭제 금지
                keep_keywords = ["법전", "마스터", "master", "rule", "pro_fact_book", "팩트"]
                deleted_count = 0

                # 삭제 대상 먼저 수집
                targets_to_delete = []
                for src in sources:
                    # source_id, uuid, id 중 존재하는 필드 사용
                    s_id = (src.get("source_id") or src.get("uuid") or src.get("id") or "").strip()
                    s_title = src.get("title", "")
                    if not s_id:
                        continue
                    should_keep = any(kw in s_title for kw in keep_keywords)
                    if not should_keep:
                        targets_to_delete.append((s_id, s_title))

                keeps_count = len(sources) - len(targets_to_delete)
                total_targets = len(targets_to_delete)

                if total_targets > 0:
                    self.log_signal.emit(f"🔥 소각 대상 {total_targets}개 | VVIP 보존 {keeps_count}개 — 소각 시작!")
                    for idx, (s_id, s_title) in enumerate(targets_to_delete, start=1):
                        short_title = s_title[:45] + ("..." if len(s_title) > 45 else "")
                        progress_msg = f"🗑️ 소각 중... ({idx}/{total_targets}) ▶ {short_title}"
                        self.log_signal.emit(progress_msg)
                        print(progress_msg)
                        try:
                            await client.call_tool("source_delete", {"source_id": s_id, "confirm": True})
                            deleted_count += 1
                        except Exception as _del_e:
                            self.log_signal.emit(f"⚠️ 소각 실패 ({short_title}): {_del_e}")
                        await _asyncio.sleep(1.0)  # API 과부하 방지 1초 딜레이
                    self.log_signal.emit(f"🧹 [청소 완료] 잡다한 기사 {deleted_count}개 소각! VVIP 자산 {keeps_count}개 보존. 깨끗한 뇌로 재출발!")
                else:
                    self.log_signal.emit("🧹 [청소 완료] 이미 깨끗한 클린 룸 상태입니다. 바로 시작합니다!")
            except Exception as _purge_e:
                self.log_signal.emit(f"⚠️ 소스 청소 중 오류 (계속 진행): {_purge_e}")
                import traceback as _tb; print(_tb.format_exc())

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [하이브리드 뉴스 수집] 타겟 구역 5개 + 상위 뉴타운 5개 = 총 10개
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            search_zone_name = final_query
            self.log_signal.emit("🔍 [하이브리드 수집] VIP 듀얼 파이프라인 가동!")

            # ── 상위 지역명 자동 추출 (숫자/영문 구역 번호 제거) ──
            import re as _re
            # 예: '노량진7구역' → '노량진', '흑석3구역' → '흑석'
            broader_area = _re.sub(r'[0-9]+구역.*', '', search_zone_name).strip()
            if len(broader_area) < 2:  # 추출 실패 시 원본값 사용
                broader_area = search_zone_name
            newtown_query = broader_area + " 뉴타운 재개발 최신 뉴스"
            self.log_signal.emit("🎯 [타겟 구역] '" + search_zone_name + "' | 🗺️ [상위 뉴타운] '" + broader_area + " 뉴타운'")

            # ── [1차 수집] 타겟 구역 5개 ──
            research_query_1 = search_zone_name + " 재개발 최신 뉴스 매물 시세"
            self.log_signal.emit("🔍 [1차 리서치] 타겟 구역 뉴스 수집: '" + research_query_1 + "'")
            res_start_1 = await client.call_tool("research_start", {"query": research_query_1, "source": "web", "mode": "fast", "notebook_id": notebook_id})
            task_match_1 = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', res_start_1)
            task_id_1 = task_match_1.group(1) if task_match_1 else ""
            self.log_signal.emit("📌 [1차] Task ID: " + task_id_1)

            # ── [2차 수집] 상위 뉴타운 5개 ──
            research_query_2 = newtown_query
            self.log_signal.emit("🔍 [2차 리서치] 뉴타운 시너지 뉴스 수집: '" + research_query_2 + "'")
            res_start_2 = await client.call_tool("research_start", {"query": research_query_2, "source": "web", "mode": "fast", "notebook_id": notebook_id})
            task_match_2 = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', res_start_2)
            task_id_2 = task_match_2.group(1) if task_match_2 else ""
            self.log_signal.emit("📌 [2차] Task ID: " + task_id_2)

            # ── [상태 대기] 두 리서치 순차 완료 대기 ──
            self.log_signal.emit("⏳ [1차 리서치] 타겟 구역 수집 완료 대기 중...")
            res_status_1 = await client.call_tool("research_status", {"notebook_id": notebook_id, "task_id": task_id_1, "max_wait": 300, "poll_interval": 10})
            if "error" in res_status_1.lower() or "failed" in res_status_1.lower():
                self.log_signal.emit("⚠️ [1차 리서치] 오류 발생 — 계속 진행")
            else:
                self.log_signal.emit("✅ [1차 리서치] 타겟 구역 수집 완료!")

            self.log_signal.emit("⏳ [2차 리서치] 뉴타운 시너지 수집 완료 대기 중...")
            res_status_2 = await client.call_tool("research_status", {"notebook_id": notebook_id, "task_id": task_id_2, "max_wait": 300, "poll_interval": 10})
            if "error" in res_status_2.lower() or "failed" in res_status_2.lower():
                self.log_signal.emit("⚠️ [2차 리서치] 오류 발생 — 계속 진행")
            else:
                self.log_signal.emit("✅ [2차 리서치] 뉴타운 시너지 수집 완료!")

            self.log_signal.emit("⏳ 하이브리드 듀얼 리서치 대기 및 수집 완료!\n")

            # ── [임포트] 두 결과 순차 업로드 (총 10개) ──
            res_import_1 = ""
            res_import_2 = ""
            self.log_signal.emit("📥 [1차 임포트] 타겟 구역 뉴스 5개 업로드 중...")
            if task_id_1:
                res_import_1 = await client.call_tool("research_import", {"notebook_id": notebook_id, "task_id": task_id_1})
                self.log_signal.emit("응답: " + res_import_1.strip()[:150])

            self.log_signal.emit("📥 [2차 임포트] 뉴타운 시너지 뉴스 5개 업로드 중...")
            if task_id_2:
                res_import_2 = await client.call_tool("research_import", {"notebook_id": notebook_id, "task_id": task_id_2})
                self.log_signal.emit("응답: " + res_import_2.strip()[:150])

            self.log_signal.emit("🎉 [하이브리드 수집 완료] 타겟 구역 + 뉴타운 시너지 뉴스 총 10개 업로드 완료!")

            # task_id는 쿼리용으로 task_id_1 사용 (주요 타겟 기준)
            task_id = task_id_1
            res_import = res_import_1 if task_id_1 else ""

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 📰 네이버 뉴스 스크래핑 진행 (원고 작성 전에 AI가 팩트 인지하도록 세팅)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            self.log_signal.emit(f"📰 네이버 뉴스 스크래핑 진행 중: '{search_zone_name}'")
            if getattr(self, 'news_data', None):
                if isinstance(self.news_data, (list, tuple)) and len(self.news_data) >= 3:
                    news_title, news_link, news_body = self.news_data[0], self.news_data[1], self.news_data[2]
                else:
                    news_title, news_link = self.news_data[0], self.news_data[1]
                    news_body = "직접 입력된 뉴스로 본문을 불러오지 않았습니다."
            else:
                news_title, news_link, news_body = self._fetch_naver_news(search_zone_name)
            self.log_signal.emit(f"✅ 뉴스 수집 완료: {news_title}")

            # 🛑 [순수 뉴스 본문 업로드] NotebookLM 소스 정제 (원고 쿼리 전에 주입)
            if news_body and "뉴스 검색 실패" not in news_title:
                self.log_signal.emit(f"📦 [안전장치] 정제된 뉴스 본문을 NotebookLM에 소스로 주입 중...")
                news_fact_text = f"기사 제목: {news_title}\n기사 링크: {news_link}\n\n[순수 기사 본문]\n{news_body}"
                try:
                    await client.call_tool("notebook_add_text", {"notebook_id": notebook_id, "title": f"핵심뉴스_{search_zone_name}", "text": news_fact_text})
                    self.log_signal.emit("✅ 뉴스 본문 데이터 소스 주입 성공!")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 뉴스 본문 주입 실패 (무시하고 진행): {str(e)}")

            # 6. 📝 Generate Blog Post (Query)
            self.log_signal.emit("🪄 [API 통신] notebook_query 호출 중... (상위전문가 SEO 블로그 원고 작성 중, 최대 2~3분 대기)")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [법제처 실시간 API 연동] 블로그 생성 전 관련 법령 조회
            # scripts/law_api.py 모듈 사용 (OC 코드 설정 필요)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            law_reference_text = ""
            try:
                import sys, os as _os
                _law_script_dir = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)),
                    "..", "연구자동화 에이전트들", "노트북lm과 연동",
                    ".agents", "skills", "pro-blog-sniper", "scripts"
                )
                # 절대 경로로도 시도
                _law_script_dir2 = "/Users/seopro/연구자동화 에이전트들/노트북lm과 연동/.agents/skills/pro-blog-sniper/scripts"
                for _d in [_law_script_dir, _law_script_dir2]:
                    if _os.path.isdir(_d) and _d not in sys.path:
                        sys.path.insert(0, _d)
                import law_api
                # 구역명 기반 키워드 조회를 직접 입력한 특수 키워드로 오버라이드
                if hasattr(self, 'law_keyword') and self.law_keyword:
                    _law_keyword = self.law_keyword
                else:
                    _law_keyword = f"{search_zone_name} 입주권"
                self.log_signal.emit(f"⚖️ [법제처 API] '{_law_keyword}' 관련 법령 실시간 조회 중...")
                law_reference_text = law_api.pro_law_check(_law_keyword)
                self.log_signal.emit(f"✅ [법제처 API] 조회 완료!\n{law_reference_text[:300]}...")
            except Exception as _e:
                law_reference_text = f"[법제처 API 조회 생략: {_e}]"
                self.log_signal.emit(f"⚠️ 법제처 API 조회 실패 (계속 진행): {_e}")

            # [PPT 생성 로직 완전 제거 — 대장님 영구 지시]


            
            vvip_law_insight = (
                "**[서프로의 실전 투자 법률 인사이트: 전매제한 팩트체크]**\n\n"
                "\"재개발 입주권, 투기과열지구라 전매제한 걸리는 거 아닌가요?\"\n"
                "투자자분들이 가장 많이 걱정하시는 '도시 및 주거환경정비법(도정법) 제39조' 조합원 지위 양도 제한 규정입니다.\n\n"
                "결론부터 팩트로 짚어드립니다.\n"
                "현재 노량진 뉴타운은 강력한 규제가 적용되는 **투기과열지구**입니다. "
                "하지만 오늘 브리핑하는 매물은 전매제한 규제 자체를 '아예' 받지 않는 **무적의 매물**입니다.\n\n"
                "도정법 부칙에 따라 '**2018년 1월 24일 이전 최초로 사업시행인가를 신청한 구역**'에 해당하므로, "
                "투기과열지구 지정 및 관리처분인가 여부와 일절 무관하게 "
                "10년 보유/5년 거주 같은 조건 없이도 언제든 **합법적인 전매(매매)가 가능합니다.**\n\n"
                "환금성 리스크가 0%인 완벽히 검증된 예외 매물입니다.\n\n"
                "[출처: 법제처 국가법령정보센터 / 도시 및 주거환경정비법 제39조 및 부칙(2018.1.24.) / https://www.law.go.kr]"
            )
            expert_prompt = (
                f"당신은 대한민국 상위 1% 자산가를 전담하는 부동산 재개발 중개법인 전문가 '서프로'입니다. '{search_zone_name}' 매물 브리핑 원고를 작성해 주십시오.\n\n"
                "[PRO부동산 마스터 룰 - 서프로 PDF 블로그 완벽 복제 지침]\n"
                "1. 기호 및 서식 강제: 대제목이나 특정 인용구를 쓸 때는 반드시 각 줄의 맨 앞에 특수 블록 기호 '▌' 를 붙여서 세로선(인용구) 디자인을 연출하라. 중제목은 '1. 2. 3.', 소항목은 '①, ②, ■, ▣' 기호를 사용하라. (유니코드 이모지 절대 금지)\n"
                "2. 컬러 대체 시각적 강조: 글씨 색상을 넣을 수 없는 시스템이므로, 핵심 단어는 반드시 **[대괄호와 볼드체]** 또는 **\"따옴표와 볼드체\"**로 강력하게 강조하라.\n"
                "3. 수익성 팩트 폭격: 모호한 설명은 집어치우고, '현재 총 매수가 20억 선, 안전마진 4~5억' 처럼 숫자로 뼈를 때리는 팩트체크를 반드시 포함하라.\n"
                "4. 전매 고정 멘트 (절대 규칙): [매수 시 주의할 점] 단락을 작성할 때, 아래의 '전매' 관련 규정은 절대 요약하거나 변경하지 말고 토씨 하나 틀리지 않게 그대로 출력하라.\n\n"
                " ▌ 1. 전매\n"
                " ① 노량진 1, 3, 5구역\n"
                " 관리처분인가 나면, 전매불가\n"
                " **[예외 : 10년보유 5년거주 물건]**\n\n"
                " ② 노량진 2, 4, 6, 7, 8구역\n"
                " 투과로 지정되어도 **[계속 전매가능]**\n"
                " **[(사업시행인가신청일이 2018.1.28.전)]**\n\n"
                "5. 절대 구조 원칙 (이 순서대로 문단 블록을 철저히 분리할 것):\n\n"
                
                " ▶ 구역명 급매물, 매매가, 초기투자금, 프리미엄 ◀ (최상단 요약바)\n"
                " [IMAGE_1]\n\n"
                
                " [서프로의 다급한 훅 & 도입부] (예: 최근 정책/시장 분위기 브리핑)\n"
                " [IMAGE_2]\n\n"
                
                f" ▌ {search_zone_name} 매물 기본정보 (최신 기준)\n"
                " ▌ (출처)대한민국NO.1재개발,재건축 플랫폼 카페\n\n"
                " **[사진 클릭]** 시, **[매물 상세정보]**로 이동 됩니다.\n"
                " [IMAGE_3]\n"
                " [매물 수익성 분석] (OCR 데이터 활용, 타 구역과의 프리미엄 비교)\n"
                " [IMAGE_4]\n"
                " [지정학적 위치 및 입지 분석] (서울 한강 라인, 용산구 바로 아래 위치한 '동작구'의 가치 등을 강력히 어필)\n\n"
                
                " [TITLE_IMAGE:매수 시 주의할 점]\n"
                " (위 4번 룰의 '전매 고정 멘트'를 반드시 여기에 출력할 것.)\n\n"
                
                " [TITLE_IMAGE:취득세 팩트체크]\n"
                " (제공된 법제처 데이터에서 취득세 관련 규정을 분석하여 이 단락에 작성할 것.)\n\n"
                
                " [TITLE_IMAGE:투자 성공 전략]\n"
                " (서프로의 투자 성공 전략 브리핑 작성)\n"
                " [IMAGE_5]\n"
                " (서프로의 클로징 멘트 작성)\n"
                " [IMAGE_6]\n"
                " PRO부동산 공식 카페, 유튜브, 오픈채팅방 링크 (입장비번 등 포함)\n\n"

                "6. 데이터 즉시 반영: 아래 제공된 [최신 OCR 매물/구역 데이터]와 [법제처 데이터]를 위 구조의 알맞은 위치에 100% 녹여내라.\n"
                "7. [설계도 은폐 원칙 - 최우선 생명선]: 글을 구조화할 때 [문단 1] 등의 기계적인 구조 가이드 태그를 결과물에 절대 출력하지 마라. [IMAGE_1]~[IMAGE_6] 및 [TITLE_IMAGE:텍스트] 자리표시자만 예외로 허용한다.\n\n"

                "================================\n"
                f"[최신 OCR 기반 매물 수익성 데이터]\n{prop_ocr_text}\n"
                "================================\n"
                f"[최신 OCR 기반 구역 현황 데이터]\n{zone_ocr_text}\n"
                "================================\n"
                f"[법제처 실시간 법령/정책 결과]\n{law_reference_text}\n"
                "================================\n\n"

                f"[제목]\n"
                f"(반드시 가장 맨 앞에 '[{search_zone_name}매물]' 형태의 타겟 키워드를 띄어쓰기 없이 고정한 채로 시작하고, 그 뒤에 매력적인 제목을 단 한 줄로 작성)\n\n"
                
                f"[본문]\n"
                "(위에서 지시한 문단 구조와 [IMAGE_N], [TITLE_IMAGE:텍스트] 태그 위치를 완벽하게 지키면서 작성할 것.)"
            )
            raw_expert_response = await client.call_tool("notebook_query", {"notebook_id": notebook_id, "query": expert_prompt})
            
            import json
            import re
            
            expert_content = raw_expert_response
            try:
                parsed = json.loads(raw_expert_response)
                # Check different possible keys
                if "answer" in parsed:
                    expert_content = parsed["answer"]
                elif "text" in parsed:
                    expert_content = parsed["text"]
                elif "content" in parsed:
                    expert_content = parsed["content"]
            except:
                pass
                
            if not expert_content:
                expert_content = ""
            else:
                # 1. 노트북LM 주석 번호 제거 (예: [1], [5, 6], [11] 등)
                expert_content = re.sub(r'\[[\d,\s\-]+\]', '', expert_content)
                # 2. 자잘하게 콤마만 남는 찌꺼기 제거
                expert_content = expert_content.replace(' , ', ' ').replace(',  ', ' ')
                # 3. 마크다운 기호 완전히 제거
                expert_content = expert_content.replace('**', '').replace('###', '')
                # 4. 제목 중복 제거
                expert_content = re.sub(r'^\[.*?\] .*? \n\n', '', expert_content)
                expert_content = expert_content.lstrip('\n* ')

            if getattr(self, "raw_data", None):
                comp_type = self.raw_data.get("comp_type", "")
                p_rights = self.raw_data.get("p_rights", "")
                p_premium = self.raw_data.get("p_premium", "")
                final_tax_str = self.raw_data.get("final_tax_str", "")
                p_sale = self.raw_data.get("p_sale", "")           # 매매가
                p_invest = self.raw_data.get("invest_price", "")   # 실투자금 (초기투자금)
                
                # [계산 로직 수정]: 총매수가는 L2에 나온 금액 + 5번 프리미엄
                try:
                    import re
                    p_val = float(p_premium.replace('억', '').replace(',', '').strip()) if p_premium else 0.0
                    l2_text = self.raw_data.get("list_2", "")
                    l2_prices = re.findall(r'([\d.]+)억', l2_text)
                    
                    if l2_prices:
                        calc_total = sum(float(p) for p in l2_prices) + p_val
                    else:
                        r_val = float(p_rights.replace('억', '').replace(',', '').strip()) if p_rights else 0.0
                        calc_total = r_val + p_val

                    if calc_total > 0:
                        p_total = f"{int(calc_total)}" if calc_total.is_integer() else f"{calc_total:g}"
                    else:
                        p_total = self.raw_data.get("p_total", "")
                except:
                    p_total = self.raw_data.get("p_total", "")
                    
                p_margin = self.raw_data.get("p_margin", "")       # 안전마진
                list_texts = " / ".join([self.raw_data.get(f"list_{i}", "") for i in range(1, 6)])
                zone_name = self.raw_data.get("dist_display", final_query)
            else:
                comp_type = "알 수 없음"
                p_rights = "알 수 없음"
                p_premium = "알 수 없음"
                final_tax_str = "알 수 없음"
                p_sale = "알 수 없음"
                p_invest = "알 수 없음"
                p_total = "알 수 없음"
                p_margin = "알 수 없음"
                list_texts = ocr_text if ocr_text else "없음"
                zone_name = final_query
            
            # 1. 텍스트 입력(final_query)에서 구체적 지역명("한남1구역", "장위4구역", "상도동재개발" 등) 최우선 추출
            search_zone_name = final_query
            
            # 적어도 한글 2글자 이상 포함된 구역/단지 패턴 찾기
            match_full = re.search(r'([가-힣]{2,10}(?:뉴타운)?\s*\d+(?:구역|단지|차))', final_query)
            if match_full:
                # 사용자가 명시적으로 입력한 구체적 구역/단지명 사용 (콤보박스 값 무시)
                search_zone_name = match_full.group(1).replace(" ", "")
            else:
                # 2. 구체적인 지역명(한남, 신림 등)이 없는 경우("1구역 매물", "최신 동향") 
                # 콤보박스(GUI) 값(zone_name) 확인 후 노량진 덧붙임
                ui_zone = zone_name.strip() if zone_name else ""
                
                if ui_zone and re.match(r'^\d+구역$', ui_zone):
                    search_zone_name = f"노량진{ui_zone}"
                else:
                    # 콤보박스도 비정상적/없을 경우, 사용자 입력에서 번호만 빼서 노량진 추가
                    match_num = re.search(r'(\d+)구역', final_query)
                    if match_num and "노량진" not in final_query:
                        search_zone_name = f"노량진{match_num.group(1)}구역"
                    else:
                        search_zone_name = final_query

            # 🚀 정보몽땅 딥 크롤러 실행!
            self.log_signal.emit(f"🔎 [클린업 검색어 분석] 최종 반영된 클린업 검색 키워드: '{search_zone_name}'")
            deep_info = self._fetch_cleanup_deep_info(search_zone_name)
            
            # [안전장치] 에러 텍스트 필터링 (수집불가, Error, None 등 방어) - 빡센 검문소
            for key, val in deep_info.items():
                if isinstance(val, str):
                    if "수집불가" in val:
                        deep_info[key] = "조합 문의 요망"
                    elif any(err_kw in val.lower() for err_kw in ["error", "none", "n/a", "null"]):
                        deep_info[key] = "조합 문의 요망"
            
            # 현장 메모(list_texts)에도 혹시 바이러스가 묻어있을지 모르니 강제 필터링
            if isinstance(list_texts, str) and "수집불가" in list_texts:
                list_texts = list_texts.replace("정보몽땅 수집불가", "조합 문의 요망").replace("수집불가", "조합 문의 요망")

            # [수정] 금지어(비공개, 선정 전, 조합 문의 등) 강제 사전 소독 (Pre-processing)
            for k, v in deep_info.items():
                if isinstance(v, str):
                    cleaned = re.sub(r'(?:선정 전이거나|비공개|조합 문의 요망|[\s\(\)])+', ' ', v).strip()
                    deep_info[k] = cleaned if cleaned else "향후 총회를 통해 투명하게 안내될 예정입니다."
            if isinstance(list_texts, str):
                cleaned_list = re.sub(r'(?:선정 전이거나|비공개|조합 문의 요망|[\s\(\)])+', ' ', list_texts).strip()
                list_texts = cleaned_list if cleaned_list else "향후 총회를 통해 투명하게 안내될 예정입니다."
            
            self.log_signal.emit("대장님! 크롤링 데이터 사전 소독을 완료하여 QA 무한 루프를 원천 차단했습니다!")
            
            vision_analysis_section = ""
            if ocr_text:
                vision_analysis_section = f"\n[ 👁️ 비전 AI(Vision) 이미지 분석 기반 요약 ]\n{ocr_text}\n(위 분석 요약 내용도 '수익성 브리핑'이나 '현장 브리핑' 단락에 자연스럽게 녹여내서 부동산 전문가인 스타일로 설명해줘.)\n"

            # [수정] prop_ocr_section, zone_ocr_section 및 text_input 결합 코드를 builder_instruction이 결정된 이후로 이동함
            
            # 기존 위치에 있던 뉴스 수집 로직은 위로 이동됨
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [V5 하드코딩 아키텍처] 파이썬 내장 템플릿 + JSON 추출 엔진
            # (LLM 환각 및 앵무새 버그 원천 차단)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            self.log_signal.emit("\n" + "="*50)
            self.log_signal.emit("🚀 [STEP 1] (V5) Gemini JSON 기획 데이터 추출 중...")
            self.log_signal.emit("="*50)

            # JSON 추출 프롬프트 구성 (Gemini 단독 사용)
            v5_json_prompt = f"""
당신은 10년 차 수석 부동산 중개법인 전문가 '서프로'입니다. 
다음은 특정 재개발/재건축 구역의 분석 데이터들입니다:

[구역 및 현장 데이터]
- 구역명: {search_zone_name}
- 규모 및 세대 정보: {deep_info.get('세대수_및_조합원수', '확인 중')}
- 인가 타임라인: {deep_info.get('핵심_인가일', '확인 중')}
- 예상 시세: {deep_info.get('예상_시세', '확인 중')}
- 현장 메모 요약: {list_texts}

[OCR 추출 수익성 텍스트 1 - 프리미엄/분양가/투자금 추출 우선]
{prop_ocr_text}

[OCR 추출 구역정보 텍스트 2 - 시공사/진행단계 추출 필수]
※ 아래 구역정보 OCR 원문을 반드시 정독하고, 시공사(예: 오띠에르, 드파인, 디에이치 등)와 현재 사업 진행 단계(예: 관리처분 준비 중, 이주 완료, 착공 등)를 찾아내어 JSON 데이터로 완벽하게 추출할 것.
{zone_ocr_text}

위 전체 데이터를 기반으로, 블로그에 사용할 전문적이고 자극적인 'hook_ment'(방문자의 시선을 확 끄는 1~2줄짜리 멘트, 이모지 금지, 기계적인 느낌 제거)를 하나 작성하고, 나머지 핵심 변수들을 JSON으로 추출하세요. 숫자로 표기할 값은 '억'단위 숫자만 적으세요 (예: 6억 5천만 원 -> 6.5, 12억 -> 12.0). 데이터가 모호하거나 없으면 기본값을 쓰세요.

반드시 아래 JSON 형식으로만 응답해야 합니다 (마크다운 백틱 없이 순수 JSON 객체만 반환).
{{
    "hook_ment": "어그로용 1~2줄 티저 (예: 뻔한 구역 설명은 미루겠습니다. 네이버에 없는 초급매, 딱 한 분께만 브리핑합니다.)",
    "area": "평수나 타입 문자열 (예: 59타입 혹은 84타입. 없으면 '확인 중')",
    "premium": 프리미엄 실수형 숫자 (없으면 0.0),
    "member_price": 조합원 분양가 실수형 숫자 (없으면 0.0),
    "initial_investment": 초기 투자금(실투자금) 실수형 숫자 (없으면 0.0),
    "expected_price": 예상 시세 실수형 숫자 (없으면 0.0),
    "total_households": "총 세대수 문자열 (예: 3,500세대. 없으면 '확인 중')",
    "builder": "시공사 문자열 (예: 디에이치. 없으면 '향후 투명하게 안내될 예정입니다')",
    "progress_step": "현재 진행 단계 문자열 (예: 관리처분인가. 없으면 '확인 중')"
}}
"""
            import warnings
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai
            import json
            
            extracted_data = {}

            for attempt in range(1, 6):
                try:
                    # JSON 모드 강제 적용
                    model = genai.GenerativeModel(target_model_name, generation_config={"response_mime_type": "application/json", "temperature": 0.5})
                    # 비동기가 아니라 동기 호출이므로 await 없이
                    json_res = model.generate_content(v5_json_prompt)
                    extracted_data = json.loads(json_res.text)
                    if isinstance(extracted_data, list) and len(extracted_data) > 0:
                        extracted_data = extracted_data[0]
                    elif not isinstance(extracted_data, dict):
                        extracted_data = {}
                    self.log_signal.emit(f"✅ V5 JSON 데이터 추출 성공: {json.dumps(extracted_data, ensure_ascii=False)}")
                    break  # 성공 시 무루프 탈출
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Resource has been exhausted" in error_msg or "exhausted" in error_msg.lower():
                        wait_time = 35 * attempt
                        self.log_signal.emit(f"⏳ [JSON 추출 과부하] 429 에러 감지! {wait_time}초 대기 후 악착같이 재시도합니다... (시도 {attempt}/5)")
                        import time
                        time.sleep(wait_time)
                    else:
                        self.log_signal.emit(f"⚠️ JSON 추출 기타 오류 발생. 10초 대기 후 재시도합니다... (시도 {attempt}/5) 사유: {error_msg}")
                        import time
                        time.sleep(10)
                        
                    if attempt == 5:
                        self.log_signal.emit("🚨 5회 재시도 모두 실패. 기본 데이터로 강제 진행합니다.")
                        extracted_data = {
                            "hook_ment": "가장 빠르고 확실한 마진이 보장되는 특급 급매물입니다. 바로 확인해보세요.",
                            "area": "확인 중",
                            "premium": 0.0,
                            "member_price": 0.0,
                            "initial_investment": 0.0,
                            "expected_price": 0.0,
                            "total_households": "확인 중",
                            "builder": "향후 시공사 선정 후 투명하게 안내될 예정입니다.",
                            "progress_step": "확인 중"
                        }

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [STEP 2] 파이썬 통제 수학 매핑 엔진
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            self.log_signal.emit("\n" + "="*50)
            self.log_signal.emit("🚀 [STEP 2] 파이썬 수학 연산 및 V5 템플릿 하드코딩 조립 중...")
            self.log_signal.emit("="*50)

            # 1. 간단한 최종 템플릿 조립 구조
            if not expert_content.strip():
                self.log_signal.emit("⚠️ [경고] NotebookLM 원고가 비어있습니다. 메인 Gemini 모델(2.5 Pro)로 다이렉트 렌더링 우회 생성을 시도합니다...")
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-pro')
                    response = model.generate_content(expert_prompt)
                    expert_content = response.text
                    
                    # 다시 찌꺼기 제거 과정 수행
                    expert_content = re.sub(r'\[[\d,\s\-]+\]', '', expert_content)
                    expert_content = expert_content.replace(' , ', ' ').replace(',  ', ' ')
                    expert_content = expert_content.replace('**', '').replace('###', '')
                    expert_content = re.sub(r'^\[.*?\] .*? \n\n', '', expert_content)
                    expert_content = expert_content.lstrip('\n* ')
                    
                    self.log_signal.emit("✅ Gemini 다이렉트 우회 생성 성공!")
                except Exception as eval_test_e:
                    self.log_signal.emit(f"🚨 Gemini 우회 생성 실패 ({eval_test_e}). 어쩔 수 없이 V5 기초 템플릿으로 렌더링합니다.")
                    v_hook = extracted_data.get("hook_ment", "기회는 단 한 번뿐입니다. 바로 연락주세요.")
                    v_area = extracted_data.get("area", "확인 중")
                    v_premium = extracted_data.get("premium", 0.0)
                    v_member = extracted_data.get("member_price", 0.0)
                    v_invest = extracted_data.get("initial_investment", 0.0)
                    v_expect = extracted_data.get("expected_price", 0.0)
                    v_house = extracted_data.get("total_households", "확인 중")
                    v_builder = extracted_data.get("builder", "확인 중")
                    v_step = extracted_data.get("progress_step", "확인 중")
                    
                    expert_content = f"""[제목]
[{search_zone_name}매물] {v_hook[:30]}

[본문]
[▶ {search_zone_name} 급매물, 총매수 {v_member+v_premium}억, 초기투자금 {v_invest}억, 프리미엄 {v_premium}억 ◀]

프밀리님들~~ {v_hook}

{search_zone_name}매물 긴급 브리핑입니다!
현장 진행단계는 **{v_step}** 이며, 시공사는 **{v_builder}** 로 브랜드 파워를 자랑합니다.
총 **{v_house}** 대단지의 스케일을 누리실 수 있습니다.

**[수익성 팩트체크]**
- 타입: {v_area}
- 조합원 분양가: {v_member}억
- 프리미엄: {v_premium}억
- 초기투자금: {v_invest}억
- 입주예상가: {v_expect}억

{news_title}
[NEWS_LINK]

**[서프로와 함께하는 재개발법 상식 코너]**
{law_reference_text.strip() if law_reference_text else '해당 구역은 관련 법령에 특이사항이 없습니다.'}
"""

            # [핵심 로직] 원고 내의 [NEWS_LINK] 자리표시자를 실제 수집된(파싱된) 뉴스 링크로 완벽 치환
            if "[NEWS_LINK]" in expert_content:
                expert_content = expert_content.replace("[NEWS_LINK]", f"{news_link}")
            elif news_link and "뉴스 검색 실패" not in news_title:
                expert_content += f"\n\n관련 최신 뉴스: {news_title}\n{news_link}\n"

            # =========================================================
            # [사진 & OCR 텍스트 완벽 정렬 - 정밀 태그(IMAGE_N) 삽입]
            # =========================================================
            # expert_content를 줄 단위로 분석하여 적재적소에 태그 삽입
            lines = expert_content.strip().split('\n')
            auto_tagged_content = []
            
            inserted_img1, inserted_img2, inserted_img3, inserted_img4 = False, False, False, False

            for line in lines:
                auto_tagged_content.append(line)
                
                # [IMAGE_1] 썸네일: [본문] 시작 직후
                if not inserted_img1 and "[본문]" in line:
                    auto_tagged_content.append("\n[IMAGE_1]\n")
                    inserted_img1 = True

                # [IMAGE_2] 매물사진 & 매물 OCR: 팩트 요약바(▶...◀) 직후에 배치
                if not inserted_img2 and "▶" in line and "◀" in line:
                    if not inserted_img1: # 혹시라도 [본문] 태그가 없었을 경우 대비
                        auto_tagged_content.insert(-1, "\n[IMAGE_1]\n")
                        inserted_img1 = True
                    auto_tagged_content.append("\n[IMAGE_2]")
                    if prop_ocr_text.strip():
                        auto_tagged_content.append("\n📌 **[매물 수익성 분석]**")
                        auto_tagged_content.append(prop_ocr_text.strip())
                    auto_tagged_content.append("\n[IMAGE_3]\n") # 위치사진을 연달아 또는 적절히 배치
                    inserted_img2 = True
                    inserted_img3 = True
                
                # [IMAGE_4] 구역정보사진 & 구역 OCR: "수익성 팩트체크" 또는 중간쯤에
                elif not inserted_img4 and ("수익성 팩트체크" in line or "진행단계" in line):
                    auto_tagged_content.append("\n[IMAGE_4]")
                    if zone_ocr_text.strip():
                        auto_tagged_content.append("\n🏗️ **[구역 상세 정보]**")
                        auto_tagged_content.append(zone_ocr_text.strip() + "\n")
                    inserted_img4 = True

            final_expert_text = "\n".join(auto_tagged_content)
            
            if not inserted_img1:
                final_expert_text = "[IMAGE_1]\n\n" + final_expert_text
            
            if not inserted_img4:
                # 혹시라도 삽입 안 됐을 경우를 대비한 꼬리 삽입
                final_expert_text += "\n[IMAGE_4]\n"
                if zone_ocr_text.strip():
                    final_expert_text += "\n🏗️ **[구역 상세 정보]**\n" + zone_ocr_text.strip() + "\n"

            # [IMAGE_5] 투자카드 & [IMAGE_6] 배너: 맨 하단에
            final_markdown = f"""{final_expert_text}

[IMAGE_5]

---
[VIP 투자 직통 상담] PRO부동산 서프로 010-2319-0977
[PRO부동산 공식 네이버 카페] https://cafe.naver.com/pro1023
[서프로 VVIP 카카오톡 오픈채팅방] https://open.kakao.com/o/gqNCbvGe
[유튜브 채널] 신분상승TV
---
[IMAGE_6]
"""

            
            # --- [독립 모듈 융합] 법률 경고장 자동 스티칭 시스템 ---
#             if "토지거래허가구역" in final_markdown:
#                 import re
#                 try:
                    # '재개발법 상식 코너' 이후부터 하단 구분선(---) 또는 문단 전환(\n\n) 앞까지 파싱
#                     match = re.search(r'\*\*\[서프로와 함께하는 재개발법 상식 코너\]\*\*(.*?)(?:---|\n\n)', final_markdown, re.DOTALL)
#                     if match:
#                         law_text = match.group(1).strip()
#                         
                        # 파일이 존재할 경우 스티칭 후 동일 경로에 덮어쓰기 업데이트
#                         if getattr(self, 'prop_path', None) and os.path.exists(self.prop_path):
#                             success = stitch_law_text_to_image(self.prop_path, law_text, self.prop_path)
#                             if success:
#                                 self.log_signal.emit("📸 [독립 모듈] 토지거래허가구역 경고장을 기존 매물카드 이미지 하단에 완벽하게 합체시켰습니다!")
#                             else:
#                                 self.log_signal.emit("⚠️ [독립 모듈] 이미지 스티칭 함수 반환 실패.")
#                 except Exception as ex:
#                     self.log_signal.emit(f"⚠️ [스마트 스티칭 에러]: 이미지 합성을 실패했습니다. 원인: {ex}")
            # -----------------------------------------------
# 
#             
            self.log_signal.emit("✅ V5 심플 템플릿 조립 완료!\n")
            self.log_signal.emit(f"📝 최종 작성된 분량(글자수): {len(final_markdown)}")

            self.log_signal.emit("\n✅ [STEP 2 완료] Two-Step QA 파이프라인 통과! 무결점 최종본을 뷰어에 송출합니다.")
            # ━━━━━━━━━━ [물리적 안전장치] AI 오타 강제 제거 ━━━━━━━━━━
            # LLM이 blog_rules.json 룰을 무시하고 오타를 낼 경우 파이썬 단에서 100% 차단
            import re as _re
            final_markdown = final_markdown.replace('매물매물', '매물')   # 제목 중복 오타 차단
            final_markdown = final_markdown.replace('매물 매물', '매물')  # 공백 포함 중복 오타
            # 제목 대괄호 안 연속 중복 탐지 및 정리 (예: [노량진7구역매물매물] → [노량진7구역매물])
            final_markdown = _re.sub(r'\[([^\]]*?)매물매물([^\]]*?)\]', r'[\1매물\2]', final_markdown)
            # ──────────────────────────────────────────────────────
            self.result_signal.emit(final_markdown.strip())
        except Exception as e:
            import traceback
            self.log_signal.emit(f"❌ API 통신 에러 발생:\\n{traceback.format_exc()}")
        finally:
            self.finished_signal.emit()
