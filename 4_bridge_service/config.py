import os
from dotenv import load_dotenv

load_dotenv()

# 카메라 소스
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
if CAMERA_SOURCE.isdigit():
    CAMERA_SOURCE = int(CAMERA_SOURCE)

# 영상 설정
TARGET_WIDTH = int(os.getenv("TARGET_WIDTH", "640"))
TARGET_HEIGHT = int(os.getenv("TARGET_HEIGHT", "480"))
TARGET_FPS = int(os.getenv("TARGET_FPS", "30"))
FLIP_HORIZONTAL = os.getenv("FLIP_HORIZONTAL", "True").lower() == "true"

# RTSP 출력 URL
RTSP_OUTPUT_URL = os.getenv("RTSP_OUTPUT_URL", "rtsp://localhost:8554/camera1")

print(f"📡 RTSP 출력: {RTSP_OUTPUT_URL}")