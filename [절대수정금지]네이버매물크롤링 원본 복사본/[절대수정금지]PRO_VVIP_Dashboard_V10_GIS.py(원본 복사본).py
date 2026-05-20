import sys
import requests
import json
import os
import time
import re
import urllib.parse
from datetime import datetime, timedelta
import webbrowser

# 데이터 내보내기 모듈
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, 
                             QFormLayout, QGroupBox, QCheckBox, QComboBox, QListWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QTextCursor, QGuiApplication, QColor

# ==========================================
# 📊 정밀 정렬을 위한 커스텀 숫자 아이템
# ==========================================
class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole) or 0) < float(other.data(Qt.UserRole) or 0)
        except:
            return super().__lt__(other)

# ==========================================
# 🚨 환경 상수 유지 🚨
# ==========================================

# === [ 사용자 설정 (API KEY) ] ===
# 여기에 발급받은 Gemini API 키를 입력하세요.
GEMINI_API_KEY = "AIzaSyD8xMgUAMaiNIBmfSW0EXA31kMWLzi6D8U"
# ==================================

TELEGRAM_TOKEN = "8763319926:AAGOEnjczR5e9iox7Bx5lDBSvj-LIniC5w0"
CHAT_ID = "8597355625"

# 동작구 노량진 뉴타운 관련 3개 법정동 - 각 동 좌표까지 포함
DONG_CODES = [
    {"code": "1159010100", "name": "노량진동", "lat": "37.5126839", "lon": "126.9452813"},
    {"code": "1159010200", "name": "상도동",   "lat": "37.5028000", "lon": "126.9421000"},
    {"code": "1159010800", "name": "대방동",   "lat": "37.5008000", "lon": "126.9374000"},
]

# [V10 Patch 4.3] DevTools 직접 추출 - 노량진 뉴타운 1~8구역 redevelopmentAreaNo
# 네이버 URL 패턴: new.land.naver.com/complexes?a=JGB&e=RETAIL&redevelopmentAreaNo={NO}
# ✔️ = 대장님 DevTools 직접 확인 / ⚠️ = 인접 구역 기준 추정
ZONE_REDEV_NOS = {
    "노량진 뉴타운": [
        {"name": "노량진1구역", "redev_no": "1000298"},  # ✔️ 대장님 마스터키
        {"name": "노량진2구역", "redev_no": "1000299"},  # ✔️ 대장님 마스터키
        {"name": "노량진3구역", "redev_no": "1000442"},  # ✔️ 대장님 마스터키
        {"name": "노량진4구역", "redev_no": "1000300"},  # ✔️ 대장님 마스터키
        {"name": "노량진5구역", "redev_no": "1000441"},  # ✔️ 대장님 마스터키
        {"name": "노량진6구역", "redev_no": "1000301"},  # ✔️ 대장님 마스터키
        {"name": "노량진7구역", "redev_no": "1000340"},  # ✔️ 대장님 마스터키
        {"name": "노량진8구역", "redev_no": "1000341"},  # ✔️ 대장님 마스터키
    ],
    "한남 뉴타운": [
        {"name": "한남1구역", "redev_no": "2000101"},
        {"name": "한남2구역", "redev_no": "2000201"},
        {"name": "한남3구역", "redev_no": "2000301"},
    ],
}

# 1. Mac 앱(.app) 파일 저장 경로 절대 안정화
BASE_DIR = os.path.expanduser('~/Desktop/완전자동화')
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

DB_FILE = os.path.join(BASE_DIR, "noryangjin_listings.json")

# [V10 Patch 4.8] 노량진 각 구역 중앙 좌표 하드코딩 (위도, 경도) - 네이버 좌표 은폐 방어용
ZONE_COORDS = {
    "노량진1구역": (37.510821, 126.939720),
    "노량진2구역": (37.511388, 126.938883),
    "노량진3구역": (37.511874, 126.940428),
    "노량진4구역": (37.510255, 126.941655),
    "노량진5구역": (37.510955, 126.941914),
    "노량진6구역": (37.509743, 126.938478),
    "노량진7구역": (37.508502, 126.940561),
    "노량진8구역": (37.510488, 126.937213)
}

# 2. 타겟 지역 사전 (동코드, 위도, 경도)
TARGET_REGIONS = {
    "노량진 뉴타운": {"code": "1159010100", "lat": "37.5126839", "lon": "126.9452813"},
    "한남 뉴타운": {"code": "1117013100", "lat": "37.53322", "lon": "127.0016"},
    "성수 전략정비구역": {"code": "1120011500", "lat": "37.53818", "lon": "127.0506"},
    "흑석 뉴타운": {"code": "1159010500", "lat": "37.5057", "lon": "126.9634"}
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://land.naver.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}
import random
def get_random_ip():
    return f"{random.randint(11,250)}.{random.randint(1,250)}.{random.randint(1,250)}.{random.randint(1,250)}"

phone_cache = {}

# ==========================================
# 🛠 보조 함수들
# ==========================================
def load_history() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 구형 호환: {id: price_int} -> {id: {'price_int': ...}} 로 자동 업그레이드
            upgraded = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    upgraded[k] = v
                else:
                    upgraded[k] = {'price_int': v}  # 구형 데이터 호환
            return upgraded
    return {}

def save_history(data: dict):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def format_price(num_manwon):
    if num_manwon == 0: return "0"
    eok = num_manwon // 10000
    man = num_manwon % 10000
    if man == 0: return f"{eok}억"
    return f"{eok}억 {man}만" if eok > 0 else f"{man}만"

def parse_korean_money(money_str):
    if not isinstance(money_str, str) or money_str == "확인필요" or "(수식)" in money_str: return 0
    val = 0
    s = money_str.replace(" ", "").replace(",", "")
    m_eok = re.search(r'([\d\.]+)억', s)
    if m_eok: val += float(m_eok.group(1)) * 10000
    m_cheon = re.search(r'([\d]+)천', s)
    if m_cheon: val += int(m_cheon.group(1)) * 1000
    m_man = re.search(r'([\d]+)만', s)
    if m_man: val += int(m_man.group(1))
    
    if val == 0:
        only_digits = re.sub(r'[^\d]', '', s)
        if only_digits: return int(only_digits)
    return int(val)

def extract_financials(desc):
    chotu_match = re.search(r'(?:초투|초기투자금|실투자금|실투자|투자금)\s*[:=\-]?\s*([0-9\.]+(?:억\s*[0-9]*천만?|억|천만?|만)?)', desc)
    p_match = re.search(r'(?:피|P|프리미엄|p)\s*[:=\-]?\s*([0-9\.]+(?:억\s*[0-9]*천만?|억|천만?|만)?)', desc, re.IGNORECASE)
    gam_match = re.search(r'(?:감평|감정가|권리가|권액|권리금액|권리)\s*[:=\-]?\s*([0-9\.]+(?:억\s*[0-9]*천만?|억|천만?|만)?)', desc)
    return (chotu_match.group(1).strip() if chotu_match else "확인필요",
            p_match.group(1).strip() if p_match else "확인필요",
            gam_match.group(1).strip() if gam_match else "확인필요")

def get_phone_cached(atcl_no):
    if atcl_no in phone_cache: return phone_cache[atcl_no]
    url = f"https://m.land.naver.com/article/info/{atcl_no}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        match = re.search(r'rltrTelNo\s*:\s*[\'"]([^\'"]+)[\'"]', res.text)
        if match: 
            phone_cache[atcl_no] = match.group(1); return match.group(1)
        match2 = re.search(r'0\d{1,2}-\d{3,4}-\d{4}', res.text)
        if match2: 
            phone_cache[atcl_no] = match2.group(0); return match2.group(0)
    except: pass
    return "확인필요"

# ==========================================
# 🤖 [V6.4] 1단계: LLM 블로그 정형화 모듈
# ==========================================
# GEMINI_API_KEY 는 상단 사용자 설정부에서 전역으로 선언됨.
# 환경변수가 있으면 그것으로 덮어쓰기 (환경변수 우선순위는 전역변수 다음)
_env_key = os.environ.get("GEMINI_API_KEY", "")
if _env_key and GEMINI_API_KEY in ("", "여기에_제미나이_API_키_입력"):
    GEMINI_API_KEY = _env_key

def parse_blog_with_llm(blog_text: str, region_hint: str = "") -> dict:
    """
    [V7.3] 부분 파싱 대신, 오직 '최종 매매가'와 '작성일' 정확도에 올인.
    나머지는 참고용으로만 파싱(선택)
    """
    empty = {"매매가": 0, "초기투자금": 0, "프리미엄": 0, "권리가": 0, "감평가": 0, "작성일": "", "전화": "", "_raw_text": blog_text}
    if not GEMINI_API_KEY or not blog_text:
        return empty

    prompt = f"""다음은 재개발 매물 블로그 글이다. 텍스트를 읽고 아래 JSON 형식으로 파싱해라.
목표 구역 힌트: '{region_hint}'

[ 핵심 3원칙 - 절대 준수 ]
1. 매매가: 무슨 수를 쓰든 '최종 매매가(호가)' 하나만큼은 정확한 단일 숫자로 뽑아내라.
2. 단위 변환: 모든 금액은 반드시 '만원' 단위 정수로 변환해라. (예: 15억->150000, 5억3000만->53000, '피 오억'->50000)
3. 작성일: 본문 맨 앞이나 제목 근처의 글 작성일/게시일을 'YYYY-MM-DD' 형식으로 파싱. 모르면 "".
기타 정보(초투/피 등)는 뽑히면 적되, 애매하면 0으로 비워라.

블로그 본문:
{blog_text[:3500]}

응답 형식 (JSON만 출력, 설명 금지):
{{"매매가": 숫자, "초기투자금": 숫자, "프리미엄": 숫자, "권리가": 숫자, "감평가": 숫자, "작성일": "YYYY-MM-DD", "전화": "010-xxxx-xxxx"}}"""

    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300}}
        r = requests.post(api_url, json=payload, timeout=15)
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            def _to_i(v):
                try: return int(v or 0)
                except: return 0
            
            result = {
                "매매가": _to_i(parsed.get("매매가", 0)),
                "초기투자금": _to_i(parsed.get("초기투자금", 0)),
                "프리미엄": _to_i(parsed.get("프리미엄", 0)),
                "권리가": _to_i(parsed.get("권리가", 0)),
                "감평가": _to_i(parsed.get("감평가", 0)),
                "작성일": str(parsed.get("작성일", "")),
                "전화": str(parsed.get("전화", "")),
                "_raw_text": blog_text
            }
            return result
    except Exception as e:
        pass
    return empty

# [노량진 뉴타운 1~8구역의 대략적인 GIS Bounding Polygon 셋업]
ZONE_GIS_POLYGONS = {
    "1": [(126.9385, 37.5110), (126.9450, 37.5110), (126.9450, 37.5140), (126.9385, 37.5140)],
    "2": [(126.9360, 37.5070), (126.9420, 37.5070), (126.9420, 37.5105), (126.9360, 37.5105)],
    "3": [(126.9310, 37.5065), (126.9370, 37.5065), (126.9370, 37.5115), (126.9310, 37.5115)],
    "4": [(126.9405, 37.5020), (126.9455, 37.5020), (126.9455, 37.5065), (126.9405, 37.5065)],
    "5": [(126.9355, 37.5025), (126.9400, 37.5025), (126.9400, 37.5060), (126.9355, 37.5060)],
    "6": [(126.9300, 37.5005), (126.9350, 37.5005), (126.9350, 37.5050), (126.9300, 37.5050)],
    "7": [(126.9350, 37.4980), (126.9410, 37.4980), (126.9410, 37.5020), (126.9350, 37.5020)],
    "8": [(126.9300, 37.4950), (126.9370, 37.4950), (126.9370, 37.5000), (126.9300, 37.5000)]
}

def is_point_in_polygon(lng, lat, polygon):
    if not lng or not lat:
        return False
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lng <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lng <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def determine_zone_by_gis(lng, lat):
    for zone_num, poly_coords in ZONE_GIS_POLYGONS.items():
        if is_point_in_polygon(lng, lat, poly_coords):
            return str(zone_num)
    return None

def extract_gis_coordinates(naver_item):
    lat = float(naver_item.get('latitude') or naver_item.get('lat') or 0.0)
    lng = float(naver_item.get('longitude') or naver_item.get('lng') or 0.0)
    return lat, lng

# ==========================================
# 🔬 [V6.4] 2단계: 퍼지 매칭 (DNA 비교) 모듈
# ==========================================
# 층수 → 저/중/고 분류 맵
FLOOR_MAP = {"저층": range(1, 4), "중층": range(4, 11), "고층": range(11, 100)}

def _classify_floor(floor_str: str) -> str:
    """'5층' -> '중층', '중층' -> '중층', '고' -> '고층'"""
    if not floor_str: return ""
    s = str(floor_str).strip()
    if s in ("저층", "저"): return "저층"
    if s in ("중층", "중"): return "중층"
    if s in ("고층", "고"): return "고층"
    m = re.search(r'(\d+)', s)
    if m:
        n = int(m.group(1))
        if n <= 3: return "저층"
        if n <= 10: return "중층"
        return "고층"
    return s

def is_same_property(naver_item: dict, blog_json: dict) -> tuple:
    if not isinstance(blog_json, dict): return False, 0.0, "블로그 데이터 오류"

    n_detail = str(naver_item.get('detail_desc', ''))
    b_raw = str(blog_json.get('_raw_text', ''))
    
    # 1. 네이버 공식명칭 및 상세설명 통폐합 스캔
    combined_naver_text = f"{n_apt} {n_detail}"
    
    # 2. V5.2 초강력 하드코어 확장 패턴 (은어, 줄임말 총망라)
    pattern = r"(노량진|상도|대방|본동|성수|한남|흑석)?\s*(뉴타운|재개발|재정비|촉진지구)?\s*(제)?\s*(\d+)\s*(R|r|구역|지구|촉진)"
    zone_match = re.search(pattern, combined_naver_text)
    
    if zone_match:
        zone_num = zone_match.group(4) # 숫자 그룹 (예: 1, 3, 7 등)
    else:
        # 정규식 패턴에서 번호를 잡지 못했을 경우 기존처럼 단순 숫자 의존
        fallback_m = re.search(r'(\d+)', n_apt)
        if fallback_m:
            zone_num = fallback_m.group(1)
        else:
            return False, 0.0, "[조건1 탈락] 네이버 매물명/상세설명에서 어떤 구역 번호도 추출 불가"

    # 블로그 원문 텍스트 내 해당 구역 번호 패턴 검증 (교차 검증)
    blog_zone_match = re.search(rf"(노량진|상도|대방|본동|성수|한남|흑석)?\s*(뉴타운|재개발|재정비|촉진지구)?\s*(제)?\s*({zone_num})\s*(R|r|구역|지구|촉진|차)", b_raw)
    
    if not blog_zone_match:
        # 혹시 위 정규식에도 안 걸리면 기존처럼 가장 단순한 패턴으로 최후 검증
        if not bool(re.search(rf'{zone_num}\s*구역', b_raw)):
            return False, 0.0, f"[조건1 탈락] 블로그 텍스트 내 지정 구역(제{zone_num}구역/R 등) 부재"

    # 여기까지 통과하면 조건1 달성!
    print(f"✅ [조건1 통과] 제{zone_num}구역 텍스트 확인 완료 (은어/줄임말 패스)")

    # ── [조건 2] 총 매매가 오차 ±2000만 원 이내 ──────────
    n_price = int(naver_item.get('price_int', 0) or 0)
    b_price = int(blog_json.get('매매가', 0) or 0)
    
    if b_price == 0:
        return False, 0.0, "[조건2 탈락] LLM이 블로그 매매가 추출 실패"
    
    diff_price = abs(n_price - b_price)
    if diff_price > 2000:
        return False, 0.0, f"[조건2 탈락] 매매가 오차 한도 초과 (N:{n_price}만 vs B:{b_price}만)"

    # ── [조건 3] 날짜 오차 (최대 14일 이내) ──────────
    n_date_str = str(naver_item.get('date', ''))
    b_date_str = str(blog_json.get('작성일', ''))
    
    if not b_date_str:
        return False, 0.0, "[조건3 탈락] 블로그 작성일 파싱 실패"
        
    try:
        from datetime import datetime
        # n_date_str format: YYYY-MM-DD
        n_date = datetime.strptime(n_date_str[:10], "%Y-%m-%d")
        
        # 블로그 작성일은 LLM이 'YYYY-MM-DD'로 줬을 것이라 기대
        import re
        b_date_match = re.search(r'(\d{4})[-. /년]*(\d{1,2})[-. /월]*(\d{1,2})', b_date_str)
        if not b_date_match:
            return False, 0.0, f"[조건3 탈락] 블로그 날짜 형식 인지 불가 ({b_date_str})"
            
        b_year, b_month, b_day = int(b_date_match.group(1)), int(b_date_match.group(2)), int(b_date_match.group(3))
        b_date = datetime(b_year, b_month, b_day)
        
        diff_days = abs((n_date - b_date).days)
        if diff_days > 14:
            return False, 0.0, f"[조건3 탈락] 날짜 차이 초과 (14일 초과: {diff_days}일 오차)"
    except Exception as e:
        return False, 0.0, f"[조건3 탈락] 날짜 파싱 중 오류: {e}"

    success_msg = f"[100% 매칭] {base_name}{zone_num}구역 / 매매가오차 {diff_price}만 / 날짜오차 {diff_days}일"
    return True, 1.0, success_msg
# 캐시: 구역별 블로그 링크 풀 (미리 수집)
_blog_pool: dict = {}  # {zone_num: [links]}

def _fetch_blog_pool_for_zone(region_core, target_zone_num):
    """[V10.2] 특정 구역 블로그 글을 동적으로 수집하여 _blog_pool에 저장 (JSON API 기반 + 상세 로깅)"""
    import requests
    import urllib.parse
    import json
    from datetime import datetime, timedelta

    if not target_zone_num:
        return
        
    if target_zone_num in _blog_pool:
        return
        
    kw = f"{region_core} 매매"
            
    print(f"==========================================")
    print(f"🔍 [{kw}] 블로그 데이터 수집 시작...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://section.blog.naver.com/'
    }
    
    BLACKLIST = ["거래완료", "계약완료", "매매완료", "보류", "완료된", "거래 완료", "계약 완료", "완료"]
    today_ts = datetime.now()
    fourteen_days_ago_ts = (today_ts - timedelta(days=14)).timestamp() * 1000  # API returns timestamp in ms

    collected = []
    total_found = 0
    cut_by_date = 0
    cut_by_blacklist = 0
    
    try:
        # 3페이지 (총 90개) 리서치
        for page in range(1, 4):
            url = f"https://section.blog.naver.com/ajax/SearchList.naver?countPerPage=30&currentPage={page}&keyword={urllib.parse.quote(kw)}&orderBy=recentdate&type=post"
            res = requests.get(url, headers=headers, timeout=10)
            
            # API 응답 클렌징
            clean_text = res.text.replace(")}']", "").strip()
            clean_text = clean_text.lstrip(")]}',\n")
            
            data = json.loads(clean_text)
            items = data.get('result', {}).get('searchList', [])
            total_found += len(items)
            
            if not items:
                break
            
            for item in items:
                blog_id = item.get('blogId')
                log_no = item.get('logNo')
                add_date_ms = item.get('addDate', 0)
                title = item.get('title', "")
                contents = item.get('contents', "")
                
                link = f"https://blog.naver.com/{blog_id}/{log_no}"
                
                if link in collected:
                    continue
                
                # 1. 14일 초과 데이터 컷
                if add_date_ms < fourteen_days_ago_ts:
                    cut_by_date += 1
                    continue
                    
                # 2. 블랙리스트 컷
                full_text = f"{title} {contents}"
                if any(bk in full_text for bk in BLACKLIST):
                    cut_by_blacklist += 1
                    continue
                    
                # [V10 Patch 3.5] 초정밀 거름망: 키워드 컷팅
                valid_kws = ["1구역", "2구역", "3구역", "4구역", "5구역", "6구역", "7구역", "8구역", "재개발", "입주권", "초투", "뉴타운"]
                if not any(kw in full_text for kw in valid_kws):
                    continue
                    
                negative_kws = ["원룸", "전세", "월세", "오피스텔", "임대", "원룸전세", "신축빌라분양"]
                if any(n_kw in full_text for n_kw in negative_kws):
                    continue
                    
                collected.append(link)
            
    except Exception as e:
        print(f"❌ API 오류 발생 ({kw}): {e}")

    # 신뢰 블로그 우선 정렬 후 중복 제거
    trusted_blogs = ['kuk4749', 'partir_12']
    unique = list(dict.fromkeys(collected))
    unique.sort(key=lambda x: any(tb in x for tb in trusted_blogs), reverse=True)
    _blog_pool[target_zone_num] = unique
    
    print(f"🔍 [블로그 수집 완료] {kw}: 14일 컷 {cut_by_date}개, 보류 컷 {cut_by_blacklist}개 -> 총 {len(unique)}개 확보")
    print(f"==========================================")

def deep_blog_search(region, price_int, reg_date_str):
    # 1. 가격 변환 (195000만원 -> 19.5억)
    eok_val = price_int / 10000
    eok_str = f"{eok_val:g}"  # 19.5 or 12 등
    
    # 2. 구역명 정규화: '노량진4구역' -> region_core = '노량진 4구역'
    region_core_raw = region.replace("재정비촉진구역", "").replace("뉴타운", "").strip()
    region_core = re.sub(r'(\D)(\d)', r'\1 \2', region_core_raw)
    region_core = re.sub(r'\s+', ' ', region_core).strip()
    if '구역' not in region_core: region_core = region_core + '구역'
    
    # 타겟 구역 번호 추출
    zone_num_m = re.search(r'(\d+)', region_core)
    target_zone_num = zone_num_m.group(1) if zone_num_m else None
    
    # 네이버 매물 등록일을 datetime 으로 변환
    from datetime import datetime, timedelta
    naver_date = None
    if reg_date_str and reg_date_str != "확인필요":
        try:
            naver_date = datetime.strptime(reg_date_str[:10], "%Y-%m-%d")
        except: pass

    # [V10.2] 동적으로 구역 블로그 글 풀 확보
    if target_zone_num and target_zone_num not in _blog_pool:
        _fetch_blog_pool_for_zone(region_core, target_zone_num)
        
    # _blog_pool에서 해당 구역 링크 가져오기
    pool_links = _blog_pool.get(target_zone_num, [])
    
    # 단건 검색 fallback (만약 풀에 없거나 target_zone_num이 없는 특별 케이스)
    if not pool_links:
        nso_param = "so:sim,p:3m"
        query = f"{region_core} {eok_str}억 매매 -경매"
        url = f"https://search.naver.com/search.naver?where=post&query={urllib.parse.quote(query)}&nso={nso_param}"
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=5)
            pool_links = re.findall(r'href="(https://blog\.naver\.com/[a-zA-Z0-9_]+/\d+)"', res.text)
            pool_links += re.findall(r'href="(https://m\.blog\.naver\.com/[a-zA-Z0-9_]+/\d+)"', res.text)
            pool_links = list(dict.fromkeys(pool_links))
        except:
            pass

    try:
        # 링크 목록 순회 (풀 전체 사용, 최대 30개)
        for link in pool_links[:30]:
            m_link = link.replace("https://blog.naver.com/", "https://m.blog.naver.com/")
            try:
                b_res = requests.get(m_link, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=5)
            except:
                continue
            
            # HTML 태그 및 불필요한 스크립트/스타일 완벽 제거
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(b_res.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ')
            text = re.sub(r'\s+', ' ', text)
            
            # ✅ [V6.9] 거래완료/계약완료/경매 글 완전 배제 (이미 팔린 매물 오탐 차단)
            BLOCK_KEYWORDS = ["경매", "거래완료", "계약완료", "매매완료", "거래 완료", "계약 완료"]
            if any(kw in text for kw in BLOCK_KEYWORDS):
                continue

            
            # DNA 검증: 매매가가 본문에 정확히 언급되는가?
            target_price_strs = [f"{eok_str}억"]
            if eok_val == int(eok_val):
                target_price_strs.append(f"{int(eok_val)}억")
                
            if any(ps in text for ps in target_price_strs):
                idx = -1
                for ps in target_price_strs:
                    idx = text.find(ps)
                    if idx != -1: break
                
                # 구역명 완화 검증
                if target_zone_num:
                    zone_mentioned_in_text = bool(re.search(rf'{target_zone_num}\s*구역', text))
                    if not zone_mentioned_in_text:
                        continue
                    price_context = text[max(0, idx-150):min(len(text), idx+150)]
                    context_zones = re.findall(r'(\d+)\s*구역', price_context)
                    if context_zones and target_zone_num not in context_zones:
                        continue

                chunk = text[max(0, idx - 200):min(len(text), idx + 200)]
                chunk_stripped = chunk.replace(',', '')
                
                val_pattern = r'\s*[:=\-]?\s*(?:약\s*)?([0-9\.]+(?:억\s*[0-9\.]*[천만]*원?|[천만]+원?|))'
                gam_m = re.search(r'(?:감평가|감정평가액|감평|감정가|평가액|권리가액|권리가)' + val_pattern, chunk_stripped)
                gwon_m = re.search(r'(?:권리가|권리자가액|권리금|권리액)' + val_pattern, chunk_stripped)
                p_m = re.search(r'(?:피|P|프리미엄|프리미엄\(P\)|프리미엄P|프리미엄\s*P)' + val_pattern, chunk_stripped, re.IGNORECASE)
                chotu_m = re.search(r'(?:초투|초기투자금|초기투자|실투자금|실투자|투자금|초기자금)' + val_pattern, chunk_stripped)
                phone_m = re.search(r'010[-. ]?\d{3,4}[-. ]?\d{4}', text)
                
                result = {
                    "gam": gam_m.group(1).strip() if gam_m and gam_m.group(1) else "",
                    "gwon": gwon_m.group(1).strip() if gwon_m and gwon_m.group(1) else "",
                    "p": p_m.group(1).strip() if p_m and p_m.group(1) else "",
                    "chotu": chotu_m.group(1).strip() if chotu_m and chotu_m.group(1) else "",
                    "phone": phone_m.group(0).strip() if phone_m else "",
                    "blog_url": m_link,
                    "_raw_text": text[:4000],  # LLM 2차 파싱용 원문 저장
                    "fuzzy_tag": "",
                    "match_ratio": 1.0,
                }

                # LLM 2차 파싱: 정규식이 놓친 필드가 3개 이상이면 Gemini 호출로 보강
                regex_empty_count = sum(1 for k in ["gam","gwon","p","chotu"] if not result[k])
                if regex_empty_count >= 3 and GEMINI_API_KEY:
                    llm_json = parse_blog_with_llm(text, region_hint=region_core)
                    if llm_json.get("프리미엄") and not result["p"]:
                        result["p"] = f"{llm_json['프리미엄']}만"
                    if llm_json.get("초기투자금") and not result["chotu"]:
                        result["chotu"] = f"{llm_json['초기투자금']}만"
                    if llm_json.get("감평가") and not result["gam"]:
                        result["gam"] = f"{llm_json['감평가']}만"
                    if llm_json.get("권리가") and not result["gwon"]:
                        result["gwon"] = f"{llm_json['권리가']}만"
                    if llm_json.get("전화") and not result["phone"]:
                        result["phone"] = llm_json["전화"]
                    dummy_naver = {"apt": region, "price_int": price_int,
                                   "date": reg_date_str}
                    _, ratio, tag = is_same_property(dummy_naver, llm_json)
                    result["fuzzy_tag"] = tag
                    result["match_ratio"] = ratio

                return result
    except Exception as e:
        return None
    return None

# ==========================================
# ⚙️ 스나이퍼 백그라운드 엔진 (QThread)
# ==========================================
class SniperWorker(QThread):
    log_signal = pyqtSignal(str)
    list_signal = pyqtSignal(list)
    item_parsed_signal = pyqtSignal(dict)  # 좌측 실시간 리스트패널용
    article_found_signal = pyqtSignal(dict)  # [V10] 테이블 실시간 행 추가용
    
    def __init__(self, target_region_name="노량진 뉴타운"):
        super().__init__()
        self.running = True
        self.session = requests.Session()
        self.target_region_name = target_region_name

    def fetch_naver_real_estate(self):
        self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 V10 구역 정밀 타격 모드 가동 (redevelopmentAreaNo)!")

        from curl_cffi import requests as c_req
        if not hasattr(self, "m_session"):
            self.m_session = c_req.Session(impersonate="chrome124")

        # =================================================================
        # ✅ [V10 Patch 4.5] 크롬 브라우저 지문 완벽 복제 - WAF 우회 풀세트
        # =================================================================
        hdrs = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://new.land.naver.com/",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
        }

        # ── 세션 워밍업: 메인 페이지 방문 → 쿠키 자연 확보 ────────────
        try:
            warm_hdrs = dict(hdrs)
            warm_hdrs["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            )
            warm_hdrs["Sec-Fetch-Dest"] = "document"
            warm_hdrs["Sec-Fetch-Mode"] = "navigate"
            warm_hdrs["Sec-Fetch-Site"] = "none"
            self.m_session.get(
                "https://new.land.naver.com/", headers=warm_hdrs, timeout=10
            )
            self.log_signal.emit("   🍪 쿠키 워밍업 완료 - 세션 정상 확립")
            time.sleep(random.uniform(1.5, 2.5))
        except Exception as e:
            self.log_signal.emit(f"   ⚠️ 워밍업 스킵: {e}")

        # [V10 Patch 4.0] redevelopmentAreaNo 기반 구역 타겟 리스트
        zone_targets = ZONE_REDEV_NOS.get(self.target_region_name, [])
        if not zone_targets:
            # fallback: 법정동 코드 기반 바운딩박스 방식
            self.log_signal.emit(f"   ⚠️ [{self.target_region_name}] 구역 번호 없음 - 법정동 코드 폴백 사용")
            region_data = TARGET_REGIONS.get(self.target_region_name, {})
            zone_targets = [{
                "name": self.target_region_name,
                "redev_no": None,
                "code": region_data.get("code", ""),
                "lat": region_data.get("lat", "37.51"),
                "lon": region_data.get("lon", "126.94"),
            }]

        all_articles_merged = {}

        # ── 429 백오프 안전 요청 헬퍼 ─────────────────────────────────────
        def safe_get(url, max_try=3):
            for attempt in range(max_try):
                try:
                    r = self.m_session.get(url, headers=hdrs, timeout=15)
                    if r.status_code == 429:
                        wait_sec = 10 * (attempt + 1)   # 10초 → 20초 → 30초
                        self.log_signal.emit(
                            f"   🔴 429 Rate-Limit 감지! → {wait_sec}초 백오프 대기 ({attempt+1}/{max_try})")
                        time.sleep(wait_sec)
                        continue
                    return r
                except Exception as e:
                    self.log_signal.emit(f"   ⚠️ 요청 예외: {e}")
                    time.sleep(3)
            return None
        # ────────────────────────────────────────────────────────────────────

        for zone_idx, zone in enumerate(zone_targets):
            zone_name = zone["name"]
            redev_no  = zone.get("redev_no")

            # ✅ [V10 Patch 4.4] 스나이퍼 호흡법 - 구역 전환 랜덤 딜레이
            if zone_idx > 0:
                breath = random.uniform(2.5, 5.5)
                self.log_signal.emit(
                    f"   ⏳ 사람처럼 위장 중... {breath:.1f}초 대기 (스텔스 유지)")
                time.sleep(breath)

            self.log_signal.emit(f"   📍 [{zone_name}] redevNo={redev_no} 정밀 타격!")

            for page in range(1, 4):   # 3페이지까지 (과부하 방지)
                if redev_no:
                    # =====================================================
                    # ✅ [V10 Patch 4.7] 대장님 1급 기밀 마스터키 장착!
                    # /api/articles/redevelopmentArea/{no} - 51건 실전 검증 완료
                    # articleList 키로 직접 재개발 매물 반환 확인
                    # =====================================================
                    url = (
                        f"https://new.land.naver.com/api/articles/redevelopmentArea/{redev_no}"
                        f"?realEstateType=JGB&tradeType=A1"
                        f"&redevelopmentAreaNo={redev_no}"
                        f"&page={page}&type=list&order=rank"
                    )
                else:
                    # 폴백: 법정동 바운딩박스 (JGB 단독 유지)
                    lat = float(zone.get("lat", 37.51))
                    lon = float(zone.get("lon", 126.94))
                    left_lon  = round(lon - 0.018, 7)
                    right_lon = round(lon + 0.018, 7)
                    top_lat   = round(lat + 0.0056, 7)
                    bot_lat   = round(lat - 0.0056, 7)
                    url = (
                        f"https://new.land.naver.com/api/articles/list"
                        f"?zoom=16"
                        f"&leftLon={left_lon}&rightLon={right_lon}"
                        f"&topLat={top_lat}&bottomLat={bot_lat}"
                        f"&tradeType=A1"
                        f"&realEstateType=JGB"
                        f"&cortarNo={zone.get('code', '')}"
                        f"&page={page}"
                    )

                res = safe_get(url)
                if res is None or res.status_code != 200:
                    code = res.status_code if res else "N/A"
                    self.log_signal.emit(
                        f"   ❌ [{zone_name}] HTTP {code} (page={page}) → 다음 구역")
                    break

                try:
                    data = res.json()
                except Exception:
                    self.log_signal.emit(f"   ⚠️ [{zone_name}] JSON 파싱 실패 - 패스")
                    break

                if not data:
                    self.log_signal.emit(f"   ⚠️ [{zone_name}] 빈 응답 - 패스")
                    break

                # ── 응답 구조 유연 파싱 ──
                result = data if isinstance(data, dict) else {}
                items = (
                    result.get("articleList")
                    or result.get("list")
                    or result.get("complexList")
                    or result.get("body")
                    or (data if isinstance(data, list) else [])
                )

                if not items:
                    self.log_signal.emit(
                        f"   ℹ️ [{zone_name}] page={page} 매물 0건 → 순회 종료")
                    break

                self.log_signal.emit(
                    f"   📦 [{zone_name}] page={page} → {len(items)}건 확보")

                for item in items:
                    # ✅ [V10 Patch 4.7] 실전 검증된 네이버 원본 Key 사용
                    nm   = (item.get('articleName')
                            or item.get('atclNm')
                            or item.get('complexName') or '')
                    feat = (item.get('articleFeatureDesc')          # ✅ 확정 Key
                            or item.get('articleFeatureDescription')
                            or item.get('atclFetrDesc') or '')
                    art_id = str(
                        item.get('articleNo')                       # ✅ 확정 Key
                        or item.get('articleNumber')
                        or item.get('atclNo')
                        or id(item)
                    )

                    if art_id not in all_articles_merged:
                        all_articles_merged[art_id] = item
                        # ✅ 미리보기: 가격 및 날짜 즉시 표시
                        raw_prc = item.get('dealOrWarrantPrc', '')
                        
                        cfm_y = str(item.get('articleConfirmYmd') or item.get('atclCfmYmd') or '')
                        if len(cfm_y) == 8 and cfm_y.isdigit():
                            reg_date = f"{cfm_y[:4]}-{cfm_y[4:6]}-{cfm_y[6:]}"
                        else:
                            reg_date = cfm_y if '-' in cfm_y else '확인중'
                            
                        self.article_found_signal.emit({
                            '_preview': True,
                            'id': art_id,
                            'apt': nm or zone_name,
                            'price': raw_prc,
                            'price_int': 0,
                            'reg_date': reg_date,
                            'agency': item.get('realtorName', ''),  # ✅ 확정 Key
                            'cp_name': item.get('cpName', '확인불가'),
                            'chotu': '',
                            'chotu_int': 0,
                            'p': '',
                            'p_int': 0,
                            'gam_gwon': '',
                            'feat': feat,
                            'blog_url': ''
                        })

                self.log_signal.emit(
                    f"   ✅ [{zone_name}] page={page} → {len(items)}건 통과")

                # ✅ 페이지 간 랜덤 딜레이 (스나이퍼 호흡법)
                page_breath = random.uniform(1.5, 3.0)
                self.log_signal.emit(
                    f"   ⏳ 페이지 호흡 중... {page_breath:.1f}초")
                time.sleep(page_breath)

        final_list = list(all_articles_merged.values())
        self.log_signal.emit(f"   🎯 최종 수집: {len(final_list)}건 (중복 제거)")
        return final_list




    def run_sniper(self, is_first_run=False):
        history = load_history()
        
        # [V10.1] 네이버 매물 우선 스캔 (블로그 사전 수집 제거)
        current_listings = self.fetch_naver_real_estate()
        
        if not self.running or not current_listings: return

        gui_dataset = []
        valid_count = 0
        new_count = 0
        skip_count = 0

        for item in current_listings:
            if not self.running: return
            # ✅ [V10 Patch 4.7] 실전 검증된 네이버 원본 Key 적용
            apt_name = (item.get('articleName')
                        or item.get('atclNm')
                        or item.get('complexName') or '구역명 미상')

            # ✅ articleFeatureDesc 확정 Key 우선 사용
            features = (item.get('articleFeatureDesc')
                        or item.get('articleFeatureDescription')
                        or item.get('atclFetrDesc')
                        or item.get('description') or '특징 없음')

            apt_name = apt_name.replace("재정비촉진구역", "구역")

            # [Fix] 상가/사무실 배제
            real_type = item.get('realEstateTypeName', '') or item.get('rletTpNm', '')
            if ("상가" in apt_name or "점포" in apt_name or "사무실" in apt_name
                    or "상가" in features or "사무실" in real_type or "상가" in real_type):
                continue

            # ✅ articleNo 확정 Key (articleNumber 폴백)
            article_no = str(item.get('articleNo')
                             or item.get('articleNumber')
                             or item.get('atclNo') or '')

            # ✅ dealOrWarrantPrc 확정 Key - 0원 버그 박멸 및 price_info 에러 차단
            price_info = item.get('priceInfo', {})
            raw_prc_str = (item.get('dealOrWarrantPrc')
                           or item.get('tradePrice')
                           or item.get('prc') or '')
            if isinstance(raw_prc_str, str) and '억' in raw_prc_str:
                # "26억", "3억 3,000" 형태 → 만원 단위 정수 변환
                try:
                    raw_clean = raw_prc_str.replace(',', '').replace(' ', '')
                    if '억' in raw_clean:
                        parts = raw_clean.split('억')
                        uk = float(parts[0]) * 10000
                        man = float(parts[1]) if parts[1] else 0
                        price_int = int(uk + man)
                    else:
                        price_int = int(raw_clean) if raw_clean.isdigit() else 0
                except Exception:
                    price_int = 0
            else:
                price_int = price_info.get('dealPrice') or 0
                if isinstance(price_int, str):
                    price_int = int(price_int.replace(',', '')) if price_int.replace(',', '').isdigit() else 0

            if price_int > 10000000:  
                price_int = price_int // 10000
            
            # ✅ [증분 스캔] 이미 처리한 매물이고 가격도 동일하면 → history에서 복원 (API/블로그 재호출 없음)
            cached = history.get(article_no)
            if cached and isinstance(cached, dict) and cached.get('price_int') == price_int and cached.get('art_obj'):
                skip_count += 1
                gui_dataset.append(cached['art_obj'])  # 캐시에서 바로 복원
                self.item_parsed_signal.emit(cached['art_obj'])
                self.article_found_signal.emit(cached['art_obj'])  # [V10-FIX] 캐시도 테이블 실시간 반영
                continue  # 파/블로그 재호출 완전 스킵!

            # ── 신규 매물 또는 가격 변동 매물만 아래 처리 ──
            new_count += 1
            rent_prc = price_info.get('rentPrice') or item.get('rentPrc') or 0
            if isinstance(rent_prc, str):
                rent_prc = int(rent_prc.replace(',', '')) if rent_prc.replace(',', '').isdigit() else 0

            if rent_prc > 10000000:
                rent_prc = rent_prc // 10000
                
            # ✅ [V6.9] 네이버 특징 텍스트 Fallback: rent_prc가 0이더라도 특징/설명란에서 전세/초투 추출 시도
            if rent_prc == 0 and features:
                feat_norm = features.replace(',', '')
                # "전세 5억 안고", "5억 전세", "보증금 5억" 패턴
                jeонse_m = re.search(r'(?:전세|보증금|전세안고|안고|세입자)\s*([0-9.]+)\s*억', feat_norm)
                if jeонse_m:
                    try:
                        rent_from_feat = int(float(jeонse_m.group(1)) * 10000)
                        rent_prc = rent_from_feat
                    except: pass
                # "초투 10억", "실투자 5억" 패턴 (직접 초투가 명시된 경우)
                chotu_feat_m = re.search(r'(?:초투|초기투자금|실투자)\s*([0-9.]+)\s*억', feat_norm)
                if chotu_feat_m:
                    try:
                        naver_chotu_calc = int(float(chotu_feat_m.group(1)) * 10000)
                    except: pass

            display_price = format_price(price_int)
            
            # ✅ realtorName 확정 Key (기존 brokerInfo 폴백 유지)
            broker_info = item.get('brokerInfo', {})
            agency = (item.get('realtorName')
                      or broker_info.get('brokerageName')
                      or broker_info.get('brokerName')
                      or item.get('rltrNm') or '미상')

            # ✅ [V10 Patch 4.8] 경쟁사 출처(cpName) 추출
            cp_name = item.get('cpName') or '확인불가'

            # ✅ articleConfirmYmd 확정 Key (8자리: "20260406" → "2026-04-06")
            cfm_ymd_raw = str(
                item.get('articleConfirmYmd')                # ✅ 확정 Key
                or item.get('atclCfmYmd')
                or item.get('articleConfirmDate')
                or item.get('articleConfirmYMD') or ''
            )
            if len(cfm_ymd_raw) == 8 and cfm_ymd_raw.isdigit():
                cfm_ymd_formatted = f"{cfm_ymd_raw[:4]}-{cfm_ymd_raw[4:6]}-{cfm_ymd_raw[6:]}"
            elif "-" in cfm_ymd_raw:
                cfm_ymd_formatted = cfm_ymd_raw
            else:
                cfm_ymd_formatted = f"20{cfm_ymd_raw[:2]}-{cfm_ymd_raw[2:4]}-{cfm_ymd_raw[4:6]}" if len(cfm_ymd_raw) == 6 else "확인필요"

            # ✅ [V6.8 90일 컷 로직 추가] 3개월 지난 네이버 원본 매물 필터링
            if cfm_ymd_formatted != "확인필요":
                try:
                    cfm_date = datetime.strptime(cfm_ymd_formatted[:10], "%Y-%m-%d")
                    if (datetime.now() - cfm_date) > timedelta(days=90):
                        continue
                except:
                    pass

            chotu_val, p_val, gam_gwon_val = extract_financials(features)

            # ✅ [V6.5 STEP1] 네이버 초기투자금 강제 역산: 매매가 - 보증금(전세/월세)
            # 재개발 조합원 매물은 보증금=현 세입자 전세보증금이 대부분
            naver_chotu_calc = price_int - rent_prc if rent_prc > 0 else price_int
            
            phone_num = get_phone_cached(article_no)
            blog_url_val = ""
            is_match = False
            fuzzy_tag = ""

            # 🔥 [V6.5] 블로그 교집합 검증 → LLM 파싱 → 퍼지 DNA 매칭
            blog_data = deep_blog_search(apt_name, price_int, cfm_ymd_formatted)
            if blog_data:
                blog_url_val = blog_data.get('blog_url', '')

                # LLM JSON으로 퍼지 매칭 시도
                llm_json = parse_blog_with_llm(
                    blog_data.get('_raw_text', ''),  # deep_blog_search가 저장한 원문
                    region_hint=apt_name
                ) if GEMINI_API_KEY else {}

                # ── [V5.2 업데이트] 상세 설명 검증 및 보완 ──
                detail_desc = ""
                # 특징 정보가 너무 짧거나 구역 패턴이 없을 경우 상세 정보 로드
                if not features or len(features) < 10 or not re.search(r"([1-8])\s*(R|r|구역|지구|촉진)", features):
                    try:
                        self.log_signal.emit(f"   🔎 [{apt_name}] 매물 특징 부족, 상세 설명(Detail) 로드 시도...")
                        hdrs = self._get_fin_headers()
                        detail_res = self.session.get(f"https://fin.land.naver.com/front-api/v1/article/detail/{article_no}", headers=hdrs, timeout=5)
                        if detail_res.status_code == 200:
                            dj = detail_res.json()
                            if dj.get("isSuccess"):
                                dd = dj.get("result", {}).get("detail", {})
                                detail_desc = dd.get("articleDescription") or ""
                                self.log_signal.emit(f"   ✅ 상세 설명 획득 ({len(detail_desc)}자)")
                    except Exception:
                        pass

                # ── [V9 핵심] is_same_property GIS 엔진 연동 ──
                # ✅ [V10 Patch 4.8] 좌표 0 매물 강제 매핑 엔진 (은폐 무력화)
                import math
                n_lat = float(item.get('latitude') or item.get('lat') or 0.0)
                n_lng = float(item.get('longitude') or item.get('lng') or 0.0)
                
                if n_lat == 0.0 or n_lng == 0.0 or math.isnan(n_lat) or math.isnan(n_lng):
                    for z_name, (z_lat, z_lng) in ZONE_COORDS.items():
                        if z_name in apt_name.replace(" ", ""):
                            n_lat, n_lng = z_lat, z_lng
                            break

                naver_for_match = {
                    'apt':         apt_name,
                    'price_int':   price_int,
                    'date':        cfm_ymd_formatted,
                    'feature':     features,
                    'detail_desc': detail_desc,
                    'latitude':    n_lat,
                    'longitude':   n_lng
                }
                
                # 블로그 JSON 연동 페일세이프
                if not llm_json.get('매매가') and blog_data:
                    llm_json = {
                        '매매가': 0,
                        '작성일': '',
                        '_raw_text': blog_data.get('_raw_text', '')
                    }

                is_match, match_ratio, fuzzy_tag = is_same_property(naver_for_match, llm_json)

                if is_match:
                    self.log_signal.emit(
                        f"🤖 [{apt_name}] DNA매칭 성공! {fuzzy_tag[:60]}")
                    
                    # [V8.0 비파괴 보조지표 매핑] 네이버 데이터는 훼손하지 않음
                    blog_chotu = int(llm_json.get('초기투자금', 0))
                    blog_p = int(llm_json.get('프리미엄', 0))
                    
                    if chotu_val == "확인필요" and blog_chotu > 0:
                        chotu_val = format_price(blog_chotu) + " (B)"
                    if p_val == "확인필요" and blog_p > 0:
                        p_val = format_price(blog_p) + " (B)"

                else:
                    self.log_signal.emit(
                        f"⚠️ [{apt_name}] 블로그 발견됐으나 DNA불일치: {fuzzy_tag[:60]}")
                    blog_url_val = "" # 매칭 실패하면 블로그 URL 무효화
            else:
                is_match = False

            if chotu_val == "확인필요" and rent_prc > 0:
                chotu_val = format_price(naver_chotu_calc) + " (수식)"
                
            chotu_num = parse_korean_money(chotu_val) if chotu_val != "확인필요" else 0
            if "(수식)" in chotu_val: chotu_num = naver_chotu_calc
            
            # [V8.0] (B) 텍스트를 제거하고 순수 숫자만 연산 가능하게 대응
            if "(B)" in chotu_val:
                if not chotu_num: chotu_num = parse_korean_money(chotu_val.replace("(B)", "").strip())
                
            p_num = parse_korean_money(p_val) if p_val != "확인필요" else 0
            if "(B)" in p_val and not p_num:
                p_num = parse_korean_money(p_val.replace("(B)", "").strip())

            time.sleep(0.05)
            
            is_new = article_no not in history or history[article_no].get('price_int', 0) != price_int
            
            # [새 기능] 일치하는 블로그 매물이 신규로 발견되었을 때 자동 푸시 알림!
            if is_new and is_match and not is_first_run:
                self._send_auto_alert(apt_name, display_price, chotu_val, p_val, gam_gwon_val, blog_url_val, article_no, phone_num, agency, features)

            art_obj = {
                'id': article_no, 'apt': apt_name, 'price': display_price, 'price_int': price_int,
                'chotu': chotu_val, 'chotu_int': chotu_num, 'p': p_val, 'p_int': p_num, 
                'gam_gwon': gam_gwon_val,
                'phone': phone_num, 'agency': agency, 'cp_name': cp_name,
                'feat': features, 'calc_invest': naver_chotu_calc, 'reg_date': cfm_ymd_formatted,
                'blog_url': blog_url_val
            }
            gui_dataset.append(art_obj)
            self.item_parsed_signal.emit(art_obj)  # 좌측 실시간 리스트
            self.article_found_signal.emit(art_obj)  # [V10] 테이블 실시간 행 갱신
            
            # ✅ history에 전체 매물 데이터 저장 (다음 실행 때 재호출 없이 복원)
            history[article_no] = {
                'price_int': price_int,
                'art_obj': art_obj
            }

        self.log_signal.emit(f"⚡ 스캔 완료: 신규 {new_count}건 처리 / {skip_count}건 캐시 복원 (API 절약)")
        save_history(history)
        self.list_signal.emit(gui_dataset)

    def _send_auto_alert(self, apt_name, price, chotu, p_val, gam_gwon, blog_url, atcl_id, phone, agency, feat):
        try:
            lines = [
                "🚨 *[블로그 일치 신규 매물 발견!]* 🚨\n",
                f"📍 *{apt_name}*",
                f"💰 *매매가*: {price}",
                f"💵 *초기투자금*: {chotu}",
                f"📈 *프리미엄(P)*: {p_val}",
            ]
            if gam_gwon and gam_gwon != "확인필요":
                lines.append(f"📊 *감평/권리*: {gam_gwon}")
                
            lines.extend([
                f"\n🔗 *블로그 링크*: [이동하기]({blog_url})" if blog_url else "",
                f"📝 *특징*: {feat}",
                f"📞 *연락처*: {phone} ({agency})",
                f"👉 *상세*: [모바일 확인](https://m.land.naver.com/article/info/{atcl_id})"
            ])
            msg = "\n".join(filter(None, lines))
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=3)
        except Exception as e:
            self.log_signal.emit(f"❌ 자동 알림 전송 에러: {e}")

    def run(self):
        try:
            self.log_signal.emit(f"🚀 [VVIP 스나이퍼 스레드 V5] 가동 완료! (타겟: {self.target_region_name})")
            is_first_run = not os.path.exists(DB_FILE)
            if self.running:
                try:
                    self.run_sniper(is_first_run)
                except Exception as e:
                    self.log_signal.emit(f"💥 파싱 오류 발생: {e}")
            self.log_signal.emit("✅ 스캔 완료.")
        except Exception as e:
            self.log_signal.emit(f"💥 치명적 스레드 오류: {e}")

    def stop(self):
        self.running = False


import traceback
def global_exception_handler(exc_type, exc_value, exc_traceback):
    log_path = os.path.join(os.path.expanduser("~"), "Desktop", "crash_log.txt")
    with open(log_path, "a") as f:
        f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unhandled Exception:\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
sys.excepthook = global_exception_handler

# ==========================================
# 🖥 메인 GUI 컨트롤러 (VVIP 대시보드 V5 블로그 융합 에디션)
# ==========================================
class VvipDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 VVIP 큐레이션 대시보드 V10 (실시간 렌더링 GIS 에디션)")
        self.resize(1800, 950)
        self.worker = None
        self._table_id_row_map = {}  # [V10] article_id → row 매핑 (중복 방지)
        self.initUI()
        
        app_inst = QApplication.instance()
        if app_inst: app_inst.aboutToQuit.connect(self.stop_engine)
        self.start_engine()

    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 1. 상단: 제어부
        top_layout = QHBoxLayout()
        lbl = QLabel("🚨 [PRO부동산 V5] 네이버 매물 ↔ 블로그 스텔스 융합 엔진 구동 중")
        lbl.setFont(QFont("Arial", 15, QFont.Bold))
        lbl.setStyleSheet("color: #28a745;")
        top_layout.addWidget(lbl)
        top_layout.addStretch()
        
        btn_start = QPushButton("▶ 엔진 시작"); btn_start.clicked.connect(self.start_engine)
        btn_stop = QPushButton("🛑 엔진 중지"); btn_stop.clicked.connect(self.stop_engine)
        
        # 2. GUI 상단 컨트롤 추가
        self.comboRegion = QComboBox()
        self.comboRegion.addItems(TARGET_REGIONS.keys())
        self.comboRegion.setFont(QFont("Arial", 13))
        
        self.editBudget = QLineEdit()
        self.editBudget.setPlaceholderText("초투 상한선 (예: 10)")
        self.editBudget.setFont(QFont("Arial", 13))
        self.editBudget.setFixedWidth(150)
        self.editBudget.textChanged.connect(self.apply_chotu_filter)
        
        top_layout.addWidget(QLabel("📍 타겟구역:"))
        top_layout.addWidget(self.comboRegion)
        top_layout.addWidget(QLabel("💸 초투상한(억):"))
        top_layout.addWidget(self.editBudget)
        top_layout.addWidget(btn_start)
        top_layout.addWidget(btn_stop)
        layout.addLayout(top_layout)

        # 2. 메인 스플리터
        splitter = QSplitter(Qt.Horizontal)

        # 🚀 [신규 추가] 실시간 매물 현황판
        realtime_group = QGroupBox("⚡ 실시간 수집/발굴 현황")
        realtime_group.setFont(QFont("Arial", 11, QFont.Bold))
        realtime_layout = QVBoxLayout(realtime_group)
        self.realtime_list = QListWidget()
        self.realtime_list.setStyleSheet("""
            QListWidget { background-color: #0d1117; color: #e6edf3; font-size: 13px; border: 1px solid #30363d; border-radius: 5px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #21262d; }
            QListWidget::item:selected { background-color: #1f3a5f; }
        """)
        realtime_layout.addWidget(self.realtime_list)
        splitter.addWidget(realtime_group)
        
        # 🔥 중앙: 매물 테이블 (8개 컬럼으로 확장)
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        # [V10 Patch 4.8] 광고출처 컬럼 추가
        self.table.setHorizontalHeaderLabels(['구역명', '등록일', '매매가', '부동산명', '광고출처', '초투(자동+B)', 'P(피)', '감평/권리가', '특징/블로그설명', '블로그링크'])
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 90)   # 광고출처
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 130)
        self.table.setColumnWidth(9, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellClicked.connect(self.on_table_click)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        splitter.addWidget(self.table)
        
        # 우측: 매물 상세 편집 + 멀티 공유 패널
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        group_edit = QGroupBox("📍 매물 통합 정보 편집")
        group_edit.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout = QFormLayout()
        
        self.edID = QLineEdit(); self.edID.setReadOnly(True)
        self.edRegion = QLineEdit()
        self.edPrice = QLineEdit()
        self.edChotu = QLineEdit()
        self.edP = QLineEdit()
        self.edGamGwon = QLineEdit()
        self.edPhone = QLineEdit()
        self.edAgency = QLineEdit()
        self.edBlogUrl = QLineEdit()
        self.edBlogUrl.setReadOnly(True)
        self.edBlogUrl.setStyleSheet("color: #4da6ff; text-decoration: underline;")
        self.edFeatures = QTextEdit()
        self.edFeatures.setFixedHeight(50)

        form_layout.addRow("매물번호", self.edID)
        form_layout.addRow("구역명", self.edRegion)
        form_layout.addRow("매매가", self.edPrice)
        form_layout.addRow("초투/현금", self.edChotu)
        form_layout.addRow("프리미엄", self.edP)
        form_layout.addRow("감평/권리", self.edGamGwon)
        form_layout.addRow("직통번호", self.edPhone)
        form_layout.addRow("부동산명", self.edAgency)
        form_layout.addRow("블로그링크", self.edBlogUrl)
        form_layout.addRow("상세특징", self.edFeatures)
        group_edit.setLayout(form_layout)
        right_layout.addWidget(group_edit)

        # 멀티 내보내기 Export 패널
        group_export = QGroupBox("📤 외부 공유 (VIP 마케팅)")
        group_export.setFont(QFont("Arial", 11, QFont.Bold))
        export_layout = QVBoxLayout()

        chk_layout = QHBoxLayout()
        self.chk_price = QCheckBox("매매가"); self.chk_price.setChecked(True)
        self.chk_chotu = QCheckBox("초투"); self.chk_chotu.setChecked(True)
        self.chk_p = QCheckBox("P"); self.chk_p.setChecked(True)
        self.chk_gam = QCheckBox("감/권"); self.chk_gam.setChecked(True)
        self.chk_feat = QCheckBox("특징")
        self.chk_phone = QCheckBox("연락처")
        chk_layout.addWidget(self.chk_price); chk_layout.addWidget(self.chk_chotu)
        chk_layout.addWidget(self.chk_p); chk_layout.addWidget(self.chk_gam)
        chk_layout.addWidget(self.chk_feat); chk_layout.addWidget(self.chk_phone)
        export_layout.addLayout(chk_layout)

        btn_kakao = QPushButton("💬 카톡용 요약복사")
        btn_kakao.setStyleSheet("background-color: #FEE500; font-weight: bold; padding: 10px;")
        btn_kakao.clicked.connect(self.copy_kakao)
        
        btn_excel = QPushButton("📊 전체 엑셀 저장")
        btn_excel.setStyleSheet("background-color: #217346; color: white; font-weight: bold; padding: 10px;")
        btn_excel.clicked.connect(self.save_excel)
        
        btn_img = QPushButton("🖼 VIP 명함 생성")
        btn_img.setStyleSheet("background-color: #9370DB; color: white; font-weight: bold; padding: 10px;")
        btn_img.clicked.connect(self.save_image)

        btns_layout = QHBoxLayout()
        btns_layout.addWidget(btn_kakao); btns_layout.addWidget(btn_excel); btns_layout.addWidget(btn_img)
        export_layout.addLayout(btns_layout)
        group_export.setLayout(export_layout)
        right_layout.addWidget(group_export)

        # 로그창
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #1e1e1e; color: #00ff00; padding: 5px;")
        self.log_box.setFixedHeight(150)
        right_layout.addWidget(self.log_box)

        # 텔레그램 전송
        btn_vip = QPushButton("💎 선택 매물 VIP 텔레그램 전송")
        btn_vip.setFont(QFont("Arial", 14, QFont.Bold))
        btn_vip.setStyleSheet("QPushButton { background-color: #0088cc; color: white; padding: 15px; border-radius: 8px; } QPushButton:hover { background-color: #006699; }")
        btn_vip.clicked.connect(self.send_vip_report)
        right_layout.addWidget(btn_vip)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 1000, 500]) 
        layout.addWidget(splitter)

        # ===================================================
        # 🏆 하단: VVIP 베스트5 전용 위젯
        # ===================================================
        best5_group = QGroupBox("🏆 프로부동산 VVIP 맞춤 급매 베스트 5 (초투 10억 이하)")
        best5_group.setFont(QFont("Arial", 12, QFont.Bold))
        best5_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #c9a227;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #0d1117;
                color: #c9a227;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #ffd700;
                font-size: 13px;
            }
        """)
        best5_layout = QVBoxLayout(best5_group)

        self.best5_table = QTableWidget()
        self.best5_table.setColumnCount(7)
        self.best5_table.setHorizontalHeaderLabels([
            '순위', '구역명', '매매가', '실투자금(초투)', 'P(프리미엄)', '감평/권리가', '출처'
        ])
        self.best5_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                color: #e6edf3;
                gridline-color: #30363d;
                font-size: 12px;
                border: none;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #c9a227;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #30363d;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #21262d;
            }
            QTableWidget::item:selected {
                background-color: #1f3a5f;
            }
        """)
        self.best5_table.setFixedHeight(185)
        self.best5_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.best5_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.best5_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.best5_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.best5_table.setColumnWidth(0, 50)
        self.best5_table.setColumnWidth(2, 100)
        self.best5_table.setColumnWidth(3, 115)
        self.best5_table.setColumnWidth(4, 100)
        self.best5_table.setColumnWidth(5, 130)
        self.best5_table.verticalHeader().setVisible(False)
        best5_layout.addWidget(self.best5_table)
        layout.addWidget(best5_group)

    def write_log(self, txt):
        self.log_box.append(txt)
        self.log_box.moveCursor(QTextCursor.End)

    def apply_chotu_filter(self):
        try:
            budget_str = self.editBudget.text().strip()
            if not budget_str:
                for row in range(self.table.rowCount()):
                    self.table.setRowHidden(row, False)
                return
            
            budget_limit = float(budget_str) * 10000  # 10억 -> 100000 (만원)
            
            for row in range(self.table.rowCount()):
                chotu_item = self.table.item(row, 4)
                if not chotu_item:
                    continue
                    
                chotu_text = chotu_item.text().strip()
                if not chotu_text or chotu_text == "-" or chotu_text == "확인필요":
                    self.table.setRowHidden(row, False)
                    continue
                
                nums = re.findall(r'\d+', chotu_text.replace(',', ''))
                if not nums:
                    self.table.setRowHidden(row, False)
                    continue
                    
                total_val = 0
                if "억" in chotu_text:
                    if len(nums) >= 1: total_val += int(nums[0]) * 10000
                    if len(nums) >= 2: total_val += int(nums[1])
                else:
                    if len(nums) >= 1: total_val += int(nums[0])
                
                if total_val <= budget_limit:
                    self.table.setRowHidden(row, False)
                else:
                    self.table.setRowHidden(row, True)
                    
        except Exception as e:
            pass 

    def start_engine(self):
        if self.worker is None or not self.worker.isRunning():
            self.realtime_list.clear()     # 좌측 리스트 초기화
            self.table.setRowCount(0)      # [V10] 테이블도 초기화
            self._table_id_row_map.clear() # [V10] 행 매핑 초기화
            target_name = self.comboRegion.currentText()
            self.worker = SniperWorker(target_name)
            self.worker.log_signal.connect(self.write_log)
            self.worker.list_signal.connect(self.populate_table)     # [V10-FIX] 최종 전체 테이블 플러시
            self.worker.item_parsed_signal.connect(self.append_realtime_item)
            self.worker.article_found_signal.connect(self.add_single_item_to_table)  # 실시간 행
            self.worker.start()

    def _update_best5_only(self, articles: list):
        """[V10] 배치 완료 후 Best5 위젯만 갱신 (테이블은 실시간 렌더링으로 이미 채워져 있음)"""
        BEST5_CHOTU_LIMIT = 100000
        candidates = []
        for art in articles:
            chotu_int = art.get('chotu_int', 0) or 0
            price_int = art.get('price_int', 0) or 0
            effective_chotu = chotu_int if chotu_int > 0 else price_int
            if 0 < effective_chotu <= BEST5_CHOTU_LIMIT:
                candidates.append({**art, '_eff_chotu': effective_chotu})
        def best5_sort_key(a):
            p_int = a.get('p_int', 0) or 0
            price_int = a.get('price_int', 0) or 0
            return (p_int if p_int > 0 else 9999999, price_int if price_int > 0 else 9999999)
        candidates.sort(key=best5_sort_key)
        self.update_best5(candidates[:5])

    def add_single_item_to_table(self, art: dict):
        """[V10] 매물 1건을 테이블에 실시간으로 추가/갱신한다."""
        try:
            art_id = art.get('id', '')
            is_preview = art.get('_preview', False)
            
            apt_text = art.get('apt', '')
            reg_date = art.get('reg_date', '')
            price_str = art.get('price', '수집 중...' if is_preview else '')
            agency = art.get('agency', '')
            chotu_str = art.get('chotu', '')
            p_str = art.get('p', '')
            gam_gwon = art.get('gam_gwon', '')
            feat = art.get('feat', '')
            blog_url = art.get('blog_url', '')

            self.table.setSortingEnabled(False)
    
            if art_id and art_id in self._table_id_row_map:
                # 이미 존재하는 행이면 갱신 (미리보기 → 최종 데이터로 업데이트)
                item_col0 = self._table_id_row_map[art_id]
                row = item_col0.row()
            else:
                # 신규 행 추가
                row = self.table.rowCount()
                self.table.insertRow(row)
                item_col0 = QTableWidgetItem(apt_text)
                if art_id:
                    self._table_id_row_map[art_id] = item_col0
                self.table.setItem(row, 0, item_col0)
            
            item_col0.setText(apt_text)
    
            self.table.setItem(row, 1, QTableWidgetItem(reg_date))
    
            itm_price = NumericItem(price_str)
            itm_price.setData(Qt.UserRole, art.get('price_int', 0))
            self.table.setItem(row, 2, itm_price)
    
            self.table.setItem(row, 3, QTableWidgetItem(agency))
            self.table.setItem(row, 4, QTableWidgetItem(art.get('cp_name', '확인불가')))
    
            itm_chotu = NumericItem(chotu_str)
            itm_chotu.setData(Qt.UserRole, art.get('chotu_int', 0))
            self.table.setItem(row, 5, itm_chotu)
    
            itm_p = NumericItem(p_str)
            itm_p.setData(Qt.UserRole, art.get('p_int', 0))
            self.table.setItem(row, 6, itm_p)
    
            self.table.setItem(row, 7, QTableWidgetItem(gam_gwon))
            self.table.setItem(row, 8, QTableWidgetItem(feat))
    
            blog_display = "✅ 블로그 확보" if blog_url else ("⏳ 분석 중" if is_preview else "")
            itm_blog = QTableWidgetItem(blog_display)
            if blog_url:
                itm_blog.setBackground(QColor(40, 120, 60))
            self.table.setItem(row, 9, itm_blog)
    
            # 행 0번 셀에 id/phone/blog_url 메타 저장
            item_col0.setData(Qt.UserRole, {
                'id': art_id,
                'phone': art.get('phone', '확인필요'),
                'blog_url': blog_url
            })

            # 실시간 추가 중에도 "등록일" 최신순 정렬 유지 
            self.table.setSortingEnabled(True)
            self.table.sortItems(1, Qt.DescendingOrder)
    
            # 방금 추가된 행이 보이도록 스크롤 (정렬 후 변동된 위치 반영)
            final_row = item_col0.row()
            self.table.scrollToItem(self.table.item(final_row, 0))
            
            # [V10.1] GUI 강제 새로고침
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
        except Exception as e:
            import traceback
            print(f"[에러] UI 실시간 렌더링 에러 (add_single_item_to_table): {e}")
            traceback.print_exc()

    def append_realtime_item(self, art: dict):
        if art.get('_preview'): return  # 예비 데이터는 좌측 패널에 표시 안 함
        text = f"📍 {art.get('apt','')}\n💰 매매: {art.get('price','-')} | 💵 초투: {art.get('chotu','-')}\n📈 P: {art.get('p','-')} | 📞 {art.get('agency','미상')}"
        if art.get('blog_url'):
            text += "\n🔗 [블로그 분석 매칭 완료]"
        from PyQt5.QtWidgets import QListWidgetItem
        item_w = QListWidgetItem(text)
        self.realtime_list.insertItem(0, item_w)

    def stop_engine(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.worker = None
            self.write_log("🛑 엔진을 안전하게 중지했습니다.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

    def populate_table(self, articles):
        if not articles:
            return
            
        import pandas as pd
        df = pd.DataFrame(articles)
        
        # 🚨 대장님의 최종 명령: 0원 버그 박멸 및 1, 2, 3... 무조건 최신 날짜순 쐐기 정렬 🚨
        if 'reg_date' in df.columns:
            df['등록일'] = df['reg_date'].astype(str).str.replace('.', '-', regex=False)
            
        # '등록일' 컬럼을 date 형식으로 변환 후, 최신순(내림차순) 정렬, 빈 값은 무조건 맨 아래로!
        if '등록일' in df.columns:
            df['등록일'] = pd.to_datetime(df['등록일'], errors='coerce')
            df = df.sort_values(by='등록일', ascending=False, na_position='last')
            df = df.reset_index(drop=True)
            
        articles = df.to_dict('records')

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0) 
        self.table.setRowCount(len(articles))
        for row, art in enumerate(articles):
            self.table.setItem(row, 0, QTableWidgetItem(art['apt']))
            self.table.setItem(row, 1, QTableWidgetItem(art['reg_date']))
            
            itm_price = NumericItem(art['price'])
            itm_price.setData(Qt.UserRole, art.get('price_int', 0))
            self.table.setItem(row, 2, itm_price)
            
            self.table.setItem(row, 3, QTableWidgetItem(art['agency']))
            self.table.setItem(row, 4, QTableWidgetItem(art.get('cp_name', '확인불가')))
            
            itm_chotu = NumericItem(art['chotu'])
            itm_chotu.setData(Qt.UserRole, art.get('chotu_int', 0))
            self.table.setItem(row, 5, itm_chotu)
            
            itm_p = NumericItem(art['p'])
            itm_p.setData(Qt.UserRole, art.get('p_int', 0))
            self.table.setItem(row, 6, itm_p)
            
            self.table.setItem(row, 7, QTableWidgetItem(art.get('gam_gwon', '')))
            self.table.setItem(row, 8, QTableWidgetItem(art['feat']))
            blog_url_val = art.get('blog_url', '')
            blog_display = "✅ 블로그 확보" if blog_url_val else ""
            itm_blog = QTableWidgetItem(blog_display)
            if blog_url_val:
                itm_blog.setBackground(QColor(220, 255, 220))
                # [V8.0] 전체 배경색 강조를 끄고 조용히 URL 링크만 탑재
            self.table.setItem(row, 9, itm_blog)

            self.table.item(row, 0).setData(Qt.UserRole, {
                "id": art['id'],
                "phone": art.get('phone', '확인필요'),
                "blog_url": art.get('blog_url', '')
            })

        self.table.setSortingEnabled(True)
        self.table.sortItems(1, Qt.DescendingOrder) # [V7.4] 사용자의 지시에 맞춰 '등록일' 내림차순(최신순) 정렬 처리
        self.apply_chotu_filter()

        # ── [V6.5] 베스트5 추출 엔진 ──────────────────────────────────
        BEST5_CHOTU_LIMIT = 100000  # 10억 = 100,000만원

        # 1차 필터: 초투 10억 이하 + 거래가 있는 진성 매물
        candidates = []
        for art in articles:
            chotu_int = art.get('chotu_int', 0) or 0
            price_int = art.get('price_int', 0) or 0
            # chotu_int가 0이면 price_int로 대체 (역산값 fallback)
            effective_chotu = chotu_int if chotu_int > 0 else price_int
            if 0 < effective_chotu <= BEST5_CHOTU_LIMIT:
                candidates.append({**art, '_eff_chotu': effective_chotu})

        # 2차 정렬: 프리미엄 낮은순 → 매매가 낮은순
        def best5_sort_key(art):
            p_int = art.get('p_int', 0) or 0
            price_int = art.get('price_int', 0) or 0
            # P가 있으면 P 우선, 없으면 매매가로 정렬
            p_key   = p_int if p_int > 0 else 9999999
            prc_key = price_int if price_int > 0 else 9999999
            return (p_key, prc_key)

        candidates.sort(key=best5_sort_key)
        best5 = candidates[:5]
        self.update_best5(best5)
        # ────────────────────────────────────────────────────────────

    def update_best5(self, best5_list: list):
        """[V6.5] VVIP 베스트5 테이블을 고급 스타일로 렌더링"""
        MEDAL = {0: "🥇 1위", 1: "🥈 2위", 2: "🥉 3위", 3: "  4위", 4: "  5위"}
        ROW_COLORS = [
            QColor(40, 30, 0),   # 1위 황금빛
            QColor(30, 30, 35),  # 2위 은빛
            QColor(35, 20, 10),  # 3위 동빛
            QColor(15, 20, 30),  # 4위
            QColor(15, 20, 30),  # 5위
        ]
        RANK_TEXT_COLORS = [
            QColor(255, 215, 0),   # 금색
            QColor(192, 192, 192), # 은색
            QColor(205, 127, 50),  # 동색
            QColor(180, 200, 230), # 연파랑
            QColor(180, 200, 230),
        ]

        self.best5_table.setRowCount(0)
        if not best5_list:
            self.best5_table.setRowCount(1)
            empty = QTableWidgetItem("⏳ 수집 중... 스캔이 완료되면 베스트 5가 자동으로 표시됩니다.")
            empty.setForeground(QColor(100, 150, 200))
            empty.setTextAlignment(Qt.AlignCenter)
            self.best5_table.setItem(0, 0, empty)
            self.best5_table.setSpan(0, 0, 1, 7)
            return

        self.best5_table.setRowCount(len(best5_list))
        for i, art in enumerate(best5_list):
            bg   = ROW_COLORS[i]
            fg   = RANK_TEXT_COLORS[i]

            p_int     = art.get('p_int', 0) or 0
            price_int = art.get('price_int', 0) or 0
            chotu_int = art.get('_eff_chotu', 0) or 0
            has_blog  = bool(art.get('blog_url', ''))

            # 출처 태그
            src_tag = "✅ 네이버+블로그" if has_blog else "📌 네이버"
            src_color = QColor(100, 220, 120) if has_blog else QColor(120, 160, 220)

            cols = [
                (MEDAL.get(i, f"  {i+1}위"), fg),
                (art.get('apt', ''),         QColor(230, 230, 230)),
                (art.get('price', '-'),       QColor(255, 200, 80)),
                (format_price(chotu_int) if chotu_int else '-', QColor(100, 220, 200)),
                (format_price(p_int) if p_int else '확인필요',   QColor(255, 140, 80)),
                (art.get('gam_gwon', '-'),    QColor(180, 180, 220)),
                (src_tag,                     src_color),
            ]

            for col, (text, color) in enumerate(cols):
                itm = QTableWidgetItem(str(text))
                itm.setForeground(color)
                itm.setBackground(bg)
                itm.setTextAlignment(Qt.AlignCenter)
                itm.setFont(QFont("Arial", 11, QFont.Bold if col == 0 else QFont.Normal))
                self.best5_table.setItem(i, col, itm)

            self.best5_table.setRowHeight(i, 32)

    def on_table_click(self, row, col):

        data_dict = self.table.item(row, 0).data(Qt.UserRole)
        atcl_id = data_dict['id'] if isinstance(data_dict, dict) else ""
        phone = data_dict['phone'] if isinstance(data_dict, dict) else ""

        self.edID.setText(atcl_id)
        self.edRegion.setText(self.table.item(row, 0).text() if self.table.item(row, 0) else "")
        self.edPrice.setText(self.table.item(row, 2).text() if self.table.item(row, 2) else "")
        self.edAgency.setText(self.table.item(row, 3).text() if self.table.item(row, 3) else "")
        self.edChotu.setText(self.table.item(row, 4).text() if self.table.item(row, 4) else "")
        self.edP.setText(self.table.item(row, 5).text() if self.table.item(row, 5) else "")
        self.edGamGwon.setText(self.table.item(row, 6).text() if self.table.item(row, 6) else "")
        self.edPhone.setText(phone)
        self.edFeatures.setText(self.table.item(row, 7).text() if self.table.item(row, 7) else "")
        self.edBlogUrl.setText(data_dict.get('blog_url', "") if isinstance(data_dict, dict) else "")

    def on_table_double_click(self, row, col):
        data_dict = self.table.item(row, 0).data(Qt.UserRole)
        if isinstance(data_dict, dict):
            url = data_dict.get('blog_url', "")
            if url and url.startswith("http"):
                webbrowser.open(url)
                self.write_log(f"🌐 블로그 링크 열기: {url}")
        
    def copy_kakao(self):
        region = self.edRegion.text()
        if not region:
            QMessageBox.warning(self, "오류", "매물을 선택해 주세요.")
            return
            
        msg_parts = [f"📍 {region}"]
        if self.chk_price.isChecked(): msg_parts.append(f"💰 매매가: {self.edPrice.text()}")
        if self.chk_chotu.isChecked(): msg_parts.append(f"💵 초투: {self.edChotu.text()}")
        if self.chk_gam.isChecked() and self.edGamGwon.text(): msg_parts.append(f"📊 {self.edGamGwon.text()}")
        if self.chk_p.isChecked(): msg_parts.append(f"📈 P: {self.edP.text()}")
        if self.chk_feat.isChecked(): msg_parts.append(f"📝 특징: {self.edFeatures.toPlainText()}")
        if self.chk_phone.isChecked(): msg_parts.append(f"📞 담당: {self.edPhone.text()} ({self.edAgency.text()})")
        
        final_msg = " / ".join(msg_parts)
        QGuiApplication.clipboard().setText(final_msg)
        self.write_log(f"📋 카톡 클립보드 복사 완료: {final_msg}")
        QMessageBox.information(self, "복사 완료", "클립보드에 복사되었습니다. 카톡에 붙여넣기(Cmd+V) 하세요.")

    def save_excel(self):
        rows = self.table.rowCount()
        if rows == 0: return
        data = []
        for r in range(rows):
            data.append({
                "구역명": self.table.item(r, 0).text() if self.table.item(r, 0) else "",
                "등록일": self.table.item(r, 1).text() if self.table.item(r, 1) else "",
                "매매가": self.table.item(r, 2).text() if self.table.item(r, 2) else "",
                "부동산명": self.table.item(r, 3).text() if self.table.item(r, 3) else "",
                "광고출처": self.table.item(r, 4).text() if self.table.item(r, 4) else "",
                "초기투자금": self.table.item(r, 5).text() if self.table.item(r, 5) else "",
                "프리미엄(P)": self.table.item(r, 6).text() if self.table.item(r, 6) else "",
                "감평/권리가": self.table.item(r, 7).text() if self.table.item(r, 7) else "",
                "특징요약": self.table.item(r, 8).text() if self.table.item(r, 8) else "",
                "블로그링크": self.table.item(r, 9).text() if self.table.item(r, 9) else "",
            })
            
        df = pd.DataFrame(data)
        
        # 🚨 화면 출력(엑셀) 직전: 모든 구역 데이터를 섞어서 무조건 최신순(내림차순) 정렬 🚨
        if '확인일자' in df.columns:
            df = df.sort_values(by='확인일자', ascending=False, na_position='last')
        elif '등록일' in df.columns:
            df = df.sort_values(by='등록일', ascending=False, na_position='last')

        # 뒤죽박죽된 좌측 인덱스(순번)를 1번부터 깔끔하게 재정렬
        df = df.reset_index(drop=True)
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(BASE_DIR, f"노량진_실시간_매물현황_{date_str}.xlsx")
        try:
            df.to_excel(filepath, index=False)
            self.write_log(f"📊 엑셀 저장 완료: {filepath}")
            QMessageBox.information(self, "엑셀 저장", f"엑셀 파일이 저장되었습니다.\n{filepath}")
        except Exception as e:
            self.write_log(f"❌ 엑셀 저장 실패: {e}")

    def save_image(self):
        region = self.edRegion.text()
        if not region: return
            
        try:
            img = Image.new('RGB', (1080, 1080), color=(26, 26, 26))
            draw = ImageDraw.Draw(img)
            
            font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
            if not os.path.exists(font_path): font_path = "/Library/Fonts/Arial Unicode.ttf" 
                
            font_title = ImageFont.truetype(font_path, 75)
            font_sub = ImageFont.truetype(font_path, 45)
            font_body = ImageFont.truetype(font_path, 60)
            font_footer = ImageFont.truetype(font_path, 35)
            
            draw.text((80, 80), "📺 신분상승 TV", font=font_sub, fill=(255, 215, 0)) 
            draw.text((80, 150), "노량진 뉴타운 VIP 급매", font=font_title, fill=(255, 255, 255))
            draw.line([(80, 240), (1000, 240)], fill=(100, 100, 100), width=3)
            
            draw.text((120, 320), f"📍 구 역  :  {self.edRegion.text()}", font=font_body, fill=(220, 220, 220))
            draw.text((120, 440), f"💰 매매가 :  {self.edPrice.text()}", font=font_body, fill=(255, 120, 120))
            draw.text((120, 560), f"💵 초투금 :  {self.edChotu.text()}", font=font_body, fill=(120, 255, 120))
            draw.text((120, 680), f"📈 P (피) :  {self.edP.text()}", font=font_body, fill=(120, 200, 255))
            
            if self.edGamGwon.text():
                draw.text((120, 800), f"📊 {self.edGamGwon.text()}", font=font_body, fill=(200, 200, 200))
            
            draw.line([(80, 920), (1000, 920)], fill=(70, 70, 70), width=2)
            draw.text((250, 960), "PRO부동산 서프로 직통 ☎ 010-2319-0977", font=font_footer, fill=(255, 215, 0))
            
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(BASE_DIR, f"VIP_매물이미지_{date_str}.png")
            img.save(filepath)
            self.write_log(f"🖼 VIP 이미지 생성 완료: {filepath}")
            QMessageBox.information(self, "이미지 저장", f"명함 이미지가 저장되었습니다!\n{filepath}")
            
        except Exception as e:
            self.write_log(f"❌ 이미지 저장 실패: {e}")

    def send_vip_report(self):
        apt_name = self.edRegion.text()
        if not apt_name: return

        lines = [
            "💎 *[PRO부동산 VVIP 큐레이션]* 💎\n",
            f"📍 *{apt_name}*",
            f"💰 *매매가*: {self.edPrice.text()}",
            f"💵 *초기투자금*: {self.edChotu.text()}",
            f"📈 *프리미엄(P)*: {self.edP.text()}"
        ]
        if self.edGamGwon.text():
            lines.append(f"📊 *감평/권리*: {self.edGamGwon.text()}")
            
        lines.extend([
            f"📝 *브리핑*: {self.edFeatures.toPlainText()}",
            f"📞 *담당*: {self.edPhone.text()} ({self.edAgency.text()})",
            f"👉 [모바일 상세 확인](https://m.land.naver.com/article/info/{self.edID.text()})\n",
            "─────────────────────",
            "👑 *[PRO부동산 공식 플랫폼]*",
            "🔹 네이버카페: https://cafe.naver.com/pro1023",
            "🔹 투자직통망: 010-2319-0977 (서프로)",
            "─────────────────────"
        ])

        final_msg = "\n".join(lines)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": final_msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
        
        try:
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                self.write_log(f"📤 {apt_name} VIP 브리핑 전송 완료!")
        except Exception as e:
            self.write_log(f"❌ API 전송 에러: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VvipDashboard()
    window.show()
    sys.exit(app.exec_())
