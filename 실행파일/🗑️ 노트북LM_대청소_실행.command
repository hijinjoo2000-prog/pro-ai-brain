#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🗑️ NotebookLM 묵은 쓰레기 대청소 스크립트
#    TARGET: 노트북 622ca8d0 (신규 활성 노트북)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -f ~/.zshrc ]; then
    source ~/.zshrc
fi

cd "/Users/seopro/Desktop/완전자동화"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗑️ NotebookLM 소스 대청소 시작"
echo "   보존: 법전/마스터/rule/팩트 키워드 소스"
echo "   소각: 그 외 모든 일회성 뉴스 소스"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

/opt/homebrew/Caskroom/miniforge/base/bin/python3 "grand_purge.py"

echo ""
echo "✅ 대청소 완료! 창을 닫으셔도 됩니다."
read -p "엔터를 누르면 창이 닫힙니다..."
