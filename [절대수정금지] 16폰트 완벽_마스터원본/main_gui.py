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
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QTextBrowser, QSplitter, QSizePolicy, QMessageBox, QFileDialog, QComboBox, QScrollArea, QDialog, QGroupBox, QGridLayout)

# [SKILL_SYSTEM 4] 작업 폴더 자동 생성
os.makedirs(os.path.join(os.path.expanduser("~"), "Desktop", "완전자동화", "최종_쇼츠영상"), exist_ok=True)
os.makedirs(os.path.join(os.path.expanduser("~"), "Desktop", "완전자동화", "임시_작업파일"), exist_ok=True)

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from PIL import Image, ImageDraw, ImageFont

# Mac 절대경로 실행 바이너리 상수 (ai_brain 모듈과 동기화)
MCP_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp"
AUTH_EXEC = "/opt/homebrew/Caskroom/miniforge/base/bin/notebooklm-mcp-auth"


from ai_brain import AIPlannerThread, SimpleMCPClient
from naver_bot import NaverAutoBlogWorker
from image_factory import make_property_image

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

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

class ManualPurgeThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def run(self):
        import asyncio
        asyncio.run(self.async_run())

    async def async_run(self):
        self.log_signal.emit("\n🔥 [수동 소각 시스템 가동] 영구 노트북 소스 청소를 시작합니다...")
        client = SimpleMCPClient(MCP_EXEC)
        try:
            await client.start()
            NOTEBOOK_ID = "622ca8d0-38a2-4052-ab57-c64102fa6788"
            
            # 소스 리스트 가져오기
            res = await client.call_tool("notebook_get", {"notebook_id": NOTEBOOK_ID})
            import json, time
            data = json.loads(res) if isinstance(res, str) else res
            
            notebook = data.get("notebook", [])
            if not notebook or len(notebook) == 0:
                self.log_signal.emit("✅ 소스 목록이 비어있습니다. 청소 완료!")
                return
                
            sources_raw = notebook[0][1]
            targets = []
            keeps = []
            
            for src in sources_raw:
                try:
                    s_id = src[0][0]
                    s_title = src[1]
                    
                    if any(keyword in s_title for keyword in ["법전", "마스터", "rule", "pro_fact_book", "팩트"]):
                        keeps.append(s_title)
                    else:
                        targets.append((s_id, s_title))
                except:
                    pass
                    
            if not targets:
                self.log_signal.emit(f"✅ 삭제할 쓰레기 소스가 없습니다! (보존 소스: {len(keeps)}개 유지)")
                return
                
            self.log_signal.emit(f"🚀 총 {len(targets)}개의 쓰레기 소스를 소각합니다... (VVIP 자산 {len(keeps)}개 보존)")
            
            for i, target in enumerate(targets):
                s_id, s_title = target
                # 제목 축약
                short_title = s_title[:40] + ("..." if len(s_title) > 40 else "")
                self.log_signal.emit(f"🗑️ 쓰레기 소각 중... ({i+1}/{len(targets)}) - {short_title}")
                try:
                    await client.call_tool("source_delete", {
                        "source_id": s_id,
                        "confirm": True
                    })
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 소각 실패 ({short_title}): {e}")
                
                await asyncio.sleep(1.0)
                
            self.log_signal.emit("\n🌟 [청소 완료] 묵은 쓰레기 대청소가 완벽하게 끝났습니다!")
            
        except Exception as e:
            self.log_signal.emit(f"❌ 소각 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client.proc and client.proc.returncode is None:
                client.proc.terminate()
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
        b0.clicked.connect(self.open_thumbnail_maker)
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
        
        self.purge_btn = QPushButton("🗑️ 묵은 쓰레기 대청소")
        self.purge_btn.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        self.purge_btn.setFixedSize(140, 75)
        self.purge_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 12px; } QPushButton:hover { background-color: #c0392b; }")
        self.purge_btn.clicked.connect(self.start_manual_purge)
        
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.post_btn)
        btn_layout.addWidget(self.auth_btn)
        btn_layout.addWidget(self.purge_btn)
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
            # [뉴스 수집 제한 해제] when:7d 옵션 삭제 (10개 정상 수집 복구)
            # [뉴스 10개 강제 확보] 구글 RSS 쿼리 최적화: 띄어쓰기 버전 병렬 시도
            base_query = urllib.parse.quote(news_query)
            spaced_query = urllib.parse.quote(news_query.replace('구역', ' 구역 ').strip())
            url = f"https://news.google.com/rss/search?q={spaced_query}&hl=ko&gl=KR&ceid=KR:ko"
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
                
            # [FALLBACK] 구글 RSS 결과가 5개 미만이면 네이버 뉴스 스크래핑으로 보충
            if count < 5:
                try:
                    from bs4 import BeautifulSoup
                    naver_url = f"https://search.naver.com/search.naver?where=news&query={base_query}&sort=1"
                    naver_res = requests.get(naver_url, headers=headers, timeout=5)
                    naver_soup = BeautifulSoup(naver_res.text, 'html.parser')
                    naver_items = naver_soup.select("a.news_tit")
                    for ni in naver_items:
                        if count >= 10:
                            break
                        n_title = ni.text.strip()
                        n_link = ni.get("href", "")
                        if n_title and n_title not in [self.combo_news.itemText(j) for j in range(self.combo_news.count())]:
                            self.combo_news.addItem(f"[{count+1}] {n_title}")
                            self.news_linksList.append(n_link)
                            count += 1
                except Exception as ne:
                    pass  # fallback 실패 시 무시
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

    def open_thumbnail_maker(self):
        """정방형 썸네일 생성기 (카페올리기/thumbnail_maker.py) 실행 — PPT/법제처 코드 없음."""
        thumb_path = os.path.join(os.path.expanduser("~"), "Desktop", "카페올리기", "thumbnail_maker.py")
        if not os.path.exists(thumb_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "파일 없음",
                f"썸네일 생성기를 찾을 수 없습니다.\n경로: {thumb_path}\n\n카페올리기 폴더를 확인해주세요.")
            return
        try:
            # [맥OS Tkinter AbortTrap 방지] miniforge 환경변수 제거 후 시스템 Python 사용
            import subprocess
            clean_env = os.environ.copy()
            for key in ["CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CONDA_EXE",
                        "CONDA_PYTHON_EXE", "VIRTUAL_ENV"]:
                clean_env.pop(key, None)
            # PATH에서 miniforge/conda 경로 제거
            path_parts = clean_env.get("PATH", "").split(":")
            clean_path = ":".join([p for p in path_parts if "miniforge" not in p and "conda" not in p])
            clean_env["PATH"] = clean_path
            # 시스템 Python3으로 실행
            subprocess.Popen(
                ["/usr/bin/python3", thumb_path],
                env=clean_env,
                cwd=os.path.dirname(thumb_path)
            )
            self.log_display.append("🖼️ 썸네일 생성기(정방형)를 실행했습니다. — 별도 창을 확인하세요!")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "실행 오류", f"썸네일 생성기 실행 실패:\n{e}")

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
        scripts = ["info_1~8maker.py", "property_maker_final_v61.py", "adress.py"]
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

        # [대장님 영구 지시] 법제처 PPT 이미지(law_slide_*.png) 포스팅 주입 로직 완전 제거

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
            # [복원] 정방형 썸네일 생성기 — 카페올리기/thumbnail_maker.py (PPT/법제처 코드 없음)
            'thumb': os.path.join(desktop_dir, '카페올리기', 'thumbnail_maker.py'),
            'prop': os.path.join(desktop_dir, '카페올리기', 'property_maker_final_v61.py'),
            'addr': os.path.join(desktop_dir, '카페올리기', 'adress.py'), 
            'zone': os.path.join(desktop_dir, '카페올리기', 'info_1~8maker.py')
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

    def start_manual_purge(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "수동 대청소", "정말로 묵은 쓰레기 소스를 싹 밀어버리시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.purge_btn.setEnabled(False)
            self.purge_thread = ManualPurgeThread()
            self.purge_thread.log_signal.connect(self.append_log)
            self.purge_thread.finished_signal.connect(self.on_purge_finished)
            self.purge_thread.start()

    def on_purge_finished(self):
        self.purge_btn.setEnabled(True)

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = ProRealEstateAIPlanner()
    window.show()
    sys.exit(app.exec())
