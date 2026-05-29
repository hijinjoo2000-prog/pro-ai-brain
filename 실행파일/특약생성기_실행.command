#!/bin/bash
cd "/Users/seopro/연구자동화 에이전트들/계약서,확인설명서 자동생성기"

# 파이썬 실행 (python3 우선, 없으면 python)
if command -v python3 &> /dev/null
then
    python3 PRO부동산_재개발특약생성기.py
else
    python PRO부동산_재개발특약생성기.py
fi
