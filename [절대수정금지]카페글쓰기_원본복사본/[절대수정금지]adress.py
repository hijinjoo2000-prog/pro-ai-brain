import os
import sys
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# [1] 데이터 정의
# =============================================================================
ZONES_ADDR = {
    '1': {
        'b_area': '75m²', 'status': '관리처분인가 준비중',
        'l_area': '64m²', 'floor': '3층 / 저층',
        'rooms': '3 / 1', 'fee': '알수없음',
        'b_type': '다세대주택', 'direction': '남향',
        'use': '주택', 'approval': '1994.5.10.',
        'move_in': '협의', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 노량진동 312번지 일대',
    },
    '2': {
        'b_area': '철거완료', 'status': '철거 완료',
        'l_area': '137m²', 'floor': '철거완료',
        'rooms': '철거완료', 'fee': '없음',
        'b_type': '철거완료', 'direction': '철거완료',
        'use': '철거완료', 'approval': '철거완료',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 노량진동 278번지 일대',
    },
    '3': {
        'b_area': '218m²', 'status': '관리처분인가 예정',
        'l_area': '188m²', 'floor': '총 2층',
        'rooms': '12 / 4', 'fee': '세입자납부',
        'b_type': '다가구주택', 'direction': '남서향',
        'use': '주택', 'approval': '1989.4.12.',
        'move_in': '입주불가', 'parking': '주차불가',
        'addr_main': '소재지 : 동작구 노량진동 232번지 일대',
    },
    '4': {
        'b_area': 'ㅡ', 'status': '철거 진행 중',
        'l_area': '56m²', 'floor': 'ㅡ',
        'rooms': 'ㅡ', 'fee': 'ㅡ',
        'b_type': '다세대주택', 'direction': 'ㅡ',
        'use': '주택', 'approval': 'ㅡ',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 노량진동 294번지 일대',
    },
    '5': {
        'b_area': '59m²', 'status': '이주완료 / 철거준비',
        'l_area': '43m²', 'floor': '5층 / 2층',
        'rooms': '3 / 1', 'fee': '없음',
        'b_type': '공동주택', 'direction': '남동향',
        'use': '주택', 'approval': '1990.06.21.',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 노량진동 270번지 일대',
    },
    '6': {
        'b_area': '철거완료', 'status': '착공 중',
        'l_area': '63m²', 'floor': '철거완료',
        'rooms': '철거완료', 'fee': '없음',
        'b_type': '철거완료', 'direction': '철거완료',
        'use': '철거완료', 'approval': '철거완료',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 노량진동 294-220번지 일대',
    },
    '7': {
        'b_area': '213m²', 'status': '이주 마무리 단계',
        'l_area': '209m²', 'floor': '총 2층',
        'rooms': '10 / 3', 'fee': '알수없음',
        'b_type': '단독주택', 'direction': '남동향',
        'use': '주택', 'approval': '1983.7.18.',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 대방동 13번지 일대',
    },
    '8': {
        'b_area': '철거완료', 'status': '철거 완료',
        'l_area': '68m²', 'floor': '철거완료',
        'rooms': '철거완료', 'fee': '없음',
        'b_type': '철거완료', 'direction': '서향',
        'use': '철거완료', 'approval': '철거완료',
        'move_in': '입주불가', 'parking': '불가능',
        'addr_main': '소재지 : 동작구 대방동 23번지 일대',
    }
}

# =============================================================================
# [2] 이미지 생성 로직 (위로 5px 보정하여 시각적 중앙 정렬)
# =============================================================================
def create_image_final(data):
    try:
        # --- 1. 캔버스 설정 (와이드 1500) ---
        width, height = 1500, 800 
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # --- 2. 색상 정의 ---
        BG_LABEL = "#E7E6E6"    
        BG_DATA = "#FFFFFF"     
        BG_FOOTER = "#000000"   
        
        TEXT_BLACK = "#000000"
        TEXT_RED = "#FF0000"
        TEXT_YELLOW = "#FFFF00"
        
        BORDER_COLOR = "#000000"

        # --- 3. 폰트 설정 ---
        def load_font(font_name, size):
            try: return ImageFont.truetype(font_name, size)
            except IOError:
                try:
                    fallback_path = os.path.join(os.path.expanduser("~"), "Desktop", "그램 공유", font_name)
                    return ImageFont.truetype(fallback_path, size)
                except IOError:
                    import sys
                    mac_font = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
                    try: return ImageFont.truetype(mac_font, size) if sys.platform == "darwin" else ImageFont.load_default()
                    except: return ImageFont.load_default()

        f_label = load_font("malgunbd.ttf", 28)
        f_val = load_font("malgun.ttf", 28)
        f_addr = load_font("malgunbd.ttf", 28)
        f_footer = load_font("malgunbd.ttf", 42)

        # --- 4. 레이아웃 치수 ---
        margin_x = 50
        margin_y = 50
        
        table_width = width - (margin_x * 2)
        
        # 열 너비 비율: 20% | 30% | 20% | 30%
        w_label = table_width * 0.2
        w_data = table_width * 0.3
        
        cols_x = [
            margin_x,
            margin_x + w_label,
            margin_x + w_label + w_data,
            margin_x + w_label + w_data + w_label,
            margin_x + table_width
        ]

        # 행 높이 계산
        footer_h = 110
        remain_h = (height - (margin_y * 2)) - footer_h
        row_h = remain_h / 7 
        
        curr_y = margin_y

        # =========================================================================
        # [A] 1~6행: 데이터 영역
        # =========================================================================
        grid_map = [
            ("건물 면적", "b_area", "추진현황", "status"),
            ("대지 지분", "l_area", "총층 / 해당층", "floor"),
            ("방수 / 욕실수", "rooms", "월 관리비", "fee"),
            ("건물 종류", "b_type", "방향", "direction"),
            ("건축물 용도", "use", "사용승인일", "approval"),
            ("입주 가능일", "move_in", "주차대수", "parking")
        ]

        for l1, k1, l2, k2 in grid_map:
            v1 = data.get(k1, "-")
            v2 = data.get(k2, "-")
            
            cells = [
                (l1, "label", cols_x[0], cols_x[1]),
                (v1, "value", cols_x[1], cols_x[2]),
                (l2, "label", cols_x[2], cols_x[3]),
                (v2, "value", cols_x[3], cols_x[4])
            ]
            
            for text, c_type, x1, x2 in cells:
                bg = BG_LABEL if c_type == "label" else BG_DATA
                font = f_label if c_type == "label" else f_val
                
                # 셀 그리기
                draw.rectangle([(x1, curr_y), (x2, curr_y + row_h)], fill=bg, outline=BORDER_COLOR, width=1)
                
                # ★ 텍스트 그리기 (위로 5px 이동)
                draw_text_visual_center(draw, text, font, TEXT_BLACK, x1, curr_y, x2 - x1, row_h)
            
            curr_y += row_h

        # =========================================================================
        # [B] 7행: 위치 정보
        # =========================================================================
        draw.rectangle([(cols_x[0], curr_y), (cols_x[4], curr_y + row_h)], fill=BG_DATA, outline=BORDER_COLOR, width=1)
        
        addr_main = data.get('addr_main', '')
        addr_warn = " ( 자세한 주소는 매도자가 공개 원치 않음 )"
        
        w1 = get_text_width(draw, addr_main, f_addr)
        w2 = get_text_width(draw, addr_warn, f_addr)
        total_w = w1 + w2
        
        start_x = cols_x[0] + (table_width - total_w) / 2
        text_h = get_text_height(draw, addr_main, f_addr)
        
        # 주소도 위로 5px 이동 (-5)
        start_y = curr_y + (row_h - text_h) / 2 - 5
        
        draw.text((start_x, start_y), addr_main, font=f_addr, fill=TEXT_BLACK)
        draw.text((start_x + w1, start_y), addr_warn, font=f_addr, fill=TEXT_RED)
        
        curr_y += row_h

        # =========================================================================
        # [C] 8행: 푸터
        # =========================================================================
        footer_y = curr_y
        draw.rectangle([(0, footer_y), (width, height)], fill=BG_FOOTER)
        
        left_text = "재개발 전문 PRO부동산"
        right_text = "02-715-0999"
        
        actual_footer_h = height - footer_y
        text_h_f = get_text_height(draw, left_text, f_footer)
        
        # 푸터 텍스트도 위로 5px 이동
        ft_y = footer_y + (actual_footer_h - text_h_f) / 2 - 5
        
        # 간격 설정
        w_l = get_text_width(draw, left_text, f_footer)
        w_r = get_text_width(draw, right_text, f_footer)
        gap = 60
        
        total_content_width = w_l + gap + w_r
        start_x = (width - total_content_width) / 2
        
        draw.text((start_x, ft_y), left_text, font=f_footer, fill=TEXT_YELLOW)
        draw.text((start_x + w_l + gap, ft_y), right_text, font=f_footer, fill=TEXT_YELLOW)

        return image

    except Exception as e:
        messagebox.showerror("에러", f"이미지 생성 중 오류:\n{e}")
        return None

# --- 유틸리티: 시각적 중앙 정렬 (위로 5px) ---
def draw_text_visual_center(draw, text, font, color, x, y, w, h):
    text_w = get_text_width(draw, text, font)
    text_h = get_text_height(draw, text, font)
    
    # 가로: 수학적 정중앙
    pos_x = x + (w - text_w) / 2
    # 세로: 수학적 정중앙 - 5px (위로 올림)
    pos_y = y + (h - text_h) / 2 - 5
    
    draw.text((pos_x, pos_y), text, font=font, fill=color)

def get_text_width(draw, text, font):
    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    else:
        return draw.textsize(text, font=font)[0]

def get_text_height(draw, text, font):
    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[3] - bbox[1]
    else:
        return draw.textsize(text, font=font)[1]

# =============================================================================
# [3] GUI 클래스
# =============================================================================
import json

DATA_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "카페올리기", "last_adress_data.json")

def load_last_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

def save_last_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

class RealEstateTableGen:
    def __init__(self, root):
        self.root = root
        self.root.title("매물장 생성기 (글자위치 보정완료)")
        self.root.geometry("1000x700")
        
        # [macOS 포커스 버그 해결] 창을 강제로 맨 앞으로 끌어오기
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # 시스템 이벤트를 통해 현재 프로세스를 강제로 활성화 (Dock 아이콘 클릭 효과)
        import os
        os.system(f'''/usr/bin/osascript -e 'tell app "System Events" to set frontmost of the first process whose unix id is {os.getpid()} to true' ''')
        
        self.init_ui()
        
    def init_ui(self):
        frame_top = tk.Frame(self.root, pady=15, bg="#333333")
        frame_top.pack(fill="x")
        
        tk.Label(frame_top, text="구역 선택:", bg="#333333", fg="white", font=("맑은 고딕", 12, "bold")).pack(side="left", padx=20)
        
        self.zone_var = tk.StringVar(value="1")
        tk.OptionMenu(frame_top, self.zone_var, *[str(i) for i in range(1,9)], command=self.load_data).pack(side="left")
        
        tk.Label(frame_top, text="※ 모든 글자를 위로 살짝 올려 정가운데로 맞춤", bg="#333333", fg="#FFFF00", font=("맑은 고딕", 10)).pack(side="right", padx=20)

        self.frame_inputs = tk.Frame(self.root, padx=20, pady=20)
        self.frame_inputs.pack(expand=True, fill="both")
        
        self.entries = {}
        grid_items = [
            ("건물 면적", "b_area", "추진현황", "status"),
            ("대지 지분", "l_area", "총층 / 해당층", "floor"),
            ("방수 / 욕실수", "rooms", "월 관리비", "fee"),
            ("건물 종류", "b_type", "방향", "direction"),
            ("건축물 용도", "use", "사용승인일", "approval"),
            ("입주 가능일", "move_in", "주차대수", "parking")
        ]
        
        for r, (l1, k1, l2, k2) in enumerate(grid_items):
            tk.Label(self.frame_inputs, text=l1, font=("맑은 고딕", 10, "bold"), bg="#E7E6E6", width=15, relief="solid").grid(row=r, column=0, sticky="e", pady=5, padx=5)
            e1 = tk.Entry(self.frame_inputs, width=25, relief="solid")
            e1.grid(row=r, column=1, padx=5)
            self.entries[k1] = e1
            
            tk.Label(self.frame_inputs, text=l2, font=("맑은 고딕", 10, "bold"), bg="#E7E6E6", width=15, relief="solid").grid(row=r, column=2, sticky="e", pady=5, padx=5)
            e2 = tk.Entry(self.frame_inputs, width=25, relief="solid")
            e2.grid(row=r, column=3, padx=5)
            self.entries[k2] = e2
            
        tk.Label(self.frame_inputs, text="소재지(앞부분)", font=("맑은 고딕", 10, "bold")).grid(row=6, column=0, sticky="e", pady=15)
        e_addr = tk.Entry(self.frame_inputs, width=60)
        e_addr.grid(row=6, column=1, columnspan=3, padx=5, sticky="w")
        self.entries['addr_main'] = e_addr
        
        btn = tk.Button(self.root, text="이미지 생성 (최종)", bg="black", fg="yellow", 
                        font=("맑은 고딕", 14, "bold"), height=2, command=self.generate)
        btn.pack(fill="x", padx=20, pady=20)
        
        last_data = load_last_data()
        if last_data:
            self.zone_var.set(last_data.get('dist', '1'))
            for k, val in last_data.items():
                if k in self.entries:
                    self.entries[k].delete(0, tk.END)
                    self.entries[k].insert(0, val)
        else:
            self.load_data("1")

    def load_data(self, zone):
        data = ZONES_ADDR.get(zone, {})
        for k, e in self.entries.items():
            e.delete(0, tk.END)
            e.insert(0, data.get(k, ""))

    def generate(self):
        data = {k: e.get() for k, e in self.entries.items()}
        data['dist'] = self.zone_var.get()
        save_last_data(data)
        
        img = create_image_final(data)
        if img:
            fname = f"매물상세_위치보정완료_노량진{data['dist']}구역.png"
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            path = os.path.join(desktop, fname)
            img.save(path)
            messagebox.showinfo("성공", f"이미지가 생성되었습니다!\n저장위치: {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RealEstateTableGen(root)
    root.mainloop()