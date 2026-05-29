#!/bin/bash

# 실행 위치를 현재 스크립트가 있는 폴더로 변경
cd "$(dirname "$0")"

# 파이썬 스크립트 실행
/opt/homebrew/bin/python3 "지분교환_계산기.py"
