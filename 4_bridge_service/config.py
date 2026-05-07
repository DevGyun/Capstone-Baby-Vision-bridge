"""
Bridge Service 설정 파일
카메라 소스를 바꾸는 것만으로 노트북/라즈베리파이/IP캠 전환 가능
"""

# ===== 카메라 소스 설정 =====
# 제출본 1: 노트북 웹캠
CAMERA_SOURCE = 0

# 제출본 2: 라즈베리파이 웹캠
# CAMERA_SOURCE = 0

# 제출본 3: IP 홈캠 (RTSP)
# CAMERA_SOURCE = "rtsp://192.168.0.100:554/stream"

# 제출본 4: IP 홈캠 (HTTP)
# CAMERA_SOURCE = "http://192.168.0.100:8080/video"


# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30