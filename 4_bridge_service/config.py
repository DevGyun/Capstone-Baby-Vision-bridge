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


# ===== RTSP 출력 설정 =====
# MediaMTX 서버 주소 (docker-compose 환경)
RTSP_OUTPUT_URL = "rtsp://mediamtx:8554/camera1"

# 로컬 테스트용 (docker 없이 실행 시)
# RTSP_OUTPUT_URL = "rtsp://localhost:8554/camera1"


# ===== 영상 품질 설정 =====
TARGET_WIDTH = 640    # 해상도 (너비)
TARGET_HEIGHT = 480   # 해상도 (높이)
TARGET_FPS = 30       # 프레임 레이트

# 고품질 옵션 (네트워크 좋을 때)
# TARGET_WIDTH = 1280
# TARGET_HEIGHT = 720
# TARGET_FPS = 30
