import sys
import requests
import threading
from PySide6.QtCore import QTimer
import os
import json
from datetime import datetime
import re
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QMessageBox, QScrollArea, QGridLayout, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
from PIL import Image, ImageDraw, ImageFont

ZONES_DATA = {
    '1': {
        'dist_num': '노량진 1구역',
        'address': '노량진동278-2번지일대 (면적:132,187㎡)',
        'status_main': '26년 2월 현재 : 관처 준비중', 
        'status_sub': '[ 25년 9월 관리처분인가 총회완료 ]',
        'total_house': '2,993세대 (분양 2,519 / 임대 474)',
        'members': '1,015명 (▶84이상 세대수 : 1,164세대)',
        'scale': '지하4층 ~ 지상49층',
        'constructor': '오띠에르 (포스코 하이엔드브랜드)',
        'completion': '2032년 이후 예상',
        'move_cost': '감정평가금액의 최대 80%지급예정',
        'rate': '100.6% (추정)',
        'member_price': '59타입: 8.5억 / 84타입: 10.5억',
        'contribution': '10 : 0 : 90 (예정)',
        'phone': '02-823-5566'
    },
    '2': {
        'dist_num': '노량진 2구역',
        'address': '노량진동312-75번지일대 (면적:16,208㎡)',
        'status_main': '26년 2월 현재 : 착공 준비중',
        'status_sub': '[ 재분양신청 완료 ]',
        'total_house': '411세대 (분양 303 / 임대 108)',
        'members': '91명 (▶84이상 세대수 : 205세대)',
        'scale': '지하4층 ~ 지상45층',
        'constructor': '드파인 (SK에코플랜트 하이엔드브랜드)',
        'completion': '2029년 이후 예상',
        'move_cost': '감정평가금액의 최대 60%지급',
        'rate': '104.9% (추정)',
        'member_price': '59타입: 7.5억 / 84타입: 9.1억',
        'contribution': '0 : 0 : 100 (예정)',
        'phone': '02-812-5113'
    },
    '3': {
        'dist_num': '노량진 3구역',
        'address': '노량진동232-19번지일대 (면적:73,068㎡)',
        'status_main': '26년 2월 현재 : 관리처분인가 임박',
        'status_sub': '[ 26년 2월 관리처분인가 예정 ]',
        'total_house': '1,253세대 (분양 1,020 / 임대 233)',
        'members': '598명 (▶84이상 세대수 : 약 657세대)',
        'scale': '지하4층 ~ 지상49층',
        'constructor': '오띠에르 (포스코 하이엔드브랜드)',
        'completion': '2031년 이후 예상',
        'move_cost': '감정평가금액의 최대 100%지급예정',
        'rate': '95.46% (추정)',
        'member_price': '59타입: 8.4억 / 84타입: 10.3억',
        'contribution': '0 : 0 : 100 (예정)',
        'phone': '02-815-5510'
    },
    '4': {
        'dist_num': '노량진 4구역',
        'address': '노량진동294-5번지일대 (면적:40,512㎡)',
        'status_main': '26년 2월 현재 : 착공예정',
        'status_sub': '[ 멸실등기 예정 : 취득세 4.6% ]',
        'total_house': '844세대 (분양 695 / 임대 149)',
        'members': '375명 (▶84이상 세대수 : 약 407세대)',
        'scale': '지하4층 ~ 지상35층',
        'constructor': '디에이치 (현대건설 하이엔드브랜드)',
        'completion': '2029년 이후 예상',
        'move_cost': '감정평가금액의 최대 70%지급',
        'rate': '100.8% (추정)',
        'member_price': '59타입: 8억 / 84타입: 10억',
        'contribution': '10 : 30 : 60 (예정)',
        'phone': '02-812-0890'
    },
    '5': {
        'dist_num': '노량진 5구역',
        'address': '노량진동270-3번지일대 (면적:38,017㎡)',
        'status_main': '26년 2월 현재 : 철거 준비중',
        'status_sub': '[ 일반이주 완료 / 재분양신청 없음 ]',
        'total_house': '727세대 (분양 597 / 임대 130)',
        'members': '275명 (▶84이상 세대수 : 약 344세대)',
        'scale': '지하4층 ~ 지상28층',
        'constructor': '써밋 (대우건설 하이엔드브랜드)',
        'completion': '2030년 이후 예상',
        'move_cost': '감정평가금액의 최대 60%지급',
        'rate': '95% (추정)',
        'member_price': '59타입: 8억 / 84타입: 10억',
        'contribution': '10 : 30 : 60 (예정)',
        'phone': '02-822-3304'
    },
    '6': {
        'dist_num': '노량진 6구역',
        'address': '노량진동294-220번지일대 (면적:72,822㎡)',
        'status_main': '26년 2월 현재 : 착공 중',
        'status_sub': '[ 멸실등기완료 / 일반분양 예정 ]',
        'total_house': '1,499세대 (분양 1,237 / 임대 262)',
        'members': '770명 (▶84이상 세대수 : 825세대)',
        'scale': '지하4층 ~ 지상28층',
        'constructor': '라클라체 (SK에코 + GS건설)',
        'completion': '2029년 이후 예상',
        'move_cost': '감정평가금액의 최대 60%지급',
        'rate': '110% (추정)',
        'member_price': '59타입: 5.7억 / 84타입: 6.8억',
        'contribution': '0 : 0 : 100 (예정)',
        'phone': '02-813-0705'
    },
    '7': {
        'dist_num': '노량진 7구역',
        'address': '대방동 13-31번지일대 (면적:33,154㎡)',
        'status_main': '26년 2월 현재 : 이주 마무리',
        'status_sub': '[ 상반기 철거예정 ]',
        'total_house': '576세대 (분양 478 / 임대 98)',
        'members': '379명 (▶84이상 세대수 : 171세대)',
        'scale': '지하4층 ~ 지상27층',
        'constructor': '드파인 (SK에코플랜트 하이엔드브랜드)',
        'completion': '2030년 이후 예상',
        'move_cost': '감정평가금액의 최대 60%지급예정',
        'rate': '97.2% (추정)',
        'member_price': '59타입: 8억 / 84타입: 10억',
        'contribution': '0 : 0 : 100 (예정)',
        'phone': '02-3280-8508'
    },
    '8': {
        'dist_num': '노량진 8구역',
        'address': '대방동23-61번지일대 (면적:55,742㎡)',
        'status_main': '26년 2월 현재 : 착공 중',
        'status_sub': '[ 멸실등기 완료 / 재분양신청완료 ]',
        'total_house': '987세대 (분양 815 / 임대 172)',
        'members': '513명 (▶84이상 세대수 : 552세대)',
        'scale': '지하4층 ~ 지상29층',
        'constructor': '아크로 (DL이앤씨 하이엔드브랜드)',
        'completion': '2029년 이후 예상',
        'move_cost': '감정평가금액의 최대 60%지급',
        'rate': '116.4% (추정)',
        'member_price': '59타입: 8억 / 84타입: 9.5억',
        'contribution': '10 : 30 : 60 (예정)',
        'phone': '02-823-1324'
    }
}

def make_info_image(data_dict, parent):
    try:
        width, height = 1000, 915
        image = Image.new('RGBA', (width, height), (255, 255, 255, 255)) 
        draw = ImageDraw.Draw(image)

        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)
        YELLOW = (255, 255, 0)
        RED = (255, 0, 0)
        BLUE = (0, 0, 200)
        GRAY_BOX_TRANSPARENT = (100, 100, 100, 100)

        # OS 구분을 없애고 프로젝트 내부의 특정 폰트를 직접 지정
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
        font_path = os.path.join(base_dir, "assets", "malgunbd.ttf")
            
        try:
            f_title = ImageFont.truetype(font_path, 100)
            f_addr = ImageFont.truetype(font_path, 30)
            f_status_main = ImageFont.truetype(font_path, 60)
            f_status_sub = ImageFont.truetype(font_path, 40)
            f_row_label = ImageFont.truetype(font_path, 35)
            f_row_val = ImageFont.truetype(font_path, 35)
            f_watermark = ImageFont.truetype(font_path, 25)
            f_footer = ImageFont.truetype(font_path, 35)
        except:
            QMessageBox.critical(parent, "오류", "폰트 파일이 없습니다.")
            return

        header_h = 130
        draw.rectangle([(0, 0), (width, header_h)], fill=BLACK)
        draw.text((width/2, header_h/2), f"{data_dict['dist_num']}", fill=WHITE, font=f_title, anchor="mm")

        info_box_h = 180
        info_y_start = header_h
        draw.rectangle([(0, info_y_start), (width, info_y_start + info_box_h)], fill=YELLOW)
        draw.text((width/2, info_y_start + 30), data_dict['address'], fill=BLACK, font=f_addr, anchor="mm")
        draw.text((width/2, info_y_start + 90), data_dict['status_main'], fill=RED, font=f_status_main, anchor="mm")
        draw.text((width/2, info_y_start + 150), data_dict['status_sub'], fill=BLACK, font=f_status_sub, anchor="mm")

        line_y = info_y_start + info_box_h
        draw.line([(0, line_y), (width, line_y)], fill=BLACK, width=5)

        table_items = [
            ("총 세대수", "total_house"), ("조합원 수", "members"), ("사업규모", "scale"),
            ("시공사", "constructor"), ("준공시기", "completion"), ("이주비 조건", "move_cost"),
            ("비례율", "rate"), ("조합원 분양가", "member_price"), ("추가분담금", "contribution"),
            ("조합 전화번호", "phone")
        ]
        
        row_start_y = line_y + 5 
        row_h = 54

        for i, (label, key) in enumerate(table_items):
            current_y = row_start_y + (i * row_h)
            draw.line([(0, current_y + row_h), (width, current_y + row_h)], fill=BLACK, width=2)
            icon_x, icon_y = 20, current_y + row_h/2
            draw.rectangle([(icon_x, icon_y-8), (icon_x+16, icon_y+8)], fill=BLACK, outline=BLACK)
            draw.text((icon_x + 30, icon_y), f"{label} :", fill=BLACK, font=f_row_label, anchor="lm")
            val_x, value_text = 330, data_dict[key]
            val_color = BLACK
            if "지상" in value_text or "예정" in value_text: val_color = RED
            elif "비례율" in label or "조합원 수" in label: val_color = BLUE
            draw.text((val_x, icon_y), value_text, fill=val_color, font=f_row_val, anchor="lm")

        watermark_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        wm_draw = ImageDraw.Draw(watermark_layer)
        wm_w, wm_h = 250, 100
        wm_x, wm_y = width - wm_w - 20, 480 
        wm_draw.rectangle([(wm_x, wm_y), (wm_x + wm_w, wm_y + wm_h)], fill=GRAY_BOX_TRANSPARENT)
        wm_draw.multiline_text((wm_x + wm_w/2, wm_y + wm_h/2), 
                               "대한민국 부동산\nNO.1 플랫폼", 
                               fill=(255, 255, 255, 220), font=f_watermark, anchor="mm", align="center")
        image = Image.alpha_composite(image, watermark_layer)

        draw = ImageDraw.Draw(image)
        footer_h = 60
        draw.rectangle([(0, height - footer_h), (width, height)], fill=BLACK)
        draw.text((width/2, height - footer_h/2), "대한민국 NO.1 재개발·재건축 플랫폼", fill=WHITE, font=f_footer, anchor="mm")

        dist_name = data_dict['dist_num']
        filename = f"구역정보_완성본_(확인용)_{dist_name}.png"
        save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
        
        image.save(save_path, "PNG")
        QMessageBox.information(parent, "완료", f"이미지 생성 완료!\n바탕화면을 확인하세요.\n파일명: {filename}")

    except Exception as e:
        QMessageBox.critical(parent, "오류", f"생성 실패: {e}")

try:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _base_dir = os.getcwd()
SAVE_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", "info_maker_last_session.json")


class DataFetchThread(QThread):
    data_fetched = Signal(dict)
    error_signal = Signal(str, str, str)  # title, message, dl_url (optional)

    def __init__(self, zone_name):
        super().__init__()
        self.zone_name = zone_name

    def run(self):
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        zone_path = os.path.join(base_dir, "seoul_zones.xlsx")
        area_path = os.path.join(base_dir, "seoul_area.xlsx")
        
        import urllib.parse
        import re
        from datetime import datetime
        try:
            from bs4 import BeautifulSoup
            BS4_OK = True
        except ImportError:
            BS4_OK = False

        import requests

        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }

        MANUAL = "수동 입력 요망"
        data = {
            "address"      : "",
            "status_main"  : "",
            "total_house"  : "",
            "members"      : "",
            "scale"        : "",
            "constructor"  : "",
            "completion"   : "",
            "move_cost"    : "",
            "rate"         : "",
            "member_price" : "",
            "contribution" : "",
            "phone"        : "",
        }

        try:
            import pandas as pd
        except ImportError:
            self.error_signal.emit(
                "pandas 라이브러리 없음",
                "팩트 데이터 추출을 위해 pandas가 필요합니다.\n터미널에서 실행하세요:\n  pip install pandas openpyxl",
                ""
            )
            pd = None

        if pd is not None:
            if not os.path.exists(zone_path):
                dl_url = "https://data.seoul.go.kr/dataList/OA-22856/L/1/datasetView.do"
                msg = (f"seoul_zones.xlsx 파일이 없습니다.\n"
                       f"팩트 데이터를 검색으로 보완합니다.\n\n"
                       f"📥 다음 URL에서 다운로드 후\n{dl_url}\n"
                       f"파일명을 'seoul_zones.xlsx'로 저장하고\n"
                       f"아래 폴더에 넣어 주세요:\n{base_dir}")
                self.error_signal.emit("엑셀 파일 없음 — 네이버 검색으로 대체", msg, dl_url)
            else:
                try:
                    df = pd.read_excel(zone_path, dtype=str)
                    df.fillna("", inplace=True)

                    name_cols = [c for c in df.columns if any(kw in str(c) for kw in ["구역", "명칭", "사업명", "이름", "NM", "NAME", "BSSH"])]
                    if not name_cols: name_cols = list(df.columns[:6])

                    # 1. 검색어에서 한글과 숫자 분리
                    keywords = re.findall(r'[가-힣]+|[0-9]+', self.zone_name)
                    
                    # 2. '구역', '지구' 등 흔한 단어 제외
                    search_keywords = [kw for kw in keywords if kw not in ['구역', '지구', '재개발', '재건축']]
                    
                    # 3. 다중 키워드 AND 검색
                    mask = pd.Series(True, index=df.index)
                    for kw in search_keywords:
                        kw_mask = pd.Series(False, index=df.index)
                        for col in name_cols:
                            kw_mask = kw_mask | df[col].str.contains(kw, na=False)
                        mask = mask & kw_mask
                    
                    result = df[mask]
                    matched_row = None
                    
                    if not result.empty:
                        matched_row = result.iloc[0]
                    else:
                        self.error_signal.emit("검색 실패", f"엑셀에 '{self.zone_name}'와 일치하는 구역이 없습니다.\n부분적으로 수동 입력해주세요.", "")

                    if matched_row is not None:
                        row = matched_row
                        def gcol(*keys):
                            for k in keys:
                                for c in df.columns:
                                    if k.upper() in c.upper().replace(" ", ""):
                                        v = str(row[c]).strip()
                                        if v and v.lower() != "nan": return v
                            return ""

                        addr = gcol("주소", "위치", "LNM_ADRES", "지번", "도로명", "번지", "소재지", "ADRES", "LOC")
                        area = gcol("면적", "AREA", "㎡")
                        if addr and area: data["address"] = f"{addr} (면적:{area}㎡)"
                        elif addr: data["address"] = addr
                        import sys
                        print(f"DEBUG MATCHED ROW: {row.to_dict()}", file=sys.stderr)
                        print(f"DEBUG ADDR: {addr}, AREA: {area}, FINAL: {data['address']}", file=sys.stderr)


                        tot   = gcol("총세대", "합계", "TOTAL", "TOT_HSHLD", "계획세대")
                        sale  = gcol("분양세대", "일반분양", "SALE_HSHLD")
                        rent  = gcol("임대세대", "임대", "RENT_HSHLD")
                        if tot:
                            if sale and rent: data["total_house"] = f"{tot}세대 (분양 {sale} / 임대 {rent})"
                            else: data["total_house"] = f"{tot}세대"

                        mber = gcol("조합원", "MBER", "조합원수")
                        if mber: 
                            data["members"] = f"{mber}명"
                        
                        # seoul_area.xlsx 보완 검색 로직 (조합원 수 한정)
                        if not data["members"] and os.path.exists(area_path):
                            try:
                                df_area = pd.read_excel(area_path, dtype=str)
                                df_area.fillna("", inplace=True)
                                a_cols = [c for c in df_area.columns if any(kw in str(c) for kw in ["구역", "명칭", "사업명", "이름"])]
                                if not a_cols: a_cols = list(df_area.columns[:6])
                                
                                mask_a = pd.Series(True, index=df_area.index)
                                for kw in search_keywords:
                                    kw_a = pd.Series(False, index=df_area.index)
                                    for c in a_cols:
                                        kw_a = kw_a | df_area[c].str.contains(kw, na=False)
                                    mask_a = mask_a & kw_a
                                
                                if not df_area[mask_a].empty:
                                    row_a = df_area[mask_a].iloc[0]
                                    for c in df_area.columns:
                                        if "조합원" in str(c).replace(" ", ""):
                                            v = str(row_a[c]).strip()
                                            if v and v.lower() != "nan":
                                                data["members"] = f"{v}명"
                                                break
                            except Exception:
                                pass

                        data["constructor"] = gcol("시공", "CNSTRCT", "건설사", "시공사")
                        data["scale"] = gcol("층", "규모", "SCALE", "FLOR")
                        data["status_main"] = gcol("단계", "현황", "진행", "상태", "STTUS", "PROGRS")

                        rt = gcol("비례율", "RATE")
                        if rt: data["rate"] = rt if "%" in rt else rt + "%"

                except Exception:
                    pass

        if BS4_OK:
            try:
                q = urllib.parse.quote(f"{self.zone_name} 재개발 비례율 이주비 분양가 추가분담금")
                nav_url = f"https://search.naver.com/search.naver?query={q}"
                nr = requests.get(nav_url, headers=HEADERS, timeout=(3, 5), allow_redirects=True)
                nr.encoding = "utf-8"
                ntxt = BeautifulSoup(nr.text, "html.parser").get_text(separator=" ", strip=True)

                def srch(pattern):
                    m = re.search(pattern, ntxt)
                    return m if m else None

                if not data["rate"]:
                    m = srch(r"비례율\s*[:\-]?\s*([\d\.]+)\s*%")
                    if m: data["rate"] = m.group(1) + "% (추정)"

                if not data["move_cost"]:
                    m = srch(r"이주비[^\n]{0,40}(\d{2,3})\s*%")
                    if m: data["move_cost"] = f"감정평가금액의 최대 {m.group(1)}% 지급"
                    else:
                        m2 = srch(r"이주비[^\n\(]{0,30}(\d+(?:\.\d+)?억)")
                        if m2: data["move_cost"] = m2.group(0)[:45].strip()

                if not data["member_price"]:
                    m59 = srch(r"59[^\d]{0,5}([\d\.]+)\s*억")
                    m84 = srch(r"84[^\d]{0,5}([\d\.]+)\s*억")
                    parts = []
                    if m59: parts.append(f"59타입: {m59.group(1)}억")
                    if m84: parts.append(f"84타입: {m84.group(1)}억")
                    if parts: data["member_price"] = " / ".join(parts)

                if not data["contribution"]:
                    m = srch(r"추가분담금[^\n\(]{0,25}([\d,]+)\s*만?원")
                    if m: data["contribution"] = m.group(0)[:45].strip()

                if not data["constructor"]:
                    m = srch(r"시공사?\s*[:\s]?([가-힣a-zA-Z\s·]{1,15}(?:건설|이앤씨|엔지니어링|GS|SK|DL|HDC|삼성|현대|대우|롯데|포스코))")
                    if m: data["constructor"] = m.group(1).strip()

                if not data["total_house"]:
                    m = srch(r"([\d,]{3,6})\s*세대")
                    if m: data["total_house"] = m.group(1).replace(",", "") + "세대"

                if not data["address"]:
                    m = srch(r"(\S+[동리]\s*\d+[\-\d]*번지[^,\n]{0,40})")
                    if m: data["address"] = m.group(1).strip()
                    
                # 엑셀 및 기존 웹 검색에서 못 찾았을 경우 네이버 단독 타겟 검색 진행
                if not data["members"]:
                    try:
                        q_mber = urllib.parse.quote(f"{self.zone_name} 조합원 수")
                        url_mber = f"https://search.naver.com/search.naver?query={q_mber}"
                        nr_mber = requests.get(url_mber, headers=HEADERS, timeout=(3, 5), allow_redirects=True)
                        nr_mber.encoding = "utf-8"
                        ntxt_mber = BeautifulSoup(nr_mber.text, "html.parser").get_text(separator=" ", strip=True)
                        
                        m_mber = re.search(r"조합원[^\d]{0,15}([\d,]{2,5})\s*명", ntxt_mber)
                        if not m_mber:
                            m_mber = re.search(r"([\d,]{2,5})\s*명", ntxt_mber)
                        
                        if m_mber:
                            data["members"] = f"{m_mber.group(1)}명 (인터넷 검색 결과)"
                    except Exception:
                        pass

                # 정비사업 정보몽땅 전화번호/면적/조합원 자동 추출
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    q_info = urllib.parse.quote(f"{self.zone_name} 정비사업 정보몽땅")
                    url_info = f"https://search.naver.com/search.naver?query={q_info}"
                    nr_info = requests.get(url_info, headers=HEADERS, timeout=(3, 5), allow_redirects=True)
                    nr_info.encoding = "utf-8"
                    soup_info = BeautifulSoup(nr_info.text, "html.parser")
                    links = soup_info.find_all('a', href=True)
                    cafe_url = None
                    for a in links:
                        if 'cleanup.seoul.go.kr/cafe/mainIndx.do?cafeUrl=' in a['href']:
                            cafe_url = a['href']
                            break
                            
                    if cafe_url:
                        cafe_req = requests.get(cafe_url, headers=HEADERS, timeout=(3, 5), verify=False)
                        cafe_soup = BeautifulSoup(cafe_req.text, "html.parser")
                        
                        if not data["phone"]:
                            tel_el = cafe_soup.select_one('.footer-address .tel span')
                            if tel_el:
                                data["phone"] = tel_el.text.strip()
                                
                        sumry_link = None
                        for a in cafe_soup.find_all('a', href=True):
                            if 'sumry' in a['href'] or '사업개요' in a.text:
                                h = a['href']
                                if not h.startswith('javascript'):
                                    sumry_link = h
                                    break
                                    
                        if sumry_link:
                            sumry_url = "https://cleanup.seoul.go.kr" + sumry_link
                            sumry_req = requests.get(sumry_url, headers=HEADERS, timeout=(3, 5), verify=False)
                            sumry_txt = BeautifulSoup(sumry_req.text, "html.parser").get_text(separator=' ', strip=True)
                            
                            m_area = re.search(r'정비구역\s*면적[^\d]*([\d,]+)', sumry_txt)
                            if m_area:
                                extracted_area = m_area.group(1) + "제곱미터"
                                if data["address"] and "면적" not in data["address"]:
                                    data["address"] = f"{data['address']} (면적: {extracted_area})"
                                elif not data["address"]:
                                    data["address"] = f"(면적: {extracted_area})"
                                    
                            is_redev = '재개발' in sumry_txt
                            extracted_members = ""
                            if is_redev:
                                m_mem = re.search(r'토지등\s*소유자\s*수\s*([\d,]+)\s*명', sumry_txt)
                                if m_mem: extracted_members = m_mem.group(1)
                            else:
                                m_mem = re.search(r'조합원\s*수\s*([\d,]+)\s*명', sumry_txt)
                                if m_mem: extracted_members = m_mem.group(1)
                                
                            if not extracted_members:
                                m_mem2 = re.search(r'조합원\s*수\s*([\d,]+)\s*명', sumry_txt)
                                if m_mem2: extracted_members = m_mem2.group(1)
                                
                            if extracted_members:
                                data["members"] = f"{extracted_members}명 (정보몽땅)"
                                
                            m_scale = re.search(r'지상\s*:\s*(\d+)\s*/\s*지하\s*:\s*(\d+)', sumry_txt)
                            if m_scale:
                                data["scale"] = f"지하{m_scale.group(2)}층 ~ 지상{m_scale.group(1)}층"
                except Exception:
                    pass

            except Exception:
                pass

        now_prefix = f"{datetime.now().year % 100}년 {datetime.now().month}월 현재 : "
        status_val = data["status_main"] if data["status_main"] else MANUAL

        mapping_data = {
            "address"      : data["address"]      or MANUAL,
            "status_main"  : now_prefix + status_val,
            "total_house"  : data["total_house"]  or MANUAL,
            "members"      : data["members"]      or MANUAL,
            "scale"        : data["scale"]        or MANUAL,
            "constructor"  : data["constructor"]  or MANUAL,
            "completion"   : data["completion"]   or MANUAL,
            "move_cost"    : data["move_cost"]    or MANUAL,
            "rate"         : data["rate"]         or MANUAL,
            "member_price" : data["member_price"] or MANUAL,
            "contribution" : data["contribution"] or MANUAL,
            "phone"        : data["phone"]        or MANUAL,
        }

        self.data_fetched.emit(mapping_data)

class InfoMakerApp(QWidget):

    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 구역정보 (최종 완성본) Mac 호환판")
        self.resize(500, 800)
        self.entries = {}
        self._loading = False
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        lbl = QLabel("[ 구역을 선택하세요 ]")
        lbl.setStyleSheet("color: red; font-weight: bold;")
        lbl.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl)

        grid_layout = QGridLayout()
        for i in range(1, 9):
            btn = QPushButton(f"{i}구역")
            btn.setStyleSheet("background-color: lightgray; padding: 5px;")
            btn.clicked.connect(lambda _, x=i: self.load_zone(x))
            row = (i-1) // 4
            col = (i-1) % 4
            grid_layout.addWidget(btn, row, col)
        
        main_layout.addLayout(grid_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        self.inner_layout = QVBoxLayout(content_widget)

        lbl2 = QLabel("[ 기본 정보 ]")
        lbl2.setStyleSheet("color: blue; font-weight: bold; font-size: 14px;")
        lbl2.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl2)

        self.add_input("1. 구역명(직접입력)", "dist_num", "노량진 1구역")
        self.entries["dist_num"].returnPressed.connect(self.fetch_and_autofill_zone_data)
        self.add_input("2. 주소/면적", "address", "노량진동278-2번지일대 (면적:132,187㎡)")
        self.add_input("3. 현재 현황(메인)", "status_main", f"{datetime.now().year % 100}년 {datetime.now().month}월 현재 : 관처 준비중")
        self.add_input("4. 세부 일정", "status_sub", "[ 26년 상반기 관리처분인가 예정 ]")

        lbl3 = QLabel("[ 상세 테이블 정보 ]")
        lbl3.setStyleSheet("color: blue; font-weight: bold; font-size: 14px;")
        lbl3.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl3)

        self.add_input("5. 총 세대수", "total_house", "2,993세대 (분양 2,519 / 임대 474)")
        self.add_input("6. 조합원 수", "members", "1,015명 (▶84이상 세대수 : 1,164세대)")
        self.add_input("7. 사업규모", "scale", "지하4층 ~ 지상49층")
        self.add_input("8. 시공사", "constructor", "오띠에르 (포스코 하이엔드브랜드)")
        self.add_input("9. 준공시기", "completion", "2032년 이후 예상")
        self.add_input("10. 이주비 조건", "move_cost", "감정평가금액의 최대 90% 지급예정")
        self.add_input("11. 비례율", "rate", "100.6% (추정)")
        self.add_input("12. 조합원 분양가", "member_price", "59타입: 8.5억 / 84타입: 10.5억")
        self.add_input("13. 추가분담금", "contribution", "10 : 0 : 90 (예정)")
        self.add_input("14. 전화번호", "phone", "02-823-5566")

        btn_gen = QPushButton("✨ 최종 완성 이미지 생성")
        btn_gen.setStyleSheet("background-color: #FFD400; font-weight: bold; font-size: 16px; padding: 10px;")
        btn_gen.clicked.connect(self.on_click)
        self.inner_layout.addWidget(btn_gen)

        main_layout.addWidget(scroll)

    def add_input(self, label_text, key_name, default_val=""):
        h_layout = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(120)
        lbl.setStyleSheet("font-weight: bold;")
        ent = QLineEdit(default_val)
        ent.textChanged.connect(self.save_data)
        h_layout.addWidget(lbl)
        h_layout.addWidget(ent)
        self.inner_layout.addLayout(h_layout)
        self.entries[key_name] = ent


    def fetch_and_autofill_zone_data(self):
        zone_name = self.entries["dist_num"].text().strip()
        if not zone_name:
            return
        
        self.setWindowTitle("데이터 수집 중입니다... 잠시만 기다려주세요.")
        self.setEnabled(False)
        self._loading = True
        
        self.fetch_thread = DataFetchThread(zone_name)
        self.fetch_thread.data_fetched.connect(self._apply_fetched_data)
        self.fetch_thread.error_signal.connect(self._show_error_message)
        self.fetch_thread.start()

    def _show_error_message(self, title, msg, url):
        QMessageBox.warning(self, title, msg)

    def _apply_fetched_data(self, mapping_data):

        self._loading = True
        for key, val in mapping_data.items():
            if key in self.entries:
                self.entries[key].setText(val)
        
        self.setWindowTitle("PRO부동산 구역정보 (최종 완성본) Mac 호환판")
        self.setEnabled(True)
        self._loading = False
        self.save_data()
        
    def load_zone(self, zone_num):
        self._loading = True
        data = ZONES_DATA.get(str(zone_num), {}).copy()
        
        if 'status_main' in data:
            current_date_prefix = f"{datetime.now().year % 100}년 {datetime.now().month}월 현재"
            data['status_main'] = re.sub(r'\d{2}년 \d{1,2}월 현재', current_date_prefix, data['status_main'])

        for key, value in data.items():
            if key in self.entries:
                self.entries[key].setText(value)
        self._loading = False
        self.save_data()

    def on_click(self):
        self.save_data()
        data = {key: entry.text() for key, entry in self.entries.items()}
        make_info_image(data, self)

    def save_data(self, *args):
        if self._loading: return
        data = {key: ent.text() for key, ent in self.entries.items()}
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            self._loading = True
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if key in ['wl_title', 'wl_contact']: continue
                        if key == 'status_main':
                            current_date_prefix = f"{datetime.now().year % 100}년 {datetime.now().month}월 현재"
                            val = re.sub(r'\d{2}년 \d{1,2}월 현재', current_date_prefix, val)
                        if key in self.entries:
                            self.entries[key].setText(val)
            except:
                pass
            finally:
                self._loading = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if sys.platform == "darwin":
        from PySide6.QtGui import QFont
        app.setFont(QFont("Apple SD Gothic Neo"))
        
    window = InfoMakerApp()
    
    # [Mac OS 포커스 강제화 처리]
    window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)
    window.show()
    window.setWindowFlags(window.windowFlags() & ~Qt.WindowStaysOnTopHint)
    window.show()
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())
