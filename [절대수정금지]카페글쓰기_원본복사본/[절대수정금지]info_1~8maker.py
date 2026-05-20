import sys
import os
import json
from datetime import datetime
import re
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QMessageBox, QScrollArea, QGridLayout, QFrame)
from PySide6.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

ZONES_DATA = {
    '1': {
        'dist_num': '1',
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
        'dist_num': '2',
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
        'dist_num': '3',
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
        'dist_num': '4',
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
        'dist_num': '5',
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
        'dist_num': '6',
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
        'dist_num': '7',
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
        'dist_num': '8',
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
        draw.text((width/2, header_h/2), f"노량진 {data_dict['dist_num']}구역", fill=WHITE, font=f_title, anchor="mm")

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
        filename = f"구역정보_완성본_(확인용)_노량진{dist_name}구역.png"
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

        self.add_input("1. 구역 번호(숫자)", "dist_num", "1")
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
    window = InfoMakerApp()
    window.show()
    sys.exit(app.exec())
