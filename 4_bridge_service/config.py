"""
Bridge Service 설정 파일
카메라 소스를 바꾸는 것만으로 노트북/라즈베리파이/IP캠 전환 가능
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ===== 카메라 소스 설정 =====
# 제출본 1: 노트북 웹캠
CAMERA_SOURCE = 0

# 제출본 2: 라즈베리파이 웹캠
# CAMERA_SOURCE = 0

# 제출본 3: IP 홈캠 (RTSP)
# CAMERA_SOURCE = "rtsp://192.168.0.100:554/stream"


# ===== RTSP 출력 설정 =====
# 외부 서버 테스트용 (기본값)
RTSP_OUTPUT_URL = os.getenv(
    "RTSP_OUTPUT_URL",
    "rtsp://0.tcp.jp.ngrok.io:16854/2710f574-2d20-4b3f-ba26-eadf0f688c4b"
)

# Docker 내부 제출용으로 바꿀 때는 아래 주석 해제
# RTSP_OUTPUT_URL = os.getenv("RTSP_OUTPUT_URL", "rtsp://mediamtx:8554/camera1")


# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30