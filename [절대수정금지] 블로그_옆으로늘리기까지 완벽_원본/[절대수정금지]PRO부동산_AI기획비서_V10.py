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
import math
import pyperclip
import traceback
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

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

# Mac 환경의 완벽한 실행을 위해 절대 경로 지정
MCP_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp"
AUTH_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp-auth"

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


class ImageDropLabel(QLabel):
    """이미지 Drag & Drop 구역"""
    imageDropped = Signal(str)

    def __init__(self, title):
        super().__init__(title)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { border: 2px dashed #9b59b6; border-radius: 10px; background-color: #f4f6f7; color: #2c3e50; font-weight: bold; }")
        self.setAcceptDrops(True)
        self.image_path = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                self.image_path = url.toLocalFile()
                self.setText(f"📸 추가된 이미지:\\n{os.path.basename(self.image_path)}")
                self.imageDropped.emit(self.image_path)


import re
import json

ZONE_DATA = {
    "1구역": ["관처 준비중 (25.9월 총회완료)", "조합원분양가: 59타입 8.5억 / 84타입 10.5억", "이주비 최대 90% 지급예정 (무60%+유30%)", "84기준 입주시 예상시세 30억 이상 예상", "추가분담금 납부조건: 10 : 0 : 90 (예정)", "3.5", "8,400만원"],
    "2구역": ["착공 준비중 (재분양신청 완료)", "조합원분양가: 59타입 7.5억 / 84타입 9.1억", "이주비 지급조건: 감정평가금액의 최대 60%", "109기준 입주시 예상시세 MIN 32억 예상", "추가분담금 납부조건: 0 : 0 : 100 (입주시 완납)", "3.5", "9,100만원"],
    "3구역": ["관리처분인가 임박 (26년2월 예정)", "조합원분양가: 59타입 8.4억 / 84타입 10.3억", "이주비 지급조건: 감정가 최대 100% 지급예정", "84기준 입주시 예상시세 MIN 30억 예상", "추가분담금 납부조건: 0 : 0 : 100 (입주시 완납)", "3.5", "10,300만원"],
    "4구역": ["철거마무리 (멸실등기 예정)", "조합원분양가: 59타입 7.5억 / 84타입 9억", "이주비 지급조건: 감정평가금액의 최대 70%", "84기준 입주시 예상시세 MIN 30억 예상", "추가분담금 납부조건: 10 : 30 : 60 (계약/중도/잔금)", "3.5", "9,000만원"],
    "5구역": ["철거준비중 (일반이주 완료)", "조합원분양가: 59타입 8억 / 84타입 10억", "이주비 지급조건: 감정평가금액의 최대 60%", "84기준 입주시 예상시세 MIN 30억 예상", "추가분담금 납부조건: 10 : 30 : 60 (계약/중도/잔금)", "3.5", "10,000만원"],
    "6구역": ["착공 중 (멸실등기완료)", "조합원분양가: 59타입 5.7억 / 84타입 6.8억", "이주비 지급조건: 감정평가금액의 최대 60%", "84기준 입주시 예상시세 MIN 30억 예상", "추가분담금 납부조건: 0 : 0 : 100 (입주시 완납)", "3.5", "6,800만원"],
    "7구역": ["이주 마무리 (12월 철거예정)", "조합원분양가: 59타입 8억 / 84타입 10억", "이주비 지급조건: 감정평가금액의 최대 60%", "84기준 입주시 예상시세 MIN 28억 예상", "추가분담금 납부조건: 0 : 0 : 100 (입주시 완납)", "3.5", "10,000만원"],
    "8구역": ["착공중", "조합원분양가: 59타입 8억 / 84타입 9.5억", "이주비 지급조건: 감정평가금액의 최대 60%", "84기준 입주시 예상시세 MIN 30억 예상", "추가분담금 납부조건: 10 : 30 : 60 (계약/중도/잔금)", "3.5", "9,500만원"]
}

def safe_float(val_str):
    try:
        return float(str(val_str).replace(" ", "").replace(",", ""))
    except Exception:
        return 0.0

def format_num(val):
    if val == int(val):
        return str(int(val))
    return str(val).rstrip('0').rstrip('.') if '.' in str(val) else str(val)

def draw_multicolor_centered(draw, center_x, y, parts, font, anchor_y="m"):
    total_width = sum(draw.textlength(text, font=font) for text, _ in parts)
    current_x = center_x - (total_width / 2)
    for text, color in parts:
        draw.text((current_x, y), text, fill=color, font=font, anchor=f"l{anchor_y}")
        current_x += draw.textlength(text, font=font)

def draw_val_unit_億(draw, x, y, value, font_val, font_unit, color):
    val_str = format_num(value)
    w_val = draw.textlength(val_str, font=font_val)
    w_unit = draw.textlength("억", font=font_unit)
    start_x = x - ((w_val + w_unit) / 2)
    draw.text((start_x, y), val_str, fill=color, font=font_val, anchor="lm")
    draw.text((start_x + w_val, y + 12), "억", fill=color, font=font_unit, anchor="lm")

def draw_adaptive_text(draw, x, y, text, font_candidates, color, max_width, anchor="mm"):
    text = str(text) if text is not None else ""
    selected_font = font_candidates[-1]
    for font in font_candidates:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        if text_w <= max_width:
            selected_font = font
            break
    draw.text((x, y), text, fill=color, font=selected_font, anchor=anchor)

def make_property_image(data, parent):
    try:
        width, height = 1300, 950
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        BLACK, WHITE, YELLOW, RED = (0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 20, 20)
        GRAY_BG, PINK_BG = (240, 240, 240), (255, 230, 230)
        TRANSPARENT_EMERALD = (210, 255, 230, 128)
        TRANSPARENT_SKY = (225, 245, 255, 128)
        
        # OS 구분을 없애고 프로젝트 내부의 특정 폰트를 직접 지정
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
        font_path = os.path.join(os.path.expanduser("~"), "Desktop", "PRO부동산_자동화_로컬최종본", "assets", "malgunbd.ttf")
        
        f_header = ImageFont.truetype(font_path, 95); f_brand = ImageFont.truetype(font_path, 35)
        f_invest_val = ImageFont.truetype(font_path, 115); f_invest_label = ImageFont.truetype(font_path, 70); f_invest_unit = ImageFont.truetype(font_path, 50)
        f_table_head = ImageFont.truetype(font_path, 35); f_table_val = ImageFont.truetype(font_path, 85); f_table_unit = ImageFont.truetype(font_path, 35)
        f_list = ImageFont.truetype(font_path, 38); f_list_sm = [ImageFont.truetype(font_path, 38), ImageFont.truetype(font_path, 34), ImageFont.truetype(font_path, 26)]
        f_list_label_matched = ImageFont.truetype(font_path, 38)
        f_right_sm = ImageFont.truetype(font_path, 23); f_right_md = ImageFont.truetype(font_path, 35)
        f_right_lg = ImageFont.truetype(font_path, 65); f_right_contact = ImageFont.truetype(font_path, 35)
        f_footer = ImageFont.truetype(font_path, 35); f_platform = [ImageFont.truetype(font_path, 21), ImageFont.truetype(font_path, 18)]
        f_tax_val = ImageFont.truetype(font_path, 40)

        # --- Header ---
        draw.rectangle([(0, 0), (width, 160)], fill=BLACK)
        brand_x_center = 150
        draw.text((brand_x_center, 60), "대한민국 부동산", fill=WHITE, font=f_brand, anchor="mm")
        header_parts = [("NO.1", YELLOW), (" 플랫폼", WHITE)]
        draw_multicolor_centered(draw, brand_x_center, 110, header_parts, f_brand, anchor_y="m")
        draw.text((width/2 - 10, 80), f"노량진 {data['dist_display']}", fill=WHITE, font=f_header, anchor="mm")
        draw.text((width/2 + 410, 80), data['prop_type'], fill=YELLOW, font=ImageFont.truetype(font_path, 100), anchor="mm")

        # --- Invest ---
        draw.rectangle([(0, 160), (width, 330)], fill=YELLOW)
        draw.text((width/2 - 250, 245), "초기투자금 :", fill=RED, font=f_invest_label, anchor="mm")
        draw_val_unit_億(draw, width/2 + 150, 245, data['invest_price'], f_invest_val, f_invest_unit, RED)

        # --- Table ---
        table_y, col_w = 330, width / 6
        draw.rectangle([(0, table_y), (col_w*4, table_y + 70)], fill=GRAY_BG)
        draw.rectangle([(0, table_y + 70), (col_w*4, table_y + 190)], fill=WHITE)
        draw.rectangle([(col_w*4, table_y), (width, table_y + 190)], fill=PINK_BG)
        cols, vals = ["매매가", "프리미엄", "권리가", "임대", "총 매수가", "안전마진"], [data['p_sale'], data['p_premium'], data['p_rights'], data['p_rent'], data['p_total'], data['p_margin']]
        for i in range(6):
            x = i * col_w
            draw.text((x + col_w/2, table_y + 35), cols[i], fill=BLACK, font=f_table_head, anchor="mm")
            color_val = RED if i == 1 else BLACK
            draw_val_unit_億(draw, x + col_w/2, table_y + 130, vals[i], f_table_val, f_table_unit, color_val)

        # --- Details ---
        detail_y, split_x = 520, col_w * 4
        list_keys, row_height = [f'list_{i}' for i in range(1, 6)], 72
        for i, key in enumerate(list_keys):
            text, cur_y = data[key], detail_y + 35 + (i * row_height)
            bg_color = GRAY_BG if i % 2 == 0 else WHITE
            y_start = detail_y + (i * row_height) - 1
            if i == 0: y_start -= 1 
            y_end = detail_y + ((i + 1) * row_height) + 1
            draw.rectangle([(0, y_start), (split_x, y_end)], fill=bg_color)
            draw.rectangle([(24, cur_y - 6), (36, cur_y + 6)], fill=BLACK)
            color_use = RED if i == 0 else BLACK
            if i == 0 and ":" in text:
                parts = text.split(":", 1)
                draw.text((60, cur_y), parts[0] + ":", fill=color_use, font=f_list_label_matched, anchor="lm")
                label_w = draw.textlength(parts[0] + ":", font=f_list_label_matched)
                draw_adaptive_text(draw, 60 + label_w + 10, cur_y, parts[1], f_list_sm, color_use, split_x - 80 - label_w, anchor="lm")
            else:
                draw_adaptive_text(draw, 60, cur_y, text, f_list_sm, color_use, split_x - 80, anchor="lm")

        # --- Right Side ---
        overlay = Image.new('RGBA', image.size, (0,0,0,0)); drw_overlay = ImageDraw.Draw(overlay)
        drw_overlay.rectangle([(split_x, detail_y), (width, detail_y + 70)], fill=TRANSPARENT_EMERALD)
        drw_overlay.rectangle([(split_x, detail_y + 70), (width, detail_y + 230)], fill=TRANSPARENT_SKY)
        image.paste(overlay, (0,0), overlay)
        
        sub_split, mid_y = col_w * 5, detail_y + 70
        draw.text((split_x + (sub_split-split_x)/2, detail_y + 35), "취득세(예상)", fill=BLACK, font=f_right_sm, anchor="mm")
        draw.text((sub_split + (width-sub_split)/2, detail_y + 35), data['final_tax_str'], fill=BLACK, font=f_tax_val, anchor="mm")
        draw.text((split_x + (width-split_x)/2, mid_y + 80), data['comp_type'], fill=BLACK, font=f_right_lg, anchor="mm")
        bot_y_start = mid_y + 160
        draw_adaptive_text(draw, split_x + (width-split_x)/2, bot_y_start + 32, "대한민국 재개발 재건축 NO.1 플랫폼", f_platform, BLACK, width-split_x-10, anchor="mm")
        draw.text((split_x + (width-split_x)/2, 840), f"서프로 : {data['contact']}", fill=BLACK, font=f_right_contact, anchor="mm")

        # --- Footer ---
        draw.rectangle([(0, 880), (width, 950)], fill=BLACK)
        footer_parts = [(f"노량진{data['dist_display']} ", WHITE), ("가장 최신", RED), (" 진행상황은 아래▼ 자세히 나와있습니다.", WHITE)]
        draw_multicolor_centered(draw, width/2, 915, footer_parts, f_footer, anchor_y="m")

        # --- Lines ---
        for i in range(1, 6): draw.line([(i * col_w, table_y), (i * col_w, table_y + 190)], fill=BLACK, width=2)
        for yp in [table_y, table_y+70, table_y+190]: draw.line([(0, yp), (width, yp)], fill=BLACK, width=2)
        for i in range(5):
            cur_y = detail_y + 35 + (i * row_height)
            draw.rectangle([(20, cur_y - 10), (40, cur_y + 10)], outline=BLACK, width=3)
        draw.line([(split_x, detail_y), (split_x, 880)], fill=BLACK, width=2)
        draw.line([(split_x, detail_y), (width, detail_y)], fill=BLACK, width=2)
        draw.line([(split_x, detail_y + 70), (width, detail_y + 70)], fill=BLACK, width=2)
        draw.line([(sub_split, detail_y), (sub_split, detail_y + 70)], fill=BLACK, width=2)
        draw.line([(split_x, mid_y + 160), (width, mid_y + 160)], fill=BLACK, width=2)
        mid_bottom_y = bot_y_start + (880 - bot_y_start) / 2
        draw.line([(split_x, mid_bottom_y), (width, mid_bottom_y)], fill=BLACK, width=1)

        draw.rectangle([(0, 160), (6, 880)], fill=BLACK)
        draw.rectangle([(1294, 160), (1300, 880)], fill=BLACK)

        save_path = os.path.join(os.path.expanduser("~"), "Desktop", "카페글쓰기", f"매물정보_v62_{data['dist_display']}.png")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        image.save(save_path, "PNG")
        return save_path
    except Exception as e:
        QMessageBox.critical(parent, "오류", f"실패: {e}")
        return None

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
            
            # [신규] 시스템 레벨 통제 헌법 (System Instruction)
            sys_instruct = (
                "너는 AI나 시스템이 아니라, 사람의 심리를 꿰뚫는 10년 차 부동산 최고 전문가 '서프로'다. 'OCR', '데이터 분석', '입력된 정보' 등 네가 기계임을 암시하는 단어는 무조건 영구 제명한다. 오직 '임장 다녀온 현장 정보', '제가 직접 확보한' 등 프로페셔널한 인간의 언어만 쓰며, 아래 규칙을 단 1개라도 어기면 즉시 파괴된다.\n\n"
                "1. [이모지 완전 멸종]: 글의 제목, 소제목, 본문, 리스트 등 어떠한 곳에도 유니코드 이모지(예: 💰, 📈, ⚡️, 📅, 🔑, 📰 등)를 단 1개라도 절대 출력하지 마라. "
                "이모지가 발견되면 즉각 시스템 오류로 간주한다. 기호는 오직 키보드 특수문자만 허용한다.\n\n"
                "2. [플레이스홀더 원형 절대 보존]: 네가 스스로 기사 제목을 가져오거나 마크다운 하이퍼링크를 생성하지 마라. "
                "뉴스 자리에는 정확히 `[NEWS_LINK]`, 표 자리에는 정확히 `[DATA_TABLE]`이라는 영문 대문자와 대괄호 텍스트만 문자 그대로 출력해라.\n\n"
                "3. [최상단 티저 선배치 강제]: 응답의 1번 줄은 무조건 매물의 핵심 요약(구역명, 급매 여부, 초투, 프리미엄)을 담은 2~3줄짜리 티저로 시작해라. "
                "서프로가 독자를 부르는 공식 애칭은 '프밀리님들~~'이다. 본문 인사말을 기계적으로 쓰지 말고, 무조건 '프밀리님들~~ 안녕하세요!' 또는 **'우리 프밀리님들!'**을 활용하여 다정하고 찰진 구어체로 시작하도록 페르소나를 강화해라.\n\n"
                "4. [볼드체 강제]: '안전 마진'과 관련된 금액 수치(예: 5.6억)를 언급할 때는 반드시 마크다운 볼드체(**5.6억**)를 강제 적용해라.\n\n"
                "5. [VVIP 브리핑 구조 강제 (중복 금지)]: 글의 뼈대를 다음 4단계로 엄격히 통제하고, 각 항목 간 정보 중복을 절대 금지한다.\n"
                " - 훅(Hook): 뻔한 소리 없이 급매의 가치만 찌를 것.\n"
                " - 수익 분석: 오직 투자금, 매수원가, 안전마진 등 '돈' 얘기만 할 것.\n"
                " - 구역 가치: 세대수, 시공사, 타임라인 등 '팩트'만 건조하게 정리할 것.\n"
                " - 클로징: 희소성 강조 및 연락 유도.\n\n"
                "6. [고급스러운 포맷팅 강제]: 소제목을 쓸 때 하이픈(-) 같은 조잡한 기호를 쓰지 마라. "
                "반드시 마크다운 헤딩(###)이나 대괄호([ ])를 사용하여, 보고서처럼 깔끔하고 무게감 있는 시각적 포맷을 유지해라.\n\n"
                "7. [산수 절대 금지]: 본문 작성 시 (A + B = C) 같은 덧셈/뺄셈 수식 과정을 절대 서술하지 마라. 총 매수 원가와 안전 마진은 반드시 제공된 데이터 테이블의 숫자만 100% 그대로 복사해서 출력해라.\n\n"
                "8. [프밀리님 전용 톤앤매너 장착]: 글 중간중간 \"우리 프밀리님들만 알고 계세요\", \"프밀리님들을 위해 제가 직접 뛰어봤습니다\" 같은 친근하고 특별한 표현을 섞어 써서 독자와의 유대감을 형성해라."
            )
            
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
                
            print('🚨 [JSON_OVERRIDE] 청소 로직 진입 - 강제 패스 시작')
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # [AUTO-PURGE 전면 차단 — 현재 비활성화 상태]
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # self.log_signal.emit("🧹 [청소 모드] 메모리 누수 방지! 이전 작업물의 일회용 쓰레기 소스를 파괴합니다...")
            # try:
            #     res_notebook = await client.call_tool("notebook_get", {"notebook_id": notebook_id})
            #     import json
            #     try:
            #         notebook_data = json.loads(res_notebook)
            #         sources = notebook_data.get("sources", [])
            #     except Exception:
            #         # JSON 파싱 실패 시 빈 리스트
            #         sources = []
            #
            #     keep_keywords = ["법전", "최종", "master", "rule", "pro_fact_book"]
            #     deleted_count = 0
            #
            #     # 삭제 대상 목록 먼저 추려서 전체 개수를 파악
            #     targets_to_delete = []
            #     for src in sources:
            #         s_id = src.get("uuid") or src.get("id") or src.get("source_id")
            #         s_title = src.get("title", "")
            #         if not s_id:
            #             continue
            #         should_keep = any(kw in s_title.lower() for kw in keep_keywords)
            #         if not should_keep:
            #             targets_to_delete.append((s_id, s_title))
            #
            #     total_targets = len(targets_to_delete)
            #     if total_targets > 0:
            #         msg = f"🧹 삭제 대상 {total_targets}개 확인 — 지금부터 무자비하게 폐기합니다!"
            #         self.log_signal.emit(msg)
            #         print(msg)
            #
            #     for idx, (s_id, s_title) in enumerate(targets_to_delete, start=1):
            #         progress_msg = f"🗑️ 일회용 쓰레기 소스 파괴 중... ( {idx} / {total_targets} )  ▶ {s_title}"
            #         self.log_signal.emit(progress_msg)
            #         print(progress_msg)
            #         await client.call_tool("source_delete", {"source_id": s_id, "confirm": True})
            #         deleted_count += 1
            #
            #     if deleted_count > 0:
            #         self.log_signal.emit(f"✨ 청소 완료! 총 {deleted_count}개의 일회용 소스 영구 삭제 완료 (클린 룸 확보)")
            #     else:
            #         self.log_signal.emit("✨ 청소 완료! (이미 깨끗한 클린 룸 상태입니다)")
            # except Exception as e:
            #     self.log_signal.emit(f"⚠️ 일회용 소스 청소 중 오류 발생 (진행은 계속됩니다): {e}")
            print('🚨 [JSON_OVERRIDE] 청소 로직 완전 무력화 성공! 원고 생성으로 직행합니다.')

            # 리서치 시작
            self.log_signal.emit(f"🔍 [API 통신] research_start 호출 중... VIP 3단계 파이프라인 탐색 시작")
            
            # 1. OCR 결과물에서 구역명을 추출하거나, 기존 area_name 변수에서 가져온다.
            search_zone_name = area_name if 'area_name' in locals() else "노량진1구역" # 안전장치 추가
            
            # 2. 이제 변수가 확실히 정의된 상태에서 쿼리를 생성한다!
            research_query = f"site:land.seoul.go.kr {search_zone_name} 정비사업, site:law.go.kr {search_zone_name} 재개발, {search_zone_name} 최신 뉴스"
            res_start = await client.call_tool("research_start", {"query": research_query, "source": "web", "mode": "fast", "notebook_id": notebook_id})
            
            task_match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', res_start)
            if not task_match:
                self.log_signal.emit(f"⚠️ Task ID 추출 실패: {res_start.strip()}")
                task_id = ""
            else:
                task_id = task_match.group(1)
                self.log_signal.emit(f"📌 Research Task ID: {task_id}\n")
                
            self.log_signal.emit("⏳ 리서치 진행 상태를 실시간으로 대기합니다 (서버 자율 대기, 최대 5분 소요)...")
            res_status = await client.call_tool("research_status", {"notebook_id": notebook_id, "task_id": task_id, "max_wait": 300, "poll_interval": 10})
            
            # 서버에서 완료(completed) 또는 실패(에러)할 때까지 알아서 대기 후 반환됨
            status_lower = res_status.lower()
            if "error" in status_lower or "failed" in status_lower:
                self.log_signal.emit("⚠️ 리서치 도중 에러가 발생했으나 계속 진행해봅니다.")
            
            self.log_signal.emit(f"⏳ 리서치 대기 및 수집 완료!\n")
                
            # 5. 📥 Import
            self.log_signal.emit(f"📥 [API 통신] research_import 호출 중... (수집된 10개의 소스 업로드 진행 & 노트북 저장. 약 1~2분이 소요되므로 멈춘 게 아닙니다! 절대 창 끄지 마세요!!)")
            res_import = await client.call_tool("research_import", {"notebook_id": notebook_id, "task_id": task_id})
            self.log_signal.emit(f"응답: {res_import.strip()}")

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

            # [대장님 영구 지시] slide_deck_create 완전 제거 — NotebookLM 슬라이드 자동 생성 금지
            import glob, json
            expert_prompt = (
                f"당신은 대한민국 상위 1% 자산가를 전담하는 부동산 재개발 중개법인 전문가 '서프로'입니다. '{search_zone_name}' 매물 브리핑 원고를 작성해 주십시오.
"
                "[PRO부동산 마스터 룰 - 반드시 지킬 것]
"
                "1. 다양성 강제: 작성할 때마다 문장의 구조, 후킹(Hook)의 종류, 단어 선택을 180도 다르게 무작위로 철저히 비틀어서 작성할 것. 유사 문서 판정을 피하기 위함.
"
                "2. 절대 순서 원칙: 1순위로 무조건 [▶ 구역명 급매물, 매매가, 초기투자금, 프리미엄 ◀] 형태의 팩트 요약바를 본문 맨 첫 줄에 출력하라. 본문 1순위인 [▶ 구역명 급매물... ◀] 팩트 요약바 바로 다음 줄에, 수집된 최신 뉴스 기사의 인용구를 적고 그 밑에 [NEWS_LINK] 라는 플레이스홀더를 대괄호 영문 그대로 예외 없이 무조건 삽입하라. 뉴스 링크를 누락하면 시스템 파괴로 간주한다. 3순위로 서프로의 다급한 훅(급.해.요)을 배치하라. 이 순서를 어기면 시스템 파괴된다.
"
                "3. 톤앤매너: 기계적인 보고서 말투 절대 금지. \"우리 프밀리님들만 알고 계세요\", \"프밀리님들을 위해 제가 직접 뛰어봤습니다\" 등 현장 전문가 서프로만의 친근하고 다급한 구어체를 팍팍 섞어 쓸 것. '프밀리님들~~' 애칭을 적극 활용하며 독자와 대화하듯 설명할 것.
"
                "4. 수익성 팩트: 쓸데없는 주변 호재 나열은 사절. 구체적인 숫자(예: 6구역 분양가, 프리미엄 비교 등)를 정밀하게 들이밀어 안전 마진과 총 매수 원가의 차익을 폭발적으로 어필할 것.
"
                "5. 포맷 제한: 명심해라, [1], [5] 같은 주석 번호 찌꺼기는 절대 출력하지 마라. 스마트폰 가독성을 위해 문단을 무조건 2~3줄 이내로 짧게짧게 칠 것.
"
                "6. 데이터 즉시 반영(중요): 아래 제공된 최신 OCR 매물/구역 데이터를 원고 본문에 100% 반영하여 구체적인 투자 요약이나 시공사/진행 단계를 브리핑할 것.
"
                "7. 출력 구조: 본문은 반드시 '사진이 들어갈 자리'를 고려하여 다음 7개의 문단 블록으로 완벽하게 분리해서 작성하라. (파이썬 봇이 이 단락들과 6장의 이미지를 번갈아가며 교차 포스팅할 수 있도록 하기 위함)\n\n\"
                \" [문단 1] 최상단 요약바 (▶ 구역명 급매물, 매매가, 초기투자금, 프리미엄 ◀)\n\"
                \" (봇이 썸네일 자동 삽입)\n\"
                \" [문단 2] 서프로의 다급한 훅 (현장 분위기, 해당 매물의 희소성 강력 어필)\n\"
                \" (봇이 매물카드 자동 삽입)\n\"
                \" [문단 3] 1~2줄짜리 짧은 위치 안내 브릿지 멘트 (예: \"해당 매물의 대략적인 위치입니다.\")\n\"
                \" (봇이 주소카드 자동 삽입)\n\"
                \" [문단 4] 매물카드 기반 수익성 분석 (OCR 데이터 활용, 안전마진과 가성비 집중 해설)\n\"
                \" (봇이 구역카드 자동 삽입)\n\"
                \" [문단 5] 구역정보 브리핑 (OCR 활용) + 뉴스 인용 미래 가치 + 법제처 코너(실거주/전매 등)\n\"
                \" (봇이 명함 자동 삽입)\n\"
                \" [문단 6] 1~2줄짜리 짧은 상담 유도 브릿지 멘트 (예: \"자세한 상담은 언제든 아래로 연락주세요.\")\n\"
                \" (봇이 하단 배너 자동 삽입)\n\"
                \" [문단 7] PRO부동산 공식 카페 및 유튜브 채널 링크 등 마무리 인사\n\n"
                "8. 법률 팩트체크 강제: 제공된 [최신 OCR 기반 구역 현황 데이터]나 [법제처 법령 조회 결과]에서 '과소토지 입주권 조건', '매도인 자격 요건' 등 법적/행정적 필수 요건을 무조건 2가지 이상 발췌해라. 발췌한 요건 2가지를 이 상식 코너에서 '프밀리님들'에게 과외하듯 현장감 있게 설명해라. 요건 2개가 누락되면 실패다.
"
                "9. 법령 쓰레기 데이터 자체 필터링: 제공된 [법제처 실시간 법령 조회 결과]에 '올림픽', '박람회', '특별법' 등 재개발 투자와 무관한 쓰레기 법령이 포함되어 있다면 가차 없이 무시하고 버려라.
"
                "10. 토지거래허가구역 특수 룰: 만약 검색 키워드나 구역 정보에 '토지거래허가구역'이 포함되어 있다면, 쓸데없는 소리는 빼고 당신의 전문 지식을 동원하여 '부동산거래신고 등에 관한 법률'에 근거한 매수자 핵심 주의사항(예: 전세 끼고 갭투자 불가, 직접 실거주 의무, 사전 허가 필수 등)을 2~3줄로 요약해라. 이때 반드시 **'제몇조 제몇항에 의거한 내용인지' 정확한 법적 근거 조항(예: 부동산거래신고법 제11조 등)**을 포함시켜서 전문성을 더한 강력한 경고를 날려라. 이 경고를 '재개발법 상식 코너'에 프밀리님들을 위한 꿀팁으로 배치해라.

"
                "================================
"
                f"🌟 [최신 OCR 기반 매물 수익성 데이터]
{prop_ocr_text}
"
                "================================
"
                f"🏗️ [최신 OCR 기반 구역 현황 데이터]
{zone_ocr_text}
"
                "================================
"
                f"⚖️ [법제처 실시간 법령 조회 결과 - 이 내용을 법률 근거로 활용할 것]
"
                "반드시 이 내용이 출력되는 본문 구간 바로 위에 **[서프로와 함께하는 재개발법 상식 코너]**라는 소제목을 출력하고, 단순히 법을 읊는 게 아니라 \"이 법이 이번 매물/구역과 어떤 상관이 있는지\" 프밀리님들에게 과외해주듯 친절하게 덧붙여 설명할 것.
"
                f"{law_reference_text}
"
                "================================

"
                f"[제목]
(반드시 가장 맨 앞에 '[{search_zone_name}매물]' 형태의 타겟 키워드를 띄어쓰기 없이 고정한 채로 시작하고, 그 뒤에 매력적인 제목을 단 한 줄로 25자 내외 작성. 절대 제목 영역에 팩트 요약바나 다른 내용을 넣지 말 것)
"
                f"[본문]
(여기에 가장 앞줄에 무조건 '[▶ 구역명 급매물, 매매가, 초기투자금, 프리미엄 ◀]' 형태의 팩트 요약바를 단독으로 1줄 작성할 것. 그 다음 줄부터 본문을 작성하되, 인사말이나 브리핑 전환 구간 등에 반드시 '{search_zone_name}매물' 이라는 타겟 키워드를 띄어쓰기 없이 정확하게 붙여서 3~4회 자연스럽게 반복 삽입할 것. 그 외에는 기존 룰대로 뉴스 인용 등 서프로 톤앤매너로 작성)"
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

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🛑 [순수 뉴스 본문 업로드] NotebookLM 소스 정제
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if news_body and "뉴스 검색 실패" not in news_title:
                self.log_signal.emit(f"📦 [안전장치] 정제된 뉴스 본문을 NotebookLM에 소스로 주입 중...")
                news_fact_text = f"기사 제목: {news_title}\n기사 링크: {news_link}\n\n[순수 기사 본문]\n{news_body}"
                try:
                    await client.call_tool("notebook_add_text", {"notebook_id": notebook_id, "title": f"핵심뉴스_{search_zone_name}", "text": news_fact_text})
                    self.log_signal.emit("✅ 뉴스 본문 데이터 소스 주입 성공!")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 뉴스 본문 주입 실패 (무시하고 진행): {str(e)}")



            
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

            final_markdown = f"""{expert_content}

---
📞 VIP 투자 직통 상담: PRO부동산 서프로 (010-2319-0977)
👑 PRO부동산 공식 네이버 카페: https://cafe.naver.com/pro1023
📺 유튜브 채널: 신분상승TV
---
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
            self.result_signal.emit(final_markdown.strip())
        except Exception as e:
            import traceback
            self.log_signal.emit(f"❌ API 통신 에러 발생:\\n{traceback.format_exc()}")
        finally:
            self.finished_signal.emit()

# =========================================================
# [새로운 기능] 네이버 블로그 스텔스 원클릭 자동 포스팅 쓰레드
# =========================================================
class NaverAutoBlogWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, title, content, image_list, nid="jjh8818", npw="pro7150999!"):
        super().__init__()
        self.title = title
        self.content = content
        self.image_list = image_list
        self.nid = nid
        self.npw = npw

    def run(self):
        temp_files_to_delete = []
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver import ActionChains
            import math
            import sys
            import time
            import pyperclip
            import tempfile
            import shutil
            import os
            import undetected_chromedriver as uc
            import pyperclip
            import random
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            import sys
            import time
            import ast

            self.log_signal.emit("⚙️ 드라이버 초기화 및 프로필 로드 중...")
            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1200,900")
            
            # 강제 User-Agent 주입 (최신 Mac Chrome 기준)
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            options.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            })
            options.add_argument('--disable-notifications')
            
            # 최신 Chrome 버전에 맞추기 위한 동적 버전 추출
            version_main = 146
            try:
                import subprocess
                version_str = subprocess.check_output(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version']).decode('utf-8')
                version_main = int(version_str.strip().split()[2].split('.')[0])
            except Exception:
                pass

            driver = uc.Chrome(options=options, version_main=version_main)
            
            # CDP를 통한 navigator.webdriver 완벽 무력화
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                """
            })
                
            wait = WebDriverWait(driver, 20)

            self.log_signal.emit("🚀 네이버 로그인 (pyperclip 스텔스 우회)...")
            driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)
            
            cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            
            try:
                for tag, val in [("id", self.nid), ("pw", self.npw)]:
                    elem = wait.until(EC.element_to_be_clickable((By.ID, tag)))
                    elem.click()
                    time.sleep(0.5 + random.random() * 0.5)
                    
                    pyperclip.copy(val)
                    time.sleep(0.5)
                    
                    actions = ActionChains(driver)
                    actions.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
                    time.sleep(1.0 + random.random() * 0.5)
                
                login_btn = wait.until(EC.element_to_be_clickable((By.ID, "log.login")))
                login_btn.click()
                time.sleep(3)
            except Exception as e:
                self.log_signal.emit("⚠️ 자동 입력 중 캡챠가 난입했습니다! 수동 개입 모드로 전환합니다.")

            # 🚨 [스마트 비상 대기] 캡챠 발생 시 수동 개입 무한 대기 (인간-기계 협업)
            captcha_wait_time = 0
            while True:
                try:
                    current_url = driver.current_url
                    if "nidlogin.login" in current_url:
                        captcha_elements = driver.find_elements(By.XPATH, "//*[contains(@id, 'captcha') or contains(@id, 'chptcha') or contains(@class, 'captcha')]")
                        err_elements = driver.find_elements(By.CSS_SELECTOR, ".error_message, #err_empty_id")
                        
                        is_blocked = False
                        for c in captcha_elements:
                            if c.is_displayed(): is_blocked = True; break
                        for e in err_elements:
                            if e.is_displayed(): is_blocked = True; break
                            
                        if is_blocked or captcha_wait_time == 0:
                            if captcha_wait_time % 10 == 0:
                                self.log_signal.emit("🚨 켜져있는 크롬 창에서 직접 로그인을 마저 완료해주세요! (완료 시 자동 진행)")
                            time.sleep(2)
                            captcha_wait_time += 2
                        else:
                            time.sleep(2)
                            captcha_wait_time += 2
                    else:
                        break # 로그인 성공 후 페이지 이동됨
                except:
                    break

            self.log_signal.emit("📝 블로그 에디터(전체화면 모드) 진입...")
            # 테스트에서 대성공했던 마법의 URL로 교체 (iframe 제거)
            driver.get(f"https://blog.naver.com/{self.nid}/postwrite")
            time.sleep(5)
            # 팝업 제거 통합
            self.log_signal.emit("⚙️ 에디터 초기 설정(팝업취소/모바일/16pt) 적용 중...")
            try:
                js_code = (
                    "let popupBtn = document.querySelector('.se-popup-button-cancel, .button_cancel');\n"
                    "if(popupBtn) popupBtn.click();\n"
                )
                driver.execute_script(js_code)
                time.sleep(1)
            except Exception as e:
                self.log_signal.emit(f"⚠️ 에디터 설정 일부(팝업) 실패 (진행은 계속됩니다): {e}")

            # 모바일 화면 전환 (셀레니움 물리 클릭)
            try:
                mobile_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-util-button-device-mobile, button[data-log='flbbtn.vtablet']")))
                mobile_btn.click()
                time.sleep(2.0)
            except Exception as e:
                self.log_signal.emit("⚠️ 모바일 화면 전환 버튼 클릭 실패 (이미 적용되어 있거나 UI 변경됨)")

            # ==========================================
            # [Step 2] 제목 칸에 텍스트 입력 (JS 강제 실행)
            # ==========================================
            self.log_signal.emit("✍️ 스마트에디터: 제목칸 클릭 및 타이핑 (ActionChains)...")
            actions = ActionChains(driver)

            # 제목칸 명시적 클릭
            title_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.se-documentTitle')))
            title_element.click()
            time.sleep(0.5)

            # 제목 클립보드 붙여넣기
            safe_title = self.title.replace('`', '').replace('"', '\"').replace('\n', ' ')
            pyperclip.copy(safe_title)
            actions.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
            time.sleep(0.5)

            # Enter 눌러서 본문으로 이동
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(0.5)

            # 3 & 4. 본문 텍스트와 사진 교차 삽입
            self.log_signal.emit("📤 스마트에디터: 본문 텍스트 & 사진 교차 업로드 진행 중...")
            img_list = [img for img in self.image_list if os.path.exists(img)]
            num_images = len(img_list)

            paragraphs = [p for p in self.content.strip().split("\n\n") if p.strip()]

            if num_images == 0:
                chunks = ["\n\n".join(paragraphs)]
            else:
                num_chunks = num_images + 1
                chunk_size = max(1, len(paragraphs) // num_chunks)
                chunks = []
                for i in range(num_chunks):
                    if i == num_chunks - 1:
                        chunks.append("\n\n".join(paragraphs[i * chunk_size:]))
                    else:
                        chunks.append("\n\n".join(paragraphs[i * chunk_size : (i+1) * chunk_size]))

            max_iters = max(len(chunks), num_images)
            for i in range(max_iters):
                if i < len(chunks) and chunks[i].strip():
                    chunk_text = chunks[i].strip()
                    pyperclip.copy(chunk_text)
                    time.sleep(0.5)
                    
                    actions.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
                    time.sleep(1.0)
                    
                    self.log_signal.emit(f"📝 텍스트 파트 {i+1}/{len(chunks)} 붙여넣기 완료")
                
                # 줄바꿈 (Enter 2번) -> 여백 주기
                actions.send_keys(Keys.ENTER).perform()
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.5)
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # [사진 파트] 업로드 후 커서 포커스 복구 필수!
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if i < num_images:
                    img_path = img_list[i]
                    abs_img_path = os.path.abspath(img_path)
                    try:
                        safe_temp_path = os.path.join(tempfile.gettempdir(), f"blog_upload_temp_{i}.png")
                        shutil.copy(abs_img_path, safe_temp_path)
                        temp_files_to_delete.append(safe_temp_path)

                        photo_btns = driver.find_elements(By.CSS_SELECTOR, "button.se-image-toolbar-button")
                        if photo_btns:
                            js_click_code = (
                                "var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});\n"
                                "arguments[0].dispatchEvent(evt);\n"
                            )
                            driver.execute_script(js_click_code, photo_btns[0])
                            time.sleep(1.5)
                            
                            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                            if inputs:
                                try:
                                    driver.execute_script("arguments[0].style.display = 'block';", inputs[-1])
                                    inputs[-1].send_keys(safe_temp_path)
                                except Exception:
                                    try:
                                        inputs[-1].send_keys(safe_temp_path)
                                    except Exception as e:
                                        self.log_signal.emit(f"⚠️ 사진 {i+1} 임의 전송 실패: {e}")
                                        
                        # 렌더링 대기 (에디터가 이미지를 소화하도록 넉넉히)
                        self.log_signal.emit(f"⏳ 사진 {i+1}번 렌더링 대기 중... (5초)")
                        time.sleep(5.0)
                        
                        # ★ 사진 업로드 후 포커스 강제 복구 (가장 중요)
                        self.log_signal.emit("🖱️ 사진 업로드 완료 – 하단 스크롤 및 포커스 강제 복구 중...")
                        try:
                            # 1단계: 강제로 스크롤을 끝까지 내림
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1.5)  # 렌더링 후 스크롤 대기
                        except Exception:
                            pass
                        
                        # 2단계: 커서를 끝으로 보내고 Enter로 새로운 문단 강제 개설
                        actions.send_keys(Keys.END).perform()
                        time.sleep(0.5)
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(1.0)
                        
                    except Exception as e:
                        self.log_signal.emit(f"⚠️ 이미지 업로드 오류: {e}")

            self.log_signal.emit("🎉 [완벽 성공] 원고 자동 포스팅 렌더링 완료!\n✨ 잠시 후 열린 브라우저에서 최종 교정 후 우측 상단의 [발행] 버튼을 눌러주세요!")
            
            # 셀레니움 브라우저 유지 (User가 수동으로 '발행' 버튼 클릭 및 닫기 필요)
            while True:
                time.sleep(100)

        except Exception as e:
            import traceback
            self.log_signal.emit(f"❌ 포스팅 실패 에러 보고서:\n{traceback.format_exc()}")
        finally:
            # 안전한 임시 파일 정리 로직
            for temp_file in temp_files_to_delete:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except: pass
            self.finished_signal.emit()


class ProRealEstateAIPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 AI 기획비서 - 일체형 매물생성 스튜디오 탑재 (원본 매립 모델)")
        self.resize(1350, 950)
        self.setStyleSheet("background-color: #f7f9fc;")
        self.file_paths = {'thumb': '', 'prop': '', 'addr': '', 'zone': '', 'card': '', 'banner': ''}
        
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 1. 상단 검색 및 이미지 드롭 구역
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("검색어를 입력하세요 (예: 노량진6구역 재개발 최신 동향)")
        self.query_input.setFont(QFont("Malgun Gothic", 12))
        self.query_input.setStyleSheet("""
            QLineEdit {
                padding: 15px; border: 2px solid #8e44ad; border-radius: 5px; background-color: #ffffff;
            }
            QLineEdit:focus { border: 2px solid #8e44ad; }
        """)
        self.query_input.returnPressed.connect(self.start_ai_planner)
        self.query_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_fetch_news = QPushButton("📰 뉴스 기사 가져오기")
        self.btn_fetch_news.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        self.btn_fetch_news.setStyleSheet("QPushButton { background-color: #2980b9; color: white; padding: 15px; border-radius: 5px; } QPushButton:hover { background-color: #3498db; }")
        self.btn_fetch_news.clicked.connect(self.fetch_news)

        self.law_keyword_input = QLineEdit()
        self.law_keyword_input.setPlaceholderText("⚖️ 법제처 특수 검색어 (예: 과소토지, 무허가건축물) - 비워두면 구역명 자동 적용")
        self.law_keyword_input.setFont(QFont("Malgun Gothic", 11))
        self.law_keyword_input.setStyleSheet("border: 2px dashed #27ae60; padding: 10px; border-radius: 5px;")

        self.combo_news = QComboBox()
        self.combo_news.addItem("버튼을 눌러 뉴스를 수집하세요.")
        self.combo_news.setFont(QFont("Malgun Gothic", 10))
        self.combo_news.setStyleSheet("background-color: #f4f4f4; color: #0055FF; font-weight: bold; padding: 10px; border-radius: 5px; border: 1px solid #bdc3c7;")
        self.combo_news.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.news_linksList = []

        self.image_drop = ImageDropLabel("카드 생성 시 미리보기는 원본 팝업을 참고하세요")
        self.image_drop.setFixedSize(300, 90)
        
        # 왼쪽에 검색어와 뉴스, 오른쪽에 이미지드롭
        left_top_layout = QVBoxLayout()
        
        search_box = QHBoxLayout()
        search_box.addWidget(self.query_input)
        search_box.addWidget(self.btn_fetch_news)
        
        left_top_layout.addLayout(search_box)
        left_top_layout.addWidget(self.law_keyword_input)
        left_top_layout.addWidget(self.combo_news)
        
        top_layout.addLayout(left_top_layout)
        top_layout.addWidget(self.image_drop)
        main_layout.addLayout(top_layout, 1)
        
        # 2. 부품 생산 스튜디오 (외부 모듈 연결)
        maker_group = QGroupBox("🔥 1단계: 부품 생산 (이미지 렌더링 팩토리)")
        maker_group.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        maker_group.setStyleSheet("""
            QGroupBox { border: 2px solid #e74c3c; border-radius: 8px; margin-top: 15px; padding-top: 15px; background-color: #ffffff; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #c0392b; }
        """)
        maker_layout = QVBoxLayout(maker_group)
        
        b0 = QPushButton("0) 썸네일 생성기 (정방형)")
        b0.clicked.connect(lambda: self.run_script("thumbnail_maker.py"))
        b0.setStyleSheet("color: #FF00FF; font-weight: bold; padding: 10px; font-size: 14px;")

        b1 = QPushButton("1) 구역정보 생성기 (1~8구역)")
        b1.clicked.connect(lambda: self.run_script("info_1~8maker.py"))
        b1.setStyleSheet("color: #0055FF; font-weight: bold; padding: 10px; font-size: 14px;")

        b2 = QPushButton("2) 매물카드 생성기")
        b2.clicked.connect(lambda: self.run_script("property_maker_final_v61.py"))
        b2.setStyleSheet("color: #009966; font-weight: bold; padding: 10px; font-size: 14px;")

        b3 = QPushButton("3) 주소카드 생성기")
        b3.clicked.connect(lambda: self.run_script("adress.py"))
        b3.setStyleSheet("color: #FF9900; font-weight: bold; padding: 10px; font-size: 14px;")

        b_all = QPushButton("🌟 모든 생성기 한 번에 띄우기 (일괄 실행)")
        b_all.clicked.connect(self.run_all_makers)
        b_all.setStyleSheet("color: white; background-color: #8e44ad; font-weight: bold; padding: 12px; font-size: 15px; border-radius: 5px;")

        maker_layout.addWidget(b0)
        maker_layout.addWidget(b1)
        maker_layout.addWidget(b2)
        maker_layout.addWidget(b3)
        maker_layout.addWidget(b_all)
        main_layout.addWidget(maker_group, 2)

        # 2.5 자동 스캔 (신규 추가된 부분)
        scan_group = QGroupBox("📸 부품 스캔 (이미지 매칭 확인)")
        scan_group.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        scan_group.setStyleSheet("QGroupBox { border: 2px solid #3498db; border-radius: 8px; margin-top: 5px; padding-top: 15px; background-color: #ffffff; } QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2980b9; }")
        
        v_scan = QVBoxLayout()
        self.labels = {}
        self.preview_labels = {}
        file_map = [('thumb', '0. 썸네일'), ('prop', '1. 매물카드'), ('addr', '2. 주소카드'), ('zone', '3. 구역정보'), ('card', '4. 명함'), ('banner', '5. 배너')]

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(15)
        for idx, (key, name) in enumerate(file_map):
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            
            l_name = ClickableLabel(name)
            l_name.setFixedWidth(70)
            l_name.setStyleSheet("color: #0055FF; font-weight: bold; text-decoration: underline;")
            l_name.setCursor(Qt.PointingHandCursor)
            l_name.clicked.connect(lambda k=key: self.open_generator(k))
            
            l_preview = ClickableLabel("미리보기")
            l_preview.setFixedSize(50, 35)
            l_preview.setAlignment(Qt.AlignCenter)
            l_preview.setStyleSheet("border: 1px dashed gray; font-size: 10px; background-color: #fdfdfd;")
            l_preview.setCursor(Qt.PointingHandCursor)
            l_preview.clicked.connect(lambda k=key: self.open_preview_image(k))
            self.preview_labels[key] = l_preview
            
            l_file = QLabel("파일 없음"); l_file.setStyleSheet("color: #FF0000; font-size: 10px;")
            self.labels[key] = l_file
            btn_chg = QPushButton("변경"); btn_chg.setFixedWidth(40); btn_chg.setStyleSheet("background-color: #E0E0E0; color: black; font-size: 10px; padding: 2px;")
            btn_chg.clicked.connect(lambda _, k=key: self.manual_select(k))
            
            h.addWidget(l_name); h.addWidget(l_preview); h.addWidget(l_file); h.addWidget(btn_chg)
            grid_layout.addLayout(h, idx // 3, idx % 3)

        v_scan.addLayout(grid_layout)
        
        btn_rescan = QPushButton("🔄 이미지 자동 매칭 (다시 찾기)")
        btn_rescan.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        btn_rescan.setStyleSheet("background-color: #f39c12; color: white; padding: 5px; border-radius: 5px;")
        btn_rescan.clicked.connect(self.scan_files)
        v_scan.addWidget(btn_rescan)
        
        scan_group.setLayout(v_scan)
        main_layout.addWidget(scan_group, 2)

        # 3. 로그인 설정 (신규)
        settings_layout = QHBoxLayout()
        settings_layout.addStretch()
        
        # ID/PW 입력 필드
        self.naver_id_input = QLineEdit("jjh8818")
        self.naver_id_input.setPlaceholderText("네이버 ID")
        self.naver_id_input.setFont(QFont("Consolas", 12))
        self.naver_id_input.setFixedWidth(120)
        self.naver_id_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        
        self.naver_pw_input = QLineEdit("pro7150999!")
        self.naver_pw_input.setPlaceholderText("네이버 PW")
        self.naver_pw_input.setFont(QFont("Consolas", 12))
        self.naver_pw_input.setEchoMode(QLineEdit.Password)
        self.naver_pw_input.setFixedWidth(130)
        self.naver_pw_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")

        settings_layout.addWidget(QLabel("🔑 네이버 포스팅 자동화 계정 ID: "))
        settings_layout.addWidget(self.naver_id_input)
        settings_layout.addWidget(QLabel(" PW: "))
        settings_layout.addWidget(self.naver_pw_input)
        
        main_layout.addLayout(settings_layout)

        # 4. 보라색 실행 버튼 구역
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("🚀 실제 데이터 기반 무한 리서치 시작!")
        self.run_btn.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        self.run_btn.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; padding: 20px; border-radius: 12px; } QPushButton:hover { background-color: #732d91; } QPushButton:disabled { background-color: #95a5a6; }")
        self.run_btn.clicked.connect(self.start_ai_planner)

        self.post_btn = QPushButton("📝 VVIP 블로그 자동 원격 포스팅")
        self.post_btn.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        self.post_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; padding: 20px; border-radius: 12px; } QPushButton:hover { background-color: #219653; } QPushButton:disabled { background-color: #95a5a6; }")
        self.post_btn.clicked.connect(self.start_auto_post)
        
        self.auth_btn = QPushButton("🔑 구글 로그인\n(쿠키 갱신)")
        self.auth_btn.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        self.auth_btn.setFixedSize(140, 75)
        self.auth_btn.setStyleSheet("QPushButton { background-color: #e67e22; color: white; border-radius: 12px; } QPushButton:hover { background-color: #d35400; }")
        self.auth_btn.clicked.connect(self.run_auth_refresh)
        
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.post_btn)
        btn_layout.addWidget(self.auth_btn)
        main_layout.addLayout(btn_layout, 1)
        
        # 4. 하단 모니터/뷰어 구역
        splitter = QSplitter(Qt.Horizontal)
        
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0,0,0,0)
        log_label = QLabel("📺 API 실시간 응답 모니터")
        log_label.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #f39c12; font-family: Consolas; font-size: 13px; padding: 10px; border-radius: 8px; }")
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_viewer)
        
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0,0,0,0)
        result_label = QLabel("📜 통신 완료 산출물 뷰어")
        result_label.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        self.result_viewer = QTextBrowser()
        self.result_viewer.setStyleSheet("QTextBrowser { background-color: #ffffff; border: 2px solid #ecf0f1; border-radius: 8px; padding: 15px; font-size: 14px; }")
        result_layout.addWidget(result_label)
        result_layout.addWidget(self.result_viewer)
        
        splitter.addWidget(log_widget)
        splitter.addWidget(result_widget)
        splitter.setSizes([450, 850])
        main_layout.addWidget(splitter, 4)
        
        # 첫 실행 시 자동 스캔 처리
        self.scan_files(first_boot=True)
        self.load_settings()

    def load_settings(self):
        import os, json
        from PySide6.QtGui import QPixmap
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "query" in data:
                        self.query_input.setText(data["query"])
                    if "law_keyword" in data:
                        self.law_keyword_input.setText(data["law_keyword"])
                    if "naver_id" in data:
                        self.naver_id_input.setText(data["naver_id"])
                    if "naver_pw" in data:
                        self.naver_pw_input.setText(data["naver_pw"])
                    
                    # ✅ [기억 복원] 부품 이미지 경로 6종 복원
                    saved_paths = data.get("file_paths", {})
                    for key, path in saved_paths.items():
                        if key in self.file_paths and path and os.path.exists(path):
                            # scan_files()가 이미 더 좋은 파일을 찾은 경우 덮어쓰지 않음
                            # (파일 없음 상태인 경우에만 저장된 경로로 복원)
                            if not self.file_paths.get(key):
                                self.file_paths[key] = path
                                fname = os.path.basename(path)
                                if len(fname) > 20: fname = fname[:8] + "..." + fname[-8:]
                                self.labels[key].setText(fname)
                                self.labels[key].setStyleSheet("color: #9900cc; font-weight: bold; font-size: 10px;")
                                pixmap = QPixmap(path)
                                scaled_pix = pixmap.scaled(self.preview_labels[key].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                self.preview_labels[key].setPixmap(scaled_pix)
                                self.preview_labels[key].setStyleSheet("border: 1px solid #9900cc;")
                    
                    if hasattr(self, 'maker_app'):
                        if "maker_zone" in data:
                            self.maker_app.combo_zone.setCurrentText(data["maker_zone"])
                        if "maker_entries" in data:
                            for k, v in data["maker_entries"].items():
                                if k in self.maker_app.entries:
                                    self.maker_app.entries[k].setText(v)
                                    
                    # ✅ [기억 복원] 뉴스 리스트 및 선택 인덱스 복원
                    if "news_items" in data and "news_linksList" in data:
                        self.combo_news.clear()
                        for item in data["news_items"]:
                            self.combo_news.addItem(item)
                        self.news_linksList = data["news_linksList"]
                        if "news_index" in data and 0 <= data["news_index"] < len(self.news_linksList):
                            self.combo_news.setCurrentIndex(data["news_index"])

                    # ✅ [기억 복원] 마지막 작성된 블로그 초안(결과물) 복원
                    if "last_draft_text" in data:
                        self.result_viewer.setHtml(data["last_draft_text"])
                            
            except Exception as e:
                pass

    def closeEvent(self, event):
        import os, json
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner_settings.json")
        try:
            data = {
                "query": self.query_input.text(),
                "law_keyword": self.law_keyword_input.text(),
                "naver_id": self.naver_id_input.text(),
                "naver_pw": self.naver_pw_input.text()
            }
            # ✅ [기억 저장] 현재 부품 이미지 경로 6종을 JSON에 보존 (내용 있는 것만)
            if hasattr(self, 'file_paths'):
                data["file_paths"] = {k: v for k, v in self.file_paths.items() if v and os.path.exists(v)}
            
            if hasattr(self, 'maker_app'):
                data["maker_zone"] = self.maker_app.combo_zone.currentText()
                maker_entries_data = {}
                for k, v in self.maker_app.entries.items():
                    maker_entries_data[k] = v.text()
                data["maker_entries"] = maker_entries_data
                
            # ✅ [기억 저장] 뉴스 목록과 선택 상태 저장
            if hasattr(self, 'news_linksList') and self.news_linksList:
                data["news_items"] = [self.combo_news.itemText(i) for i in range(self.combo_news.count())]
                data["news_linksList"] = self.news_linksList
                data["news_index"] = self.combo_news.currentIndex()

            # ✅ [기억 저장] 마지막 작성된 블로그 초안 보존 (앱 재시작 시 공란 방지)
            data["last_draft_text"] = self.result_viewer.toHtml()
                
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        super().closeEvent(event)

    def fetch_news(self):
        query = self.query_input.text().strip()
        if not query:
            self.append_log("⚠️ 최상단의 검색어 창에 구역명을 먼저 입력해주세요 (예: 노량진1구역)")
            return
            
        self.btn_fetch_news.setEnabled(False)
        self.combo_news.clear()
        self.combo_news.addItem("뉴스를 수집하는 중입니다... (약 0.5초 소요)")
        QApplication.processEvents()
        
        import re
        # 뉴스 검색용 쿼리 정제 (매물, 급매 등의 단어 배제)
        news_query = re.sub(r'(매물|급매물|초급매|급매|매매|전세|월세|임대)', '', query).strip()
        if not news_query:
            news_query = query
            
        self.append_log(f"🔎 원본 '{query}' ➔ 정제된 '{news_query}' 기반 최신 뉴스 검색 중...")
        
        import requests
        import urllib.parse
        import xml.etree.ElementTree as ET
        try:
            encoded_query = urllib.parse.quote(news_query)
            # when:7d 추가: 최근 7일 내의 뉴스만 검색, 똑같은 옛날 뉴스가 뜨는 것 방지
            url = f"https://news.google.com/rss/search?q={encoded_query}%20when%3A7d&hl=ko&gl=KR&ceid=KR:ko"
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            res = requests.get(url, headers=headers, timeout=5)
            
            root = ET.fromstring(res.text)
            items = root.findall('.//item')
            
            # 파이썬 내장 라이브러리로 pubDate 추출 및 최신순 정렬
            from email.utils import parsedate_to_datetime
            import datetime
            def get_pub_date(item):
                pd = item.find('pubDate')
                if pd is not None and pd.text:
                    try:
                        return parsedate_to_datetime(pd.text)
                    except:
                        pass
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            
            items.sort(key=get_pub_date, reverse=True)
            
            self.combo_news.clear()
            self.news_linksList.clear()
            
            if not items:
                self.combo_news.addItem("결과: 관련 뉴스를 찾을 수 없습니다.")
                self.append_log("❌ 결과: 관련 뉴스를 찾을 수 없습니다.")
                self.btn_fetch_news.setEnabled(True)
                return
                
            count = 0
            for item in items:
                if count >= 10:
                    break
                    
                title_elem = item.find('title')
                link_elem = item.find('link')
                
                title = title_elem.text.strip() if title_elem is not None else "제목 없음"
                link = link_elem.text.strip() if link_elem is not None else ""
                
                self.combo_news.addItem(f"[{count+1}] {title}")
                self.news_linksList.append(link)
                count += 1
                
            self.append_log(f"✅ [뉴스 스크랩 성공] 총 {count}개의 뉴스를 가져왔습니다. 콤보박스에서 사용할 뉴스를 선택해주세요.")
            
        except requests.exceptions.Timeout:
            self.combo_news.clear()
            self.combo_news.addItem("뉴스 수집 실패 (시간 초과)")
            self.append_log("❌ 뉴스 스크랩 실패: 서버 응답 시간 초과 (5초)")
        except Exception as e:
            self.combo_news.clear()
            self.combo_news.addItem("뉴스 수집 실패")
            self.append_log(f"❌ 뉴스 스크랩 실패: {e}")
            
        self.btn_fetch_news.setEnabled(True)

    def start_ai_planner(self, *args):
        import os
        query = self.query_input.text()
        
        idx = self.combo_news.currentIndex()
        if idx < 0 or not hasattr(self, 'news_linksList') or not self.news_linksList or idx >= len(self.news_linksList):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "경고", "먼저 '뉴스 기사 가져오기' 버튼을 누르고 기사를 선택해주세요!")
            return
            
        selected_text = self.combo_news.currentText()
        if selected_text.startswith("["):
            parts = selected_text.split("] ", 1)
            if len(parts) > 1:
                news_title = parts[1]
            else:
                news_title = selected_text
        else:
            news_title = selected_text
            
        news_link = self.news_linksList[idx]
        news_data = (news_title, news_link)
        
        # ==== 빨대 꽂기 기술 ====
        import json
        save_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", "last_card_data.json")
        card_raw_data = {}
        if os.path.exists(save_file_path):
            try:
                with open(save_file_path, "r", encoding="utf-8") as f:
                    card_raw_data = json.load(f)
            except:
                pass

        if not card_raw_data:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "오류", "저장된 매물카드 데이터가 없습니다. 먼저 '매물카드 생성기'를 실행하여 저장해주세요.")
            self.run_btn.setEnabled(True)
            self.query_input.setEnabled(True)
            self.image_drop.setAcceptDrops(True)
            return

        dist_display = card_raw_data.get('dist_display', '1구역')
        card_raw_data['dist_display'] = dist_display
        
        # 원본 생성기가 사진을 저장하는 절대 경로!
        auto_img_path = os.path.join(os.path.expanduser("~"), "Desktop", "카페글쓰기", f"매물정보_v62_{dist_display}.png")
        
        # UI에서 직접 드롭한 사진이 있다면 그걸 우선순위로, 없으면 원본 생성기가 저장한 최신 사진 사용
        img_path = getattr(self.image_drop, 'image_path', None)
        if not img_path and os.path.exists(auto_img_path):
            img_path = auto_img_path
            
        self.log_viewer.clear()
        self.result_viewer.clear()
        
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ NotebookLM 서버 통신 중... (절대 창을 닫지 마세요)")
        self.query_input.setEnabled(False)
        self.image_drop.setAcceptDrops(False)
        
        # API 통신 스레드 실행 (매물카드/구역정보카드 OCR 경로 추가 전달)
        prop_path = self.file_paths.get('prop', '') if hasattr(self, 'file_paths') else ''
        zone_path = self.file_paths.get('zone', '') if hasattr(self, 'file_paths') else ''
        law_keyword = self.law_keyword_input.text().strip()
        self.thread = AIPlannerThread(query, img_path, card_raw_data, news_data, prop_path or None, zone_path or None, law_keyword)
        self.thread.log_signal.connect(self.append_log)
        self.thread.result_signal.connect(self.show_result)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.auth_error_signal.connect(self.prompt_auth_refresh)
        self.thread.start()

    def run_script(self, script_name):
        base_dir = "/Users/seopro/Desktop/카페올리기"
        script_path = os.path.join(base_dir, script_name)
        
        if os.path.exists(script_path):
            try:
                import sys
                import subprocess
                from PySide6.QtWidgets import QMessageBox
                
                # [맥OS GUI 크래시 해결] 가상환경 PATH 제거로 Tkinter Abort Trap 6 방지
                clean_env = os.environ.copy()
                if "VIRTUAL_ENV" in clean_env:
                    venv_bin = os.path.join(clean_env["VIRTUAL_ENV"], "bin") + ":"
                    if "PATH" in clean_env:
                        clean_env["PATH"] = clean_env["PATH"].replace(venv_bin, "")
                    del clean_env["VIRTUAL_ENV"]
                
                if sys.platform == "darwin":
                    subprocess.Popen(["python3", script_name], cwd=base_dir, env=clean_env)
                else:
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    subprocess.Popen(["python", script_name], cwd=base_dir, creationflags=creationflags, env=clean_env)
                self.log_viewer.append(f"🔨 {script_name} 실행 완료")
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "실행 오류", f"'{script_name}' 실행 중 오류가 발생했습니다:\n{str(e)}")
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "오류", f"'{script_name}' 파일이 없습니다.\n경로: {script_path}")

    def run_all_makers(self):
        scripts = ["thumbnail_maker.py", "info_1~8maker.py", "property_maker_final_v61.py", "adress.py"]
        import time
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "일괄 실행", "모든 매물 생성기를 한 번에 띄웁니다.\n창이 여러 개 열리더라도 놀라지 마세요!")
        for s in scripts:
            self.run_script(s)
            time.sleep(0.5)

    def append_log(self, text, *args):
        self.log_viewer.append(text)
        self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())
        
    def show_result(self, markdown_text, *args):
        import os
        self.result_viewer.setPlainText(markdown_text)
        txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "최종_블로그원고.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        
    def on_finished(self, *args):
        from PySide6.QtCore import QTimer
        # UI 복원
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🚀 실제 데이터 기반 무한 리서치 시작!")
        self.query_input.setEnabled(True)
        self.image_drop.setAcceptDrops(True)
        
        result_text = self.result_viewer.toPlainText().strip()
        
        # ✅ 원고 완성 알림: 원고가 정상적으로 생성되었을 때만 초록 버튼 반짝임 활성화
        if result_text and "초안 생성 실패" not in result_text:
            self.append_log("\n" + "="*50)
            self.append_log("✅ [원고 완성!] 오른쪽 뷰어에서 원고를 검토하세요!")
            self.append_log("📢 내용이 마음에 들면 → [✅ 원고 확인 완료! 지금 발행!] 버튼을 눌러주세요.")
            self.append_log("="*50 + "\n")
            
            # 초록 버튼 텍스트 및 스타일 변경 (발행 대기 강조)
            self.post_btn.setText("✅ 원고 확인 완료! 지금 발행!")
            self.post_btn.setEnabled(True)
            
            # QTimer로 버튼 반짝임 애니메이션 (1초 간격, 6회)
            self._blink_count = 0
            self._blink_on = True
            self._blink_timer = QTimer(self)
            self._blink_timer.timeout.connect(self._blink_post_btn)
            self._blink_timer.start(600)

    def _blink_post_btn(self):
        """초록 버튼 반짝임 애니메이션 (6회 후 고정)"""
        if self._blink_count >= 12:
            self._blink_timer.stop()
            # 최종 상태: 밝은 초록으로 고정
            self.post_btn.setStyleSheet(
                "QPushButton { background-color: #f39c12; color: white; padding: 20px; border-radius: 12px; font-weight: bold; border: 3px solid #e67e22; }"
                "QPushButton:hover { background-color: #e67e22; }"
            )
            return
        
        if self._blink_on:
            self.post_btn.setStyleSheet(
                "QPushButton { background-color: #f1c40f; color: #1a1a1a; padding: 20px; border-radius: 12px; font-weight: bold; font-size: 16px; border: 3px solid #f39c12; }"
            )
        else:
            self.post_btn.setStyleSheet(
                "QPushButton { background-color: #27ae60; color: white; padding: 20px; border-radius: 12px; font-weight: bold; font-size: 16px; }"
                "QPushButton:hover { background-color: #219653; }"
            )
        self._blink_on = not self._blink_on
        self._blink_count += 1

    def prompt_auth_refresh(self, *args):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "인증 토큰 만료", "NotebookLM 서버 응답 거부(400 Error).\n구글 로그인(토큰 갱신)을 진행해야 합니다!\n\n상단의 주황색 [🔑 구글 로그인] 버튼을 눌러주세요.")

    def start_auto_post(self, *args):
        import os
        raw_text = self.result_viewer.toPlainText().strip()
        if not raw_text or len(raw_text) < 50:
            QMessageBox.warning(self, "오류", "먼저 [무한 리서치 시작]을 통해 원고를 생성해야 합니다.")
            return

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # [물리적 라인 절단기] [제목]과 [본문] 태그를 통한 완벽 분리 파싱
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        import re
        
        # [제목] 추출 (다음 [본문] 태그 이전까지)
        title_match = re.search(r'\[제목\](.*?)(?=\[본문\])', raw_text, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = title_match.group(1).replace('*', '').replace('#', '').strip()
        else:
            # 예외 처리: 태그를 못 찾았을 경우 첫 번째 줄을 시도
            lines_split = raw_text.strip().split('\n')
            title = lines_split[0].replace('[제목]', '').replace('제목:', '').replace('*', '').replace('#', '').strip()

        # [본문] 추출
        body_match = re.search(r'\[본문\](.*)', raw_text, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1).strip()
        else:
            # 예외 처리
            content = '\n'.join(lines_split[1:]).strip() if not title_match else raw_text.strip()

        if not title:
            title = "PRO부동산 스마트 브리핑 최신 정보"
            
        content += "\n\n👇 [PRO부동산] 프리미엄 컨설팅 & 스마트 매칭 시스템 👇\n실시간 분석 완료된 투자 자문부터 은밀한 VVIP 초급매까지!"

        # 2. 스캔된 매칭 목록에서 순서대로 이미지 가져오기
        ordered_keys = ['thumb', 'prop', 'addr', 'zone', 'card', 'banner']
        img_list = [self.file_paths[k] for k in ordered_keys if self.file_paths.get(k) and os.path.exists(self.file_paths[k])]

        # 2-1. 법제처에서 실시간 생성된 PPT 이미지 가져오기
        import glob
        law_images = sorted(glob.glob(os.path.join(os.path.expanduser("~"), "Desktop", "완전자동화", "임시_작업파일", "law_slide_*.png")))
        # 배너 바로 앞에(혹은 맨 끝에) 끼워넣기
        if law_images:
            banner_path = self.file_paths.get('banner', None)
            if banner_path in img_list:
                idx = img_list.index(banner_path)
                img_list = img_list[:idx] + law_images + img_list[idx:]
            else:
                img_list.extend(law_images)

        # 3. Vision 분석 박스(image_drop)에 입력된 이미지는 포스팅 리스트에서 절대 제외(Exclude)
        vision_img = getattr(self.image_drop, 'image_path', None)
        if vision_img in img_list:
            img_list.remove(vision_img)

        nid = self.naver_id_input.text().strip()
        npw = self.naver_pw_input.text().strip()

        self.post_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.post_btn.setText("⏳ 스텔스 포스팅 모듈 가동 중... (크롬 생성대기 & 봇 회피 중)")
        self.log_viewer.clear()
        
        # 블로그 포스터 스레드 실행
        self.post_thread = NaverAutoBlogWorker(title, content, img_list, nid, npw)
        self.post_thread.log_signal.connect(self.append_log)
        self.post_thread.finished_signal.connect(self.on_post_finished)
        self.post_thread.start()

    def on_post_finished(self):
        self.post_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.post_btn.setText("📝 VVIP 블로그 자동 원격 포스팅")

    def scan_files(self, first_boot=False):
        import glob
        import os
        from PySide6.QtGui import QPixmap
        search_dirs = [
            os.getcwd(), 
            os.path.join(os.path.expanduser("~"), "Desktop"), 
            os.path.join(os.path.expanduser("~"), "Desktop", "카페글쓰기"),
            os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유")
        ]
        patterns = {'thumb': '최종_썸네일_*.png', 'prop': '매물정보_v62_*.png', 'addr': '매물상세_위치보정완료_*.png', 'zone': '구역정보_완성본_*.png', 'card': 'real_my_card.png', 'banner': 'kakao_banner.jpg'}
        
        for key, pattern in patterns.items():
            all_found_files = [] 
            for d in search_dirs:
                if not os.path.exists(d): continue
                files = glob.glob(os.path.join(d, pattern))
                if files:
                    all_found_files.extend(files) 
            
            if all_found_files:
                found = max(all_found_files, key=os.path.getmtime)
                self.file_paths[key] = found
                # 긴 파일명 자르기
                fname = os.path.basename(found)
                if len(fname) > 20: fname = fname[:8] + "..." + fname[-8:]
                self.labels[key].setText(fname)
                self.labels[key].setStyleSheet("color: #009966; font-weight: bold; font-size: 10px;")
                
                # 미리보기 업데이트
                pixmap = QPixmap(found)
                scaled_pix = pixmap.scaled(self.preview_labels[key].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_labels[key].setPixmap(scaled_pix)
                self.preview_labels[key].setStyleSheet("border: 1px solid black;")
            else:
                self.file_paths[key] = ""
                self.labels[key].setText("파일 없음")
                self.labels[key].setStyleSheet("color: #FF0000; font-size: 10px;")
                
                # 미리보기 초기화
                self.preview_labels[key].clear()
                self.preview_labels[key].setText("미리보기")
                self.preview_labels[key].setStyleSheet("border: 1px dashed gray; font-size: 10px; background-color: #fdfdfd;")
        if not first_boot and hasattr(self, 'log_viewer') and self.log_viewer:
            self.append_log("✅ [정밀 스캔 완료] 최신 이미지로 UI가 업데이트되었습니다.")
                
    def manual_select(self, key):
        import os
        from PySide6.QtWidgets import QFileDialog
        from PySide6.QtGui import QPixmap
        f, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "Images (*.png *.jpg)")
        if f:
            self.file_paths[key] = f
            fname = os.path.basename(f)
            if len(fname) > 20: fname = fname[:8] + "..." + fname[-8:]
            self.labels[key].setText(fname)
            self.labels[key].setStyleSheet("color: #0000FF; font-weight: bold; font-size: 10px;")
            
            # 미리보기 업데이트
            pixmap = QPixmap(f)
            scaled_pix = pixmap.scaled(self.preview_labels[key].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_labels[key].setPixmap(scaled_pix)
            self.preview_labels[key].setStyleSheet("border: 1px solid black;")

    def open_preview_image(self, key):
        import os
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        if key in self.file_paths and os.path.exists(self.file_paths[key]):
            img_path = self.file_paths[key]
            
            dlg = QDialog(self)
            dlg.setWindowTitle("이미지 미리보기")
            dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(0, 0, 0, 0)
            
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(img_path)
            
            screen = QApplication.primaryScreen().geometry()
            max_w = int(screen.width() * 0.8)
            max_h = int(screen.height() * 0.8)
            
            if pixmap.width() > max_w or pixmap.height() > max_h:
                pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
            lbl.setPixmap(pixmap)
            layout.addWidget(lbl)
            
            # Click to close
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = lambda e: dlg.accept()
            
            dlg.exec()

    def open_generator(self, key):
        import subprocess
        import os
        from PySide6.QtWidgets import QMessageBox
        
        # 외부 앱 열기로 동작
        self.open_preview_image(key)

        # 바탕화면에 흩어져 있는 스튜디오 앱의 실제 경로 매핑
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        script_map = {
            'thumb': os.path.join(desktop_dir, '카페올리기', 'thumbnail_maker.py'),
            'prop': os.path.join(desktop_dir, '카페올리기', 'property_maker_final_v61.py'),
            'addr': os.path.join(desktop_dir, '카페올리기', 'adress.py'), 
            'zone': os.path.join(desktop_dir, '카페올리기', 'info_1~8maker.py') # 9_카페올리기_완벽본과 동일한 수기 입력 구역생성기 연결
        }
        
        script_path = script_map.get(key)
        if not script_path:
            QMessageBox.information(self, "안내", "해당 부품은 별도의 생성기가 필요 없는 고정 이미지이거나 특수 스크립트 연결이 없습니다.")
            return

        if not os.path.exists(script_path):
            QMessageBox.critical(self, "오류", f"생성기 스크립트를 찾을 수 없습니다:\n{script_path}")
            return
        try:
            import sys
            import os
            script_dir = os.path.dirname(script_path)
            script_name = os.path.basename(script_path)
            
            # [맥OS GUI 크래시 해결 핵심] 
            # 9_카페올리기_완벽본.py는 가상환경 없이 실행되어서 python3가 시스템 파이썬(Tkinter 호환)으로 정상 실행됩니다.
            # 하지만 V3는 .venv 가상환경에서 실행되므로, 자식 프로세스가 가상환경 파이썬을 따라가면서 Tkinter Abort Trap 6 에러가 납니다.
            # 9_카페올리기와 똑같이 동작하도록 자식 프로세스에 넘겨줄 환경변수에서 가상환경 경로를 강제로 삭제합니다.
            clean_env = os.environ.copy()
            if "VIRTUAL_ENV" in clean_env:
                venv_bin = os.path.join(clean_env["VIRTUAL_ENV"], "bin") + ":"
                if "PATH" in clean_env:
                    clean_env["PATH"] = clean_env["PATH"].replace(venv_bin, "")
                del clean_env["VIRTUAL_ENV"]
            
            if sys.platform == "darwin":
                subprocess.Popen(["python3", script_name], cwd=script_dir, env=clean_env)
            else:
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                subprocess.Popen(["python", script_name], cwd=script_dir, creationflags=creationflags, env=clean_env)
                
            if hasattr(self, 'append_log'):
                self.append_log(f"🔨 [{script_name}] 별도 생성기를 백그라운드에서 호출했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "실행 오류", f"'{script_name}' 실행 중 오류가 발생했습니다:\n{str(e)}")

    def run_auth_refresh(self, *args):
        import subprocess
        import os
        self.log_viewer.append("\n🔄 [보안 인증] 구글 로그인 창(크롬)을 호출합니다... (로그인 후 자동 종료됩니다!)")
        cmd = AUTH_EXEC if os.path.exists(AUTH_EXEC) else "notebooklm-mcp-auth"
        subprocess.Popen([cmd])

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = ProRealEstateAIPlanner()
    window.show()
    sys.exit(app.exec())
