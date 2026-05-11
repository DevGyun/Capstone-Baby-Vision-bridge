"""
Bridge Service 설정 파일
"""

import cv2
import subprocess

def detect_camera_source():
    # 1. 라즈베리파이 카메라 모듈 먼저 시도
    try:
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True, timeout=3
        )
        if result.returncode == 0:
            print("✅ 라즈베리파이 카메라 감지")
            return "libcamera"
    except Exception:
        pass

    # 2. 웹캠 (테스트용 fallback)
    for index in range(3):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.release()
            print(f"✅ 웹캠 감지 (테스트 모드): index {index}")
            return index

    print("❌ 카메라를 찾을 수 없습니다.")
    return None

# ===== 카메라 소스 (자동 감지) =====
CAMERA_SOURCE = detect_camera_source()

# ===== 서버 설정 =====
import os
from dotenv import load_dotenv
load_dotenv()
SERVER_URL = os.getenv("SERVER_URL", "http://211.243.47.179:8000")

# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30

# ===== 기타 설정 =====
BRIDGE_STATE_FILE = "bridge_state.json"
POLL_INTERVAL = 5