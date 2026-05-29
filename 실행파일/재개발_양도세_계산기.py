import os
import webbrowser

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, '재개발_양도세_계산기.html')
    
    if os.path.exists(html_path):
        print(f"[{html_path}] 파일을 기본 브라우저에서 엽니다...")
        webbrowser.open('file://' + html_path)
    else:
        print(f"오류: '{html_path}' 파일을 찾을 수 없습니다.")
        print("파이썬 파일과 동일한 폴더에 '재개발_양도세_계산기.html' 파일이 있어야 합니다.")
        input("엔터를 누르면 종료됩니다...")

if __name__ == '__main__':
    main()
