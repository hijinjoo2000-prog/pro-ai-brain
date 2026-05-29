# -*- coding: utf-8 -*-
import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

class InfoTableMaker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRO부동산 - 구역별 현황 표 이미지 팩토리 (V3 자동기억)")
        self.resize(1000, 500)
        self.setStyleSheet("background-color: #F5F5F5; font-family: 'Malgun Gothic';")
        
        # 🧠 [추가] 마지막 작업 내용을 기억할 세이브 파일 경로
        self.save_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "카페글쓰기", "table_memory.json")
        
        self.initUI()
        
        # UI 세팅 후 마지막 기억 불러오기
        self.load_memory()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 1. 타이틀 입력
        title_layout = QHBoxLayout()
        title_label = QLabel("📊 표 제목:")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #000000;")
        self.title_input = QLineEdit()
        self.title_input.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; background-color: #FFFFFF;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # 2. 데이터 테이블 (엑셀 형식)
        self.table = QTableWidget(8, 6)
        self.table.setHorizontalHeaderLabels(["구역", "브랜드", "가구수", "사업단계", "진행현황", "건설사"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white; gridline-color: #ddd; color: #000000;")
        layout.addWidget(self.table)
        
        # 3. 생성 버튼
        self.btn_generate = QPushButton("📸 고화질 표 이미지 생성 및 저장")
        self.btn_generate.setStyleSheet("""
            QPushButton { background-color: #1A1A1A; color: white; font-size: 16px; font-weight: bold; padding: 15px; border-radius: 8px; }
            QPushButton:hover { background-color: #4A4A4A; }
        """)
        self.btn_generate.clicked.connect(self.generate_image)
        layout.addWidget(self.btn_generate)

    # ==========================================
    # 🧠 [기억 장치 로직] 세이브 & 로드
    # ==========================================
    def load_memory(self):
        """프로그램 시작 시, 저장된 파일이 있으면 불러오고 없으면 기본값 세팅"""
        if os.path.exists(self.save_file_path):
            try:
                with open(self.save_file_path, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                    
                self.title_input.setText(memory.get("title", "노량진뉴타운 구역별 현황  (25년 10월 기준)"))
                table_data = memory.get("table", [])
                
                for row, row_data in enumerate(table_data):
                    for col, text in enumerate(row_data):
                        item = QTableWidgetItem(text)
                        item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, col, item)
                return
            except Exception as e:
                print(f"기억 불러오기 실패, 기본값으로 초기화: {e}")
        
        # 세이브 파일이 없거나 에러가 나면 최초 기본 데이터 세팅
        self.load_default_data()

    def load_default_data(self):
        self.title_input.setText("노량진뉴타운 구역별 현황  (25년 10월 기준)")
        default_data = [
            ["1구역", "오띠에르", "2,993", "사업시행인가", "관리처분인가 총회 완료", "포스코이앤씨"],
            ["2구역", "드파인", "411", "관리처분인가", "철거 완료", "SK에코플랜트"],
            ["3구역", "오띠에르", "1,253", "사업시행인가", "11월 관리처분인가 예정", "포스코건설"],
            ["4구역", "디에이치", "844", "관리처분인가", "철거마무리, 멸실등기예정", "현대건설"],
            ["5구역", "써밋", "727", "관리처분인가", "철거 준비 중", "대우건설"],
            ["6구역", "드파인", "1,499", "관리처분인가", "착공 시작", "SK에코플랜트·GS건설"],
            ["7구역", "드파인", "576", "관리처분인가", "이주 마무리 (철거준비)", "SK에코플랜트"],
            ["8구역", "아크로", "987", "관리처분인가", "철거 완료, 11월 착공예정", "DL이앤씨"]
        ]
        for row, row_data in enumerate(default_data):
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def save_memory(self):
        """현재 화면에 적힌 글씨들을 파일로 조용히 저장"""
        memory = {
            "title": self.title_input.text(),
            "table": []
        }
        for row in range(8):
            row_data = []
            for col in range(6):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            memory["table"].append(row_data)
            
        try:
            os.makedirs(os.path.dirname(self.save_file_path), exist_ok=True)
            with open(self.save_file_path, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"저장 실패: {e}")

    def closeEvent(self, event):
        """프로그램의 X버튼을 눌러서 끌 때 자동으로 기억(저장) 작동"""
        self.save_memory()
        event.accept()

    # ==========================================
    # 🎨 [이미지 생성 로직]
    # ==========================================
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def generate_image(self):
        # 📸 [추가] 이미지 생성 버튼을 누를 때도 한 번 더 든든하게 자동 저장!
        self.save_memory()
        
        try:
            img_w, img_h = 1200, 650
            bg_color = self.hex_to_rgb("#F5F5F5")
            image = Image.new('RGB', (img_w, img_h), bg_color)
            draw = ImageDraw.Draw(image)
            
            font_path = os.path.join(os.path.expanduser("~"), "Desktop", "PRO부동산_자동화_로컬최종본", "assets", "malgunbd.ttf")
            if not os.path.exists(font_path):
                font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc" 
            
            f_title = ImageFont.truetype(font_path, 40)
            f_header = ImageFont.truetype(font_path, 18)
            f_zone = ImageFont.truetype(font_path, 24)
            f_brand = ImageFont.truetype(font_path, 22)
            f_body = ImageFont.truetype(font_path, 20)
            f_footer = ImageFont.truetype(font_path, 16)
            
            title_text = self.title_input.text()
            draw.text((img_w/2, 50), title_text, fill=self.hex_to_rgb("#000000"), font=f_title, anchor="mm")
            
            col_widths = [110, 140, 110, 180, 380, 220]
            start_x = 30
            start_y = 130
            row_h = 50
            
            headers = ["", "브랜드", "가구수", "사업단계", "진행현황", "건설사"]
            curr_x = start_x
            for i, h_text in enumerate(headers):
                draw.text((curr_x + col_widths[i]/2, start_y - 20), h_text, fill=self.hex_to_rgb("#000000"), font=f_header, anchor="mm")
                curr_x += col_widths[i]
                
            for row in range(8):
                y = start_y + (row * row_h)
                draw.rectangle([(start_x, y), (start_x + sum(col_widths), y + row_h - 2)], fill=self.hex_to_rgb("#FFFFFF"))
                draw.line([(start_x, y + row_h - 2), (start_x + sum(col_widths), y + row_h - 2)], fill=(220,220,220), width=1)
                
                curr_x = start_x
                
                for col in range(6):
                    item = self.table.item(row, col)
                    text = item.text() if item else ""
                    
                    if col == 0: 
                        box_color = self.hex_to_rgb("#1A1A1A")
                        draw.rectangle([(curr_x, y), (curr_x + col_widths[col] - 2, y + row_h - 4)], fill=box_color)
                        draw.text((curr_x + col_widths[col]/2, y + row_h/2), text, fill=self.hex_to_rgb("#FFFFFF"), font=f_zone, anchor="mm")
                        
                    elif col == 1: 
                        box_color = self.hex_to_rgb("#6B664B") if row in [0, 2] else self.hex_to_rgb("#4A4A4A")
                        draw.rectangle([(curr_x, y), (curr_x + col_widths[col] - 2, y + row_h - 4)], fill=box_color)
                        text_fill = (245, 235, 160) if row in [0, 2] else (230, 230, 230)
                        draw.text((curr_x + col_widths[col]/2, y + row_h/2), text, fill=text_fill, font=f_brand, anchor="mm")
                        
                    else: 
                        text_color = self.hex_to_rgb("#000000") 
                        if col == 4: 
                            if "철거 완료" in text or "착공" in text:
                                text_color = self.hex_to_rgb("#E53935")
                            elif "11월 관리처분인가 예정" in text or ("예정" in text and "철거" not in text and "착공" not in text):
                                text_color = self.hex_to_rgb("#3A53A4")
                            elif "철거" in text or "멸실등기" in text:
                                text_color = self.hex_to_rgb("#4A4A4A")

                        draw.text((curr_x + col_widths[col]/2, y + row_h/2), text, fill=text_color, font=f_body, anchor="mm")
                    
                    curr_x += col_widths[col]

            footer_y = start_y + (8 * row_h) + 20
            draw.text((start_x + sum(col_widths) - 10, footer_y), "자료 : 재개발·재건축 NO.1플랫폼", fill=self.hex_to_rgb("#000000"), font=f_footer, anchor="rm")

            save_path = os.path.join(os.path.expanduser("~"), "Desktop", "카페글쓰기", "노량진구역별현황_V2.png")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            image.save(save_path, "PNG")
            
            QMessageBox.information(self, "성공", f"이미지가 성공적으로 생성되었습니다!\n저장위치: {save_path}")
            
            if sys.platform == "darwin":
                os.system(f"open '{save_path}'")
            else:
                os.startfile(save_path)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"이미지 생성 중 오류가 발생했습니다:\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = InfoTableMaker()
    ex.show()
    sys.exit(app.exec())