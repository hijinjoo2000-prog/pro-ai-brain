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
import pyautogui
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
            from selenium.webdriver.common.action_chains import ActionChains
            import math
            import sys
            import time
            import pyperclip
            import tempfile
            import shutil
            import os
            import random
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
                    time.sleep(1.5)  # [클립보드 동기화 락] Mac OS 잘림 방지
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

            # ==========================================
            # [Step 1] 모든 방해 팝업(도움말, 임시저장 등) 무자비하게 0.5초 간격으로 파괴
            # ==========================================
            self.log_signal.emit("⚙️ 에디터 초기화 (방해 팝업 파괴 및 모바일 모드 설정 중)...")
            for _ in range(4):
                try:
                    driver.execute_script("""
                        // 1. 작성중인 글 취소/확인 팝업 파괴 ('취소' 버튼 클릭)
                        var allBtns = document.querySelectorAll('button');
                        allBtns.forEach(btn => {
                            if((btn.innerText && btn.innerText.includes('취소')) || (btn.className && btn.className.includes('cancel'))) {
                                btn.click();
                            }
                        });
                        // 2. 도움말 모달 X 버튼 파괴
                        var helpBtns = document.querySelectorAll('button.se-help-panel-close-button');
                        helpBtns.forEach(btn => { btn.click(); });
                        
                        // 3. 혹시 모를 팝업들(.se-popup-button-cancel)
                        var popups = document.querySelectorAll('.se-popup-button-cancel');
                        popups.forEach(btn => { btn.click(); });
                    """)
                except:
                    pass
                time.sleep(0.5)

            # ==========================================
            # [Step 2] 모바일 화면 전환 및 16pt 폰트 강제 적용
            # ==========================================
            self.log_signal.emit("📱 에디터 16pt 세팅 및 폰트 초기화 중...")
            try:
                driver.execute_script("""
                    var mobileBtn = document.querySelector('button.se-util-button-device-mobile') || document.querySelector('button.se-util-button-device-tablet');
                    if(mobileBtn) mobileBtn.click();
                """)
                time.sleep(1.0)
            except:
                pass



            # ==========================================
            # [Step 3] 제목칸 클릭 및 타이핑 (ActionChains)
            # ==========================================
            self.log_signal.emit("✍️ 스마트에디터: 제목칸 클릭 및 타이핑 (ActionChains)...")
            actions = ActionChains(driver)

            try:
                # 완벽하게 제목칸을 강제 포커스 (JS로 scroll & focus 후 Selenium Click)
                target = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.se-documentTitle')))
                driver.execute_script("arguments[0].scrollIntoView(); arguments[0].focus();", target)
                time.sleep(0.5)
                target.click()
                time.sleep(0.5)
            except Exception as e:
                self.log_signal.emit(f"⚠️ 제목칸 클릭 오류 (대체 시도): {e}")

            safe_title = self.title.replace('`', '').replace('"', '\"').replace('\n', ' ')
            pyperclip.copy(safe_title)
            actions.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
            time.sleep(0.8)

            # Enter 눌러서 본문으로 떨어지기
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(1.0)
            
            # 본문에 포커스된 상태에서 "전체 선택(Ctrl+A)" 효과 방지 및 명확한 글씨체 적용
            self.log_signal.emit("🔠 본문 내용 시작 전 16pt 폰트 설정...")
            try:
                driver.execute_script("""
                    var fontBtn = document.querySelector('button[data-name="font-size"]');
                    if(fontBtn) fontBtn.click();
                """)
                time.sleep(0.5)
                driver.execute_script("""
                    var size16Btn = document.querySelector('button[data-value="fs16"]');
                    if(size16Btn) size16Btn.click();
                    else {
                        var btns = document.querySelectorAll('button');
                        for(var i=0; i<btns.length; i++) {
                            if(btns[i].innerText === '16') { btns[i].click(); break; }
                        }
                    }
                """)
                time.sleep(1.0)
            except Exception as e:
                self.log_signal.emit(f"⚠️ 폰트 16pt 설정 실패: {e}")

            # 네이버 스마트에디터의 ~ 취소선 마크다운 자동완성 버그를 회피하기 위해, 
            # CMD+V 후 스페이스바 혹은 여백을 명확히 주도록 본문 삽입 로직 변경
            # 3 & 4. 본문 텍스트와 사진 교차 삽입
            self.log_signal.emit("📤 스마트에디터: 본문 텍스트 & 사진 교차 업로드 진행 중...")
            img_list = [img for img in self.image_list if os.path.exists(img)]
            num_images = len(img_list)

            safe_content = self.content.replace('~', '〜').replace('---', 'ㅡㅡㅡ').replace('---', 'ㅡㅡㅡ').replace('#', '＃').replace('=', '＝')
            paragraphs = [p for p in safe_content.strip().split("\n\n") if p.strip()]

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
                
                # [사진 파트]
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
                                        self.log_signal.emit(f"⚠️ 사진 {i+1} 전송 실패: {e}")

                        self.log_signal.emit(f"⏳ 사진 {i+1}번 렌더링 대기 중... (5초)")
                        time.sleep(5.0)
                        
                        # 사진 업로드 후 엔터
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
