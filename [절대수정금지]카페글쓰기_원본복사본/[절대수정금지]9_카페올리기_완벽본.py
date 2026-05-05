import sys
import os
import time
import glob
import json
import pyperclip
import subprocess
import shutil
import tempfile

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QTextEdit, 
                               QGroupBox, QMessageBox, QProgressBar, QComboBox, QFileDialog, QDialog)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QPixmap

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

# =========================================================
# [설정] 고정 정보
# =========================================================
NAVER_ID = "jjh8818" 
NAVER_PW = "pro7150999!" # 🔥 보안을 위해 비밀번호를 다시 입력해 주세요!
CAFE_WRITE_URL = "https://cafe.naver.com/ca-fe/cafes/31071493/menus/71/articles/write?boardType=I"
SAVE_FILE = "cafe_last_session.json"

# =========================================================
# [작업자] 카페 포스팅 로봇
# =========================================================
class CafeWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()

    def __init__(self, paths, info):
        super().__init__()
        self.paths = paths
        self.info = info

    def run(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver import ActionChains

        # 업로드 순서: 썸네일 -> 매물 -> 주소 -> 구역 -> 명함 -> 배너
        ordered_keys = ['thumb', 'prop', 'addr', 'zone', 'card', 'banner']
        upload_list = [self.paths[k] for k in ordered_keys if self.paths.get(k) and os.path.exists(self.paths[k])]

        if not upload_list:
            self.log_signal.emit("❌ 업로드할 파일이 없습니다.")
            self.finished_signal.emit()
            return

        temp_files_to_delete = [] # 🔥 삭제 대기열 보관함

        try:
            self.log_signal.emit("⚙️ 드라이버 초기화 및 프로필 로드 중...")
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            # 봇 탐지 치명적 마커 제거
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1200,900")
            
            # app.py와 동일하게 락파일 데드락 방지 (순수 스텔스 접속) 

            # 강제 User-Agent 주입 (최신 Mac Chrome 기준, app.py 완벽 복제)
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            # 🔥 최신 Chrome 버전에 딱 맞추기 위한 동적 버전 추출
            version_main = 146
            try:
                import subprocess
                version_str = subprocess.check_output(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version']).decode('utf-8')
                version_main = int(version_str.strip().split()[2].split('.')[0])
            except Exception:
                pass

            # undetected_chromedriver를 사용해 chromedriver 핑거프린팅 원천 차단
            driver = uc.Chrome(options=options, version_main=version_main)
            
            # CDP를 통한 navigator.webdriver 완벽 무력화 (이중 방어)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                """
            })
                
            wait = WebDriverWait(driver, 20)

            self.log_signal.emit("🚀 네이버 로그인 (pyperclip 스텔스 우회)...")
            driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)
            
            import random
            cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            
            try:
                for tag, val in [("id", NAVER_ID), ("pw", NAVER_PW)]:
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

            # 🚨 [스마트 비상 대기] 캡챠(봇 탐지) 발생 시 수동 개입 무한 대기 (인간-기계 협업)
            captcha_wait_time = 0
            while True:
                try:
                    current_url = driver.current_url
                    if "nidlogin.login" in current_url:
                        # 화면에 캡챠나 에러 텍스트가 떠있는지 검사
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

            self.log_signal.emit("☕ 카페 글쓰기 진입... (캡챠 무사 통과 완료)")
            driver.get(CAFE_WRITE_URL)
            time.sleep(3)
            
            self.log_signal.emit("🖼️ 카페 에디터 프레임 진입 확인...")
            try:
                # SPA 방식이면 굳이 iframe을 찾지 않아도 됨. 못 찾으면 3초 뒤 패스.
                WebDriverWait(driver, 3).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "cafe_main")))
                self.log_signal.emit("⚙️ 옛날 방식 에디터 프레임 전환 완료.")
            except:
                self.log_signal.emit("⚙️ 최신 SPA 에디터 환경 감지 완료.")

            # ---------------------------------------------------------
            # [박제설정] 팝업취소 -> 모바일보기 전환 -> 폰트 16pt 설정 (JS 강제 실행)
            # ---------------------------------------------------------
            self.log_signal.emit("⚙️ 에디터 초기 설정(팝업취소/모바일/16pt) 적용 중...")
            try:
                driver.execute_script("""
                    // 1. 임시저장 팝업 등 취소
                    let popupBtn = document.querySelector('.se-popup-button-cancel, .button_cancel'); 
                    if(popupBtn) popupBtn.click();
                    
                    // 2. 모바일보기 전환
                    let mobileBtn = document.querySelector('.se-device-mobile, .se-document-device-mobile');
                    if(mobileBtn) mobileBtn.click();
                    
                    // 3. 폰트 16pt 강제 세팅
                    let fontSizeBtn = document.querySelector('.se-toolbar-button-font-size');
                    if(fontSizeBtn) {
                        fontSizeBtn.click();
                        setTimeout(() => {
                            let size16 = document.querySelector('button[data-value="16"]');
                            if(size16) size16.click();
                        }, 500);
                    }
                """)
                # 팝업 취소/모바일 보기 세팅이 끝난 후 최소 time.sleep(3) 대기
                time.sleep(3)
            except Exception as e:
                self.log_signal.emit(f"⚠️ 에디터 설정 일부 실패 (진행은 계속됩니다): {e}")

            # ---------------------------------------------------------
            # [사진업로드] JS File Input 강제 주입 방식 (창 멈춤/튕김 완벽 우회)
            # ---------------------------------------------------------
            total = len(upload_list)

            for i, path in enumerate(upload_list):
                abs_path = os.path.abspath(path)
                
                # Mac에서 한글 파일명이나 띄어쓰기가 버그를 일으킬 것을 대비해 안전한 영문 temp 경로 생성
                safe_temp_path = os.path.join(tempfile.gettempdir(), f"cafe_temp_{i}.png")
                shutil.copy(abs_path, safe_temp_path)
                temp_files_to_delete.append(safe_temp_path)
                
                self.log_signal.emit(f"📤 업로드 ({i+1}/{total}): {os.path.basename(path)}")
                
                # noneType 오류 및 OS 시스템 창 멈춤(크래시) 현상을 방지하기 위해 
                # button.click() 대신 JS Event dispatch + Hidden input 주입 방식 사용
                photo_btns = driver.find_elements(By.CSS_SELECTOR, "button.se-image-toolbar-button")
                if photo_btns:
                    driver.execute_script("""
                        var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                        arguments[0].dispatchEvent(evt);
                    """, photo_btns[0])
                time.sleep(1.0) # 내부적으로 hidden file input dom 이 완전히 렌더링되게 잠시 대기
                
                # type='file' 인 input을 찾아서 직접 파일 경로 주입 전송 (pyautogui 네이티브 복붙 불필요!)
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if inputs:
                    try:
                        driver.execute_script("arguments[0].style.display = 'block';", inputs[-1])
                        inputs[-1].send_keys(safe_temp_path)
                    except:
                        try:
                            inputs[-1].send_keys(safe_temp_path)
                        except Exception as e:
                            self.log_signal.emit(f"⚠️ 사진 {i+1} 임의 전송 실패: {e}")
                            
                # 사진이 서버에 온전히 다 올라갈 때까지 충분히 대기
                time.sleep(4.0)
                
                self.progress_signal.emit(int(((i+1)/total)*100))
                
            # ---------------------------------------------------------
            # [자동 입력 로직] 카톡 링크와 생성된 해시태그
            # ---------------------------------------------------------
            final_text = f"👇 {self.info['wl_name']} 1:1 상담 ({self.info['wl_phone']}) 👇\n{self.info['kakao']}\n\n{self.info['tags']}"
            pyperclip.copy(final_text)
            
            self.log_signal.emit("🔗 에디터 하단에 링크와 태그를 자동 입력합니다...")
            
            try:
                actions = ActionChains(driver)
                actions.send_keys(Keys.END).perform()
                time.sleep(1)
                actions.send_keys(Keys.ENTER).perform()
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.5)
                
                actions.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
                time.sleep(1)
                
                actions.send_keys(Keys.ENTER).perform()
                
                self.log_signal.emit("✅ 링크 및 태그 자동 입력 완료!")
            except Exception as e:
                self.log_signal.emit(f"⚠️ 자동 입력 실패 (직접 복붙 해주세요): {e}")

            self.log_signal.emit("🎉 사진과 태그 작업이 모두 끝났습니다! 등록 버튼을 누르세요.")

        except Exception as e:
            self.log_signal.emit(f"❌ 오류: {str(e)}")
        finally:
            # 🔥 파이썬이 네이버 서버 통신을 끊기 전에 파일을 지우는 것을 방지!
            for temp_file in temp_files_to_delete:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except: pass
            self.finished_signal.emit()

# =========================================================
# [메인 GUI]
# =========================================================
class ProCafeMaster(QWidget):
    def __init__(self):
        super().__init__()
        self.file_paths = {'prop': '', 'addr': '', 'zone': '', 'card': '', 'banner': ''}
        self.initUI()
        self.load_data()
        self.scan_files() 

    def initUI(self):
        self.setWindowTitle("프로부동산 카페 스마트 시스템")
        self.setGeometry(200, 50, 1100, 620) # 16:9 widescreen layout
        
        font_family = "Apple SD Gothic Neo" if sys.platform == "darwin" else "맑은 고딕"
        self.setStyleSheet(f"""
            QWidget {{ background-color: #ffffff; font-family: '{font_family}'; }}
            QGroupBox {{ font-weight: bold; border: 1px solid #cccccc; border-radius: 5px; margin-top: 10px; padding-top: 15px; }}
            QPushButton {{ font-weight: bold; padding: 5px; border-radius: 3px; }}
            QLineEdit {{ padding: 4px; border: 1px solid #ccc; border-radius: 3px; }}
        """)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("🏭 프로부동산 카페 조립공장"), alignment=Qt.AlignCenter)
        
        content_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # 1. 부품 생산 (Left)
        g1 = QGroupBox("1단계: 부품 생산")
        v1 = QVBoxLayout()
        b0 = QPushButton("0) 썸네일 생성기 (정방형)"); b0.clicked.connect(lambda: self.run_script("thumbnail_maker.py")); b0.setStyleSheet("color: #FF00FF;")
        b1 = QPushButton("1) 구역정보 생성기 (1~8구역)"); b1.clicked.connect(lambda: self.run_script("info_1~8maker.py")); b1.setStyleSheet("color: #0055FF;")
        b2 = QPushButton("2) 매물카드 생성기"); b2.clicked.connect(lambda: self.run_script("property_maker_final_v61.py")); b2.setStyleSheet("color: #009966;")
        b3 = QPushButton("3) 주소카드 생성기"); b3.clicked.connect(lambda: self.run_script("adress.py")); b3.setStyleSheet("color: #FF9900;")
        v1.addWidget(b0); v1.addWidget(b1); v1.addWidget(b2); v1.addWidget(b3); g1.setLayout(v1)
        left_layout.addWidget(g1)

        # 2. 부품 스캔 (Left)
        g_scan = QGroupBox("2단계: 부품 스캔 (이미지 매칭 확인)")
        v_scan = QVBoxLayout()
        self.labels = {}
        self.preview_labels = {}
        file_map = [('thumb', '0. 썸네일'), ('prop', '1. 매물카드'), ('addr', '2. 주소카드'), ('zone', '3. 구역정보'), ('card', '4. 명함'), ('banner', '5. 배너')]

        for key, name in file_map:
            h = QHBoxLayout()
            l_name = QLabel(name); l_name.setFixedWidth(80)
            
            l_preview = ClickableLabel("미리보기")
            l_preview.setFixedSize(60, 40)
            l_preview.setAlignment(Qt.AlignCenter)
            l_preview.setStyleSheet("border: 1px dashed gray; font-size: 10px;")
            l_preview.setCursor(Qt.PointingHandCursor)
            l_preview.clicked.connect(lambda k=key: self.open_preview_image(k))
            self.preview_labels[key] = l_preview
            
            l_file = QLabel("파일 없음"); l_file.setStyleSheet("color: #FF0000;")
            self.labels[key] = l_file
            btn_chg = QPushButton("변경"); btn_chg.setFixedWidth(60); btn_chg.setStyleSheet("background-color: #E0E0E0; color: black; font-size: 11px;")
            btn_chg.clicked.connect(lambda _, k=key: self.manual_select(k))
            h.addWidget(l_name); h.addWidget(l_preview); h.addWidget(l_file); h.addWidget(btn_chg); v_scan.addLayout(h)

        btn_rescan = QPushButton("🔄 이미지 자동 매칭 (다시 찾기)")
        btn_rescan.clicked.connect(self.scan_files)
        v_scan.addWidget(btn_rescan); g_scan.setLayout(v_scan)
        left_layout.addWidget(g_scan)
        
        content_layout.addLayout(left_layout)

        # 3. 정보 기억 및 태그 생성 (Right)
        g_info = QGroupBox("3단계: 정보 기억 및 자동 태그")
        v_info = QVBoxLayout()
        
        h_zone = QHBoxLayout()
        self.combo_zone = QComboBox(); self.combo_zone.addItems([f"{i}구역" for i in range(1, 9)])
        self.edit_keyword = QLineEdit(); self.edit_keyword.setPlaceholderText("메인 키워드 (예: 노량진1구역)")
        self.combo_zone.currentIndexChanged.connect(self.update_keyword_from_zone)
        self.edit_keyword.textChanged.connect(self.update_tags)
        h_zone.addWidget(QLabel("선택 구역:")); h_zone.addWidget(self.combo_zone)
        h_zone.addWidget(QLabel("키워드:")); h_zone.addWidget(self.edit_keyword)
        v_info.addLayout(h_zone)

        self.edit_tags = QLineEdit(); self.edit_tags.setReadOnly(True)
        self.edit_tags.setStyleSheet("background-color: #f4f4f4; color: #0055FF; font-weight: bold;")
        v_info.addWidget(QLabel("🔥 추천 태그 7개 (자동 생성):")); v_info.addWidget(self.edit_tags)

        h_wl = QHBoxLayout()
        self.ent_wl_name = QLineEdit("PRO부동산")
        self.ent_wl_phone = QLineEdit("010-2319-0977")
        self.ent_wl_name.textChanged.connect(self.save_data)
        self.ent_wl_phone.textChanged.connect(self.save_data)
        h_wl.addWidget(QLabel("상호명(화이트라벨):")); h_wl.addWidget(self.ent_wl_name)
        h_wl.addWidget(QLabel("연락처(화이트라벨):")); h_wl.addWidget(self.ent_wl_phone)
        v_info.addLayout(h_wl)

        self.edit_kakao = QLineEdit(); self.edit_kakao.setText("https://open.kakao.com/o/gqNCbvGe")
        self.edit_kakao.textChanged.connect(self.save_data)
        v_info.addWidget(QLabel("💬 카카오톡 링크:")); v_info.addWidget(self.edit_kakao)

        self.edit_memo = QLineEdit(); self.edit_memo.setPlaceholderText("메모 입력...")
        self.edit_memo.textChanged.connect(self.save_data)
        v_info.addWidget(QLabel("📝 메모:")); v_info.addWidget(self.edit_memo)
        
        g_info.setLayout(v_info)
        right_layout.addWidget(g_info)

        # 4. 조립 시작 (Right)
        self.btn_run = QPushButton("🚀 카페 포스팅 가동 (자동화 완료!)")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("background-color: #FF4444; color: white; font-size: 16px; border-radius: 5px;")
        self.btn_run.clicked.connect(self.start_work)
        right_layout.addWidget(self.btn_run)

        self.pbar = QProgressBar()
        right_layout.addWidget(self.pbar)
        
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True); self.log_box.setFixedHeight(200)
        right_layout.addWidget(self.log_box)
        
        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)

    def update_keyword_from_zone(self, index=None):
        zone = self.combo_zone.currentText()
        if zone:
            self.edit_keyword.setText(f"노량진{zone}매물")
            self.update_tags()

    def update_tags(self):
        kw = self.edit_keyword.text().strip()
        if not kw:
            zone = self.combo_zone.currentText()
            kw = f"노량진{zone}매물"
        
        base_kw = kw.replace("매물", "").replace("급매", "").strip()
        
        tags = f"#{base_kw} #{base_kw}매물 #{base_kw}급매 #노량진재개발 #동작구재개발 #재개발투자 #{self.ent_wl_name.text()}"
        self.edit_tags.setText(tags)
        self.save_data()

    # 🔥 블로그 스크립트와 동일한 완벽한 스캔 로직 탑재
    def scan_files(self):
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
                self.labels[key].setText(os.path.basename(found))
                self.labels[key].setStyleSheet("color: #009966; font-weight: bold;")
                
                # 미리보기 업데이트
                pixmap = QPixmap(found)
                scaled_pix = pixmap.scaled(self.preview_labels[key].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_labels[key].setPixmap(scaled_pix)
                self.preview_labels[key].setStyleSheet("border: 1px solid black;")
            else:
                self.file_paths[key] = ""
                self.labels[key].setText("파일 없음")
                self.labels[key].setStyleSheet("color: #FF0000;")
                
                # 미리보기 초기화
                self.preview_labels[key].clear()
                self.preview_labels[key].setText("미리보기")
                self.preview_labels[key].setStyleSheet("border: 1px dashed gray; font-size: 10px;")
        self.log_box.append("✅ [정밀 스캔 완료] 방금 생성한 최신 이미지로 매칭되었습니다.")
                
    def manual_select(self, key):
        f, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "Images (*.png *.jpg)")
        if f:
            self.file_paths[key] = f
            self.labels[key].setText(os.path.basename(f))
            self.labels[key].setStyleSheet("color: #0000FF; font-weight: bold;")
            
            # 미리보기 업데이트
            pixmap = QPixmap(f)
            scaled_pix = pixmap.scaled(self.preview_labels[key].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_labels[key].setPixmap(scaled_pix)
            self.preview_labels[key].setStyleSheet("border: 1px solid black;")

    def open_preview_image(self, key):
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

    def run_script(self, script_name):
        base_dir = "/Users/seopro/Desktop/카페올리기"
        script_path = os.path.join(base_dir, script_name)
        
        if os.path.exists(script_path):
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["python3", script_name], cwd=base_dir)
                else:
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    subprocess.Popen(["python", script_name], cwd=base_dir, creationflags=creationflags)
                self.log_box.append(f"🔨 {script_name} 실행")
            except Exception as e:
                QMessageBox.critical(self, "실행 오류", f"'{script_name}' 실행 중 오류가 발생했습니다:\n{str(e)}")
        else:
            QMessageBox.critical(self, "오류", f"'{script_name}' 파일이 없습니다.\n경로: {script_path}")

    def save_data(self):
        data = {
            "zone": self.combo_zone.currentIndex(), 
            "memo": self.edit_memo.text(),
            "keyword": self.edit_keyword.text(),
            "kakao": self.edit_kakao.text(),
            "wl_name": self.ent_wl_name.text(),
            "wl_phone": self.ent_wl_phone.text()
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f: json.dump(data, f)

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.combo_zone.setCurrentIndex(data.get("zone", 0))
                    self.edit_memo.setText(data.get("memo", ""))
                    self.edit_keyword.setText(data.get("keyword", ""))
                    self.edit_kakao.setText(data.get("kakao", "https://open.kakao.com/o/gqNCbvGe"))
                    self.ent_wl_name.setText(data.get("wl_name", "PRO부동산"))
                    self.ent_wl_phone.setText(data.get("wl_phone", "010-2319-0977"))
            except: pass
        self.update_tags()

    def start_work(self):
        missing = [k for k, v in self.file_paths.items() if not v]
        if missing:
            if QMessageBox.question(self, "파일 누락", "일부 파일이 없습니다. 진행할까요?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return
        self.btn_run.setEnabled(False)
        
        info = {
            "kakao": self.edit_kakao.text(),
            "tags": self.edit_tags.text(),
            "wl_name": self.ent_wl_name.text(),
            "wl_phone": self.ent_wl_phone.text()
        }
        
        self.worker = CafeWorker(self.file_paths, info)
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if sys.platform == "darwin":
        font = QFont("Apple SD Gothic Neo")
        app.setFont(font)
        
    window = ProCafeMaster()
    window.show()
    sys.exit(app.exec())