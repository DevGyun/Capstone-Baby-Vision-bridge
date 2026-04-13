"""
Bridge Service 설정 파일
카메라 소스를 바꾸는 것만으로 노트북/라즈베리파이/IP캠 전환 가능
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ===== 카메라 소스 설정 =====
CAMERA_SOURCE = 0  # 웹캠

# ===== RTSP 출력 설정 =====
# ✅ 같은 컴퓨터의 MediaMTX로 전송
RTSP_OUTPUT_URL = os.getenv(
    "RTSP_OUTPUT_URL",
    "rtsp://211.243.47.179:8554/2a26fb0a-715e-4e2e-8072-ada50e64929f"
)
# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30