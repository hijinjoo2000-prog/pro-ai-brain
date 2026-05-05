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
