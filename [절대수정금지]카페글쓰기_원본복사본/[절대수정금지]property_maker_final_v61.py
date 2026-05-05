import os
import sys
import re
import json
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QComboBox, QPushButton, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

try:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    CURRENT_DIR = os.getcwd()

SAVE_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", "last_card_data.json")

def safe_float(value):
    if not value: return 0.0
    try:
        clean_val = re.sub(r'[^0-9.]', '', str(value))
        return float(clean_val) if clean_val else 0.0
    except: return 0.0

def format_num(value):
    try:
        val = float(value)
        if val == int(val): return str(int(val))
        return str(round(val, 2))
    except: return str(value)

def draw_multicolor_centered(draw, x, y, parts, font, anchor_y="m"):
    total_width = 0
    for text, color in parts:
        total_width += draw.textlength(text, font=font)
    
    current_x = x - (total_width / 2)
    anchor_style = f"l{anchor_y}"
    
    for text, color in parts:
        draw.text((current_x, y), text, fill=color, font=font, anchor=anchor_style)
        current_x += draw.textlength(text, font=font)

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

def load_font(size):
    font_paths = [
        "malgunbd.ttf",
        os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", "malgunbd.ttf"),
        os.path.join(os.path.expanduser("~"), "Desktop", "PRO부동산_자동화_로컬최종본", "assets", "malgunbd.ttf"),
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "malgun.ttf"
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    return ImageFont.load_default()

def draw_val_unit_億(draw, x, y, value, font_val, font_unit, color):
    val_str = format_num(value)
    w_val = draw.textlength(val_str, font=font_val)
    w_unit = draw.textlength("억", font=font_unit)
    start_x = x - ((w_val + w_unit) / 2)
    draw.text((start_x, y), val_str, fill=color, font=font_val, anchor="lm")
    draw.text((start_x + w_val, y + 12), "억", fill=color, font=font_unit, anchor="lm")

def draw_adaptive_text(draw, x, y, text, font_candidates, color, max_width, anchor="mm"):
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
        
        f_header = load_font(95); f_brand = load_font(35)
        f_invest_val = load_font(115); f_invest_label = load_font(70); f_invest_unit = load_font(50)
        f_table_head = load_font(35); f_table_val = load_font(85); f_table_unit = load_font(35)
        f_list = load_font(38); f_list_sm = [load_font(38), load_font(34), load_font(26)]
        f_list_label_matched = load_font(38)
        f_right_sm = load_font(23); f_right_md = load_font(35)
        f_right_lg = load_font(65); f_right_contact = load_font(35)
        f_footer = load_font(35); f_platform = [load_font(21), load_font(18)]
        f_tax_val = load_font(40)

        # White Label 설정 불러오기
        wl_left = data.get('wl_left', '').strip()
        wl_right = data.get('wl_right', '').strip()

        # --- Header ---
        draw.rectangle([(0, 0), (width, 160)], fill=BLACK)
        brand_x_center = 150
        
        # 상단 좌측 앱 타이틀 고정
        draw.text((brand_x_center, 60), "대한민국 부동산", fill=WHITE, font=f_brand, anchor="mm")
        header_parts = [("NO.1", YELLOW), (" 플랫폼", WHITE)]
        draw_multicolor_centered(draw, brand_x_center, 110, header_parts, f_brand, anchor_y="m")
            
        draw.text((width/2 - 10, 80), f"노량진 {data['dist_display']}", fill=WHITE, font=f_header, anchor="mm")
        draw.text((width/2 + 410, 80), data['prop_type'], fill=YELLOW, font=load_font(100), anchor="mm")

        # --- Invest ---
        draw.rectangle([(0, 160), (width, 330)], fill=YELLOW)
        draw.text((width/2 - 250, 245), "초기투자금 :", fill=RED, font=f_invest_label, anchor="mm")
        draw_val_unit_億(draw, width/2 + 150, 245, data['invest_price'], f_invest_val, f_invest_unit, RED)

        # --- Table ---
        table_y, col_w = 330, width / 6
        draw.rectangle([(0, table_y), (col_w*4, table_y + 70)], fill=GRAY_BG)
        draw.rectangle([(0, table_y + 70), (col_w*4, table_y + 190)], fill=WHITE)
        draw.rectangle([(col_w*4, table_y), (width, table_y + 190)], fill=PINK_BG)
        
        # 임대/보증금 헤더 동적 적용
        rent_type_str = data.get('rent_type', '임대')
        cols = ["매매가", "프리미엄", "권리가", rent_type_str, "총 매수가", "안전마진"]
        vals = [data['p_sale'], data['p_premium'], data['p_rights'], data['rent_val'], data['p_total'], data['p_margin']]
        
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
        
        # 하단 화이트라벨 설정 적용 
        left_text = wl_left if wl_left else "대한민국 재개발 재건축 NO.1 플랫폼"
        draw_adaptive_text(draw, split_x + (width-split_x)/2, bot_y_start + 32, left_text, f_platform, BLACK, width-split_x-10, anchor="mm")
        
        contact_text = wl_right if wl_right else f"서프로 : {data.get('contact', '010.2319.0977')}"
        draw.text((split_x + (width-split_x)/2, 840), contact_text, fill=BLACK, font=f_right_contact, anchor="mm")

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
        
        QApplication.clipboard().setText(data.get('comp_type', ''))
        QMessageBox.information(parent, "완료", f"이미지 생성 완료!\n'구성타입'이 클립보드에 복사되었습니다!\n저장위치: {save_path}")
    except Exception as e: QMessageBox.critical(parent, "오류", f"이미지 생성 실패: {e}")

class PropertyMakerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 - 매물카드 생성기 (자동저장 & 클립보드 패치)")
        self.resize(650, 950)
        self.entries = {}
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        self.inner_layout = QVBoxLayout(content_widget)
        
        # 1. 구역 선택
        lbl_h1 = QLabel("[ 1. 구역 선택 ]")
        lbl_h1.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        lbl_h1.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl_h1)
        
        self.combo_zone = QComboBox()
        self.combo_zone.addItems(list(ZONE_DATA.keys()))
        self.combo_zone.currentTextChanged.connect(self.update_zone)
        self.inner_layout.addWidget(self.combo_zone)

        # 2. 가격 및 자동계산
        lbl_h2 = QLabel("[ 2. 가격 및 자동계산 ]")
        lbl_h2.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        lbl_h2.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl_h2)
        
        self.add_input("매물 타입", "prop_type", "1+1")
        self.add_input("3. 초기투자금(자동)", "invest_price", "6", "red")
        self.add_input("4. 매매가", "p_sale", "24")
        self.add_input("5. 프리미엄", "p_premium", "16.7", "red")
        self.add_input("6. 권리가(자동)", "p_rights", "16.8")
        self.add_input("7-1. 임대/보증금 헤더", "rent_type", "임대")
        self.add_input("7-2. 임대/보증금 금액", "rent_val", "13.5")
        self.add_input("8. 총 매수가(자동)", "p_total", "28")
        self.add_input("9. 안전마진(자동)", "p_margin", "10")

        # 취득세
        lbl_h3 = QLabel("[ 취득세 자동 계산 (세율 입력시 자동변경) ]")
        lbl_h3.setStyleSheet("color: darkgreen; font-weight: bold;")
        lbl_h3.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl_h3)
        
        tax_layout = QHBoxLayout()
        tax_layout.addWidget(QLabel("세율(%)"))
        ent_tax_rate = QLineEdit("3.5")
        self.entries['tax_rate'] = ent_tax_rate
        tax_layout.addWidget(ent_tax_rate)
        tax_layout.addWidget(QLabel("➡ 결과값:"))
        ent_tax_val = QLineEdit("8,400만원")
        ent_tax_val.setStyleSheet("color: blue; font-weight: bold;")
        self.entries['tax_val'] = ent_tax_val
        tax_layout.addWidget(ent_tax_val)
        self.inner_layout.addLayout(tax_layout)

        # 3. 상세 리스트
        lbl_h4 = QLabel("[ 3. 상세 리스트 ]")
        lbl_h4.setStyleSheet("color: magenta; font-weight: bold; font-size: 16px;")
        lbl_h4.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl_h4)
        
        for i in range(1, 6):
            self.add_input(f"L{i}. 내용", f"list_{i}", ZONE_DATA["1구역"][i-1])
            
        self.add_input("구성 타입", "comp_type", "84㎡")
        self.add_input("연락처", "contact", "010.2319.0977")

        # [ 4. 화이트라벨 설정 ]
        lbl_h_wl = QLabel("\n[ 4. 화이트라벨 설정 ]")
        lbl_h_wl.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        lbl_h_wl.setAlignment(Qt.AlignCenter)
        self.inner_layout.addWidget(lbl_h_wl)

        self.add_input("하단 좌측 문구 (상호명)", "wl_left", "대한민국 재개발 재건축 NO.1 플랫폼")
        self.add_input("하단 우측 문구 (대표명)", "wl_right", "서프로 : 010.2319.0977")

        btn = QPushButton("💾 저장 및 매물카드 생성")
        btn.setStyleSheet("background-color: #FFD400; font-weight: bold; font-size: 16px; padding: 15px;")
        btn.clicked.connect(self.on_generate)
        self.inner_layout.addWidget(btn)

        layout.addWidget(scroll)
        
        # 이벤트 연결
        for key in ['p_sale', 'p_premium', 'rent_val', 'tax_rate', 'comp_type', 'list_2', 'list_4']:
            if key in self.entries:
                self.entries[key].textChanged.connect(self.sync_calculations)

        for key in ['p_total', 'p_margin', 'tax_val']:
            self.entries[key].editingFinished.connect(lambda k=key: self.calc_expression(k))

    def add_input(self, label_text, key_name, default_val="", color="black"):
        h_layout = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(150)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
        ent = QLineEdit(default_val)
        h_layout.addWidget(lbl)
        h_layout.addWidget(ent)
        self.inner_layout.addLayout(h_layout)
        self.entries[key_name] = ent

    def update_zone(self, z):
        for i in range(1, 6):
            self.entries[f'list_{i}'].setText(ZONE_DATA[z][i-1])
        self.entries['tax_rate'].setText(ZONE_DATA[z][5])
        self.entries['tax_val'].setText(ZONE_DATA[z][6])
        self.sync_calculations()

    def sync_calculations(self, *args):
        if getattr(self, '_updating', False):
            return
        self._updating = True
        try:
            sale = safe_float(self.entries['p_sale'].text())
            prem = safe_float(self.entries['p_premium'].text())
            rent = safe_float(self.entries['rent_val'].text())
            
            rate = safe_float(self.entries['tax_rate'].text())
            rights = safe_float(self.entries['p_rights'].text())

            # [계산 1] 매매가/프리미엄/권리가 양방향 동기화
            sender = self.sender() if hasattr(self, 'sender') else None
            
            if sender == self.entries['p_rights']:
                # 권리가 직접 수정됨 -> 프리미엄 = 매매가 - 권리가
                prem = sale - rights
                self.entries['p_premium'].setText(format_num(prem))
            elif sender == self.entries['p_premium']:
                # 프리미엄 직접 수정됨 -> 권리가 = 매매가 - 프리미엄
                rights = sale - prem
                self.entries['p_rights'].setText(format_num(rights))
            elif sender == self.entries['p_sale']:
                # 매매가 직접 수정됨 -> 권리가를 기본 연동
                rights = sale - prem
                self.entries['p_rights'].setText(format_num(rights))
            elif sender is None and not self.entries['p_rights'].text():
                # 최초 실행 등
                rights = sale - prem
                self.entries['p_rights'].setText(format_num(rights))
            
            # [계산 2] 초기투자금 = 매매가 - 임대
            if not self.entries['invest_price'].hasFocus():
                self.entries['invest_price'].setText(format_num(sale - rent))
                
            # [계산 3] 총매수가 (L2 금액 단위 합산 + 5번 프리미엄)
            l2_text = self.entries['list_2'].text() if 'list_2' in self.entries else ""
            l2_prices = re.findall(r'([\d.]+)억', l2_text)
            if l2_prices:
                total_invest = sum(float(p) for p in l2_prices) + prem
            else:
                total_invest = prem + rights
                
            if not self.entries['p_total'].hasFocus():
                self.entries['p_total'].setText(format_num(total_invest))
            else:
                total_invest = safe_float(self.entries['p_total'].text())

            # [계산 4] 안전마진
            future_prices = re.findall(r'([\d.]+)억', self.entries['list_4'].text())
            if future_prices and total_invest > 0:
                future_price_total = sum(float(p) for p in future_prices)
                margin = future_price_total - total_invest
                if not self.entries['p_margin'].hasFocus():
                    self.entries['p_margin'].setText(format_num(margin))

            # [계산 5] 취득세
            if not self.entries['tax_val'].hasFocus():
                tax_final = int(sale * rate * 100)
                self.entries['tax_val'].setText(f"{tax_final:,}만원")

        except Exception as e:
            pass
        finally:
            self._updating = False

    def calc_expression(self, key):
        expr = self.entries[key].text().replace(" ", "").replace(",", "").replace("만원", "")
        try:
            if re.match(r'^[0-9.+\-*/()]+$', expr):
                result = eval(expr)
                if key == 'tax_val': self.entries[key].setText(f"{int(result):,}만원")
                else: self.entries[key].setText(format_num(result))
                self.sync_calculations()
        except: pass

    def save_data(self):
        data_map = {}
        for k, v in self.entries.items():
            data_map[k] = v.text()
        data_map['dist_display'] = self.combo_zone.currentText()
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data_map, f, ensure_ascii=False, indent=4)
        except Exception as e: print(f"저장 실패: {e}")

    def load_data(self):
        if not os.path.exists(SAVE_FILE): return
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data_map = json.load(f)
            
            for k, val in data_map.items():
                if k in self.entries:
                    self.entries[k].setText(val)
            if 'dist_display' in data_map:
                self.combo_zone.setCurrentText(data_map['dist_display'])
            self.sync_calculations()
        except Exception as e: print(f"불러오기 실패: {e}")

    def on_generate(self):
        self.save_data()
        data = {k: v.text() for k, v in self.entries.items()}
        data['dist_display'] = self.combo_zone.currentText()
        data['final_tax_str'] = self.entries['tax_val'].text()
        make_property_image(data, self)

if __name__ == "__main__":
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = PropertyMakerApp()
    window.show()
    sys.exit(app.exec())
