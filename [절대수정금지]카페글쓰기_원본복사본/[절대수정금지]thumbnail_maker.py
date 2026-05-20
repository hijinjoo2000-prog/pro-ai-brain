import os
import sys
import datetime
import json
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QComboBox, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

SAVE_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", "thumbnail_maker_last_session.json")

def make_thumb(dist_num, sub1, c1_code, p_num, inv_num, parent):
    try:
        district = dist_num.strip() if dist_num else ""
        sub2_text = f"P {p_num}억" if p_num.strip() else ""
        inv_price = f"{inv_num}억" if inv_num.strip() else ""
        sub1_text = f"★ {sub1} ★" if sub1.strip() else ""
        
        width, height = 800, 800
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        color_map = {"빨강": (255, 0, 0), "노랑": (255, 255, 0), "흰색": (255, 255, 255)}
        c1 = color_map.get(c1_code, (255, 255, 255))
        RED, YELLOW, WHITE = (255, 0, 0), (255, 255, 0), (255, 255, 255)
        c2 = RED 

        # OS 구분을 없애고 프로젝트 내부의 특정 폰트를 절대경로로 명시
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
        font_path = os.path.join(base_dir, "assets", "malgunbd.ttf")
            
        def get_fitting_font(text, max_width, initial_size):
            size = initial_size
            font = ImageFont.truetype(font_path, size)
            while size > 20:
                if hasattr(draw, 'textbbox'):
                    bbox = draw.textbbox((0,0), text, font=font)
                    w = bbox[2] - bbox[0]
                else:
                    w = draw.textsize(text, font=font)[0]
                if w <= max_width:
                    break
                size -= 2
                font = ImageFont.truetype(font_path, size)
            return font

        try:
            f_date = ImageFont.truetype(font_path, 35)
            f_live = ImageFont.truetype(font_path, 30)
            f_title = get_fitting_font(district, 740, 130)
            f_sub1 = get_fitting_font(sub1_text, 740, 70) if sub1_text else ImageFont.truetype(font_path, 70)
            f_sub2 = get_fitting_font(sub2_text, 740, 100) if sub2_text else ImageFont.truetype(font_path, 100)
            f_invest = get_fitting_font(f"초기투자금 {inv_price}", 740, 115) 
            f_brand = ImageFont.truetype(font_path, 25)
        except Exception as fe:
            QMessageBox.critical(parent, "오류", f"폰트 파일 오류: {fe}")
            return

        date_str = datetime.datetime.now().strftime("%y.%m.%d.")
        live_box_w, live_box_h = 120, 50
        gap = 15
        
        if hasattr(draw, 'textbbox'):
            date_bbox = draw.textbbox((0, 0), date_str, font=f_date)
            date_w = date_bbox[2] - date_bbox[0]
        else:
            date_w = draw.textsize(date_str, font=f_date)[0]
        
        total_header_w = live_box_w + gap + date_w
        start_x = (width - total_header_w) / 2
        header_y = 50
        
        draw.rectangle([(start_x, header_y), (start_x + live_box_w, header_y + live_box_h)], fill=RED)
        draw.text((start_x + live_box_w/2, header_y + live_box_h/2), "LIVE", fill=WHITE, font=f_live, anchor="mm")
        draw.text((start_x + live_box_w + gap, header_y + live_box_h/2), date_str, fill=WHITE, font=f_date, anchor="lm")
        
        title_y = header_y + live_box_h + 120 
        draw.text((width/2, title_y), district, fill=YELLOW, font=f_title, anchor="mm")
        
        sub1_y = title_y + 130
        draw.text((width/2, sub1_y), sub1_text, fill=c1, font=f_sub1, anchor="mm")
        
        box_y = 425
        box_h = 130
        margin_x = 30
        draw.rectangle([(margin_x, box_y), (width - margin_x, box_y + box_h)], fill=YELLOW)
        draw.text((width/2, box_y + box_h/2), f"초기투자금 {inv_price}", fill=RED, font=f_invest, anchor="mm", stroke_width=1, stroke_fill=RED)
        
        sub2_y = 650 
        if sub2_text:
            draw.text((width/2, sub2_y), sub2_text, fill=c2, font=f_sub2, anchor="mm")
        
        draw.text((width/2, 765), "대한민국 재개발.재건축 NO.1플랫폼", fill=WHITE, font=f_brand, anchor="mm")

        dist_num_safe = dist_num.strip() if dist_num else "none"
        save_path = os.path.join(os.path.expanduser("~"), "Desktop", f"최종_썸네일_{dist_num_safe}.png")
        image.save(save_path, "PNG")
        QMessageBox.information(parent, "성공", f"바탕화면에 생성 완료!\n{save_path}")
    except Exception as e:
        QMessageBox.critical(parent, "오류", f"실패: {e}")

class ThumbnailApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 NO.1 썸네일 제작기 Mac 호환판")
        self.resize(400, 550)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        lbl1 = QLabel("1. 구역명 (전체 직접 입력, 예: 신림1구역)")
        lbl1.setStyleSheet("font-weight: bold;")
        self.ent_dist = QLineEdit()
        self.ent_dist.setAlignment(Qt.AlignCenter)
        self.ent_dist.textChanged.connect(self.save_data)
        layout.addWidget(lbl1); layout.addWidget(self.ent_dist)

        lbl2 = QLabel("2. 첫 번째 줄 내용")
        lbl2.setStyleSheet("font-weight: bold;")
        self.ent_sub1 = QLineEdit()
        self.ent_sub1.setAlignment(Qt.AlignCenter)
        self.ent_sub1.textChanged.connect(self.save_data)
        layout.addWidget(lbl2); layout.addWidget(self.ent_sub1)

        self.combo_c1 = QComboBox()
        self.combo_c1.addItems(["흰색", "빨강", "노랑"])
        self.combo_c1.currentTextChanged.connect(self.save_data)
        layout.addWidget(self.combo_c1)

        lbl3 = QLabel("3. 초기투자금 (숫자만)")
        lbl3.setStyleSheet("font-weight: bold;")
        self.ent_inv = QLineEdit()
        self.ent_inv.setStyleSheet("color: red;")
        self.ent_inv.setAlignment(Qt.AlignCenter)
        self.ent_inv.textChanged.connect(self.save_data)
        layout.addWidget(lbl3); layout.addWidget(self.ent_inv)

        lbl4 = QLabel("4. 프리미엄(P) 숫자만 입력")
        lbl4.setStyleSheet("font-weight: bold;")
        self.ent_p = QLineEdit()
        self.ent_p.setStyleSheet("color: red;")
        self.ent_p.setAlignment(Qt.AlignCenter)
        self.ent_p.textChanged.connect(self.save_data)
        layout.addWidget(lbl4); layout.addWidget(self.ent_p)

        btn = QPushButton("🚀 썸네일 생성하기")
        btn.setStyleSheet("background-color: #FFD400; font-weight: bold; font-size: 14px; padding: 10px;")
        btn.clicked.connect(self.on_generate)
        layout.addWidget(btn)

    def on_generate(self):
        self.save_data()
        make_thumb(
            self.ent_dist.text(),
            self.ent_sub1.text(),
            self.combo_c1.currentText(),
            self.ent_p.text(),
            self.ent_inv.text(),
            self
        )

    def save_data(self, *args):
        data = {
            "dist": self.ent_dist.text(),
            "sub1": self.ent_sub1.text(),
            "c1": self.combo_c1.currentText(),
            "p": self.ent_p.text(),
            "inv": self.ent_inv.text()
        }
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            pass

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ent_dist.setText(data.get("dist", ""))
                    self.ent_sub1.setText(data.get("sub1", ""))
                    self.combo_c1.setCurrentText(data.get("c1", "흰색"))
                    self.ent_p.setText(data.get("p", ""))
                    self.ent_inv.setText(data.get("inv", ""))
            except Exception as e:
                pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThumbnailApp()
    window.show()
    sys.exit(app.exec())
