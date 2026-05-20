#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 PRO부동산 AI기획비서 V10 [모듈화 최신판]
#    핵심 모듈: main_gui.py + ai_brain.py + naver_bot.py + image_factory.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# zsh 환경변수 로드
if [ -f ~/.zshrc ]; then
    source ~/.zshrc
fi

# 작업 폴더로 이동
cd "/Users/seopro/Desktop/완전자동화"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 PRO부동산 AI기획비서 V10 [모듈화 최신판]"
echo "   NotebookLM ID: 622ca8d0 연동 버전"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

/opt/homebrew/Caskroom/miniforge/base/bin/python3 "main_gui.py"
