"""
Bridge Service 설정 파일
카메라 소스를 바꾸는 것만으로 노트북/라즈베리파이/IP캠 전환 가능
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ===== 카메라 소스 설정 =====
CAMERA_SOURCE = 0  # 웹캠

# ===== 서버 설정 =====
# 브릿지가 등록/폴링할 메인 서버 주소
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30

# ===== 브릿지 상태 파일 =====
# 최초 등록 후 bridge_id, token을 로컬에 저장해 재실행 시 재사용
BRIDGE_STATE_FILE = "bridge_state.json"

# ===== 폴링 간격 =====
POLL_INTERVAL = 5  # 초