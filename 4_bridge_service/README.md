# 4_bridge_service

카메라 영상을 MediaMTX RTSP 서버로 전송하는 브릿지 서비스

## 역할

```
📹 카메라 (웹캠/IP캠/라즈베리파이)
  ↓ OpenCV
🌉 Bridge Service (이 폴더)
  ↓ FFmpeg
📡 MediaMTX (RTSP 서버)
  ├─→ 📱 앱 (스트림 시청)
  └─→ 🧠 AI (객체 탐지)
```

## 빠른 시작

### 1. 로컬 테스트 (Docker 없이)

```bash
# FFmpeg 설치
sudo apt-get install ffmpeg

# Python 패키지 설치
pip install -r requirements.txt

# MediaMTX 실행 (별도 터미널)
docker run -p 8554:8554 bluenviron/mediamtx

# Bridge 실행
python main.py
```

### 2. Docker로 실행

```bash
# docker-compose.yml에 이미 포함되어 있음
docker compose up bridge
```

## 설정 변경

### `config.py` 수정

```python
# 노트북 웹캠
CAMERA_SOURCE = 0

# IP 홈캠
CAMERA_SOURCE = "rtsp://192.168.0.10:554/stream"

# 라즈베리파이 (동일)
CAMERA_SOURCE = 0
```

**제출본 전환은 이 파일 1줄만 바꾸면 끝!**

## 스트림 확인 방법

### VLC로 테스트

```bash
vlc rtsp://localhost:8554/camera1
```

### FFplay로 테스트

```bash
ffplay rtsp://localhost:8554/camera1
```

## 트러블슈팅

### 카메라를 못 찾을 때

```python
# config.py에서 다른 번호 시도
CAMERA_SOURCE = 0  # 안 되면 1, 2 시도
```

### FFmpeg 에러

```bash
# FFmpeg 설치 확인
ffmpeg -version

# 없으면 설치
sudo apt-get install ffmpeg
```

### MediaMTX 연결 실패

```bash
# MediaMTX 실행 확인
docker ps | grep mediamtx

# 없으면 실행
docker compose up mediamtx
```

## 성능 튜닝

### 고화질 (네트워크 좋을 때)

```python
# config.py
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TARGET_FPS = 30
```

### 저화질 (네트워크 안 좋을 때)

```python
# config.py
TARGET_WIDTH = 320
TARGET_HEIGHT = 240
TARGET_FPS = 15
```

## 라즈베리파이 설정

### 웹캠 연결 확인

```bash
ls /dev/video*
# /dev/video0 나오면 OK
```

### 권한 설정

```bash
sudo usermod -a -G video $USER
```

### 실행

```bash
# config.py 설정은 동일
python main.py
```

## 주의사항

- **FFmpeg 필수**: 시스템에 FFmpeg 설치 필요
- **카메라 독점**: 한 번에 하나의 프로그램만 카메라 사용 가능
- **MediaMTX 먼저**: Bridge 실행 전에 MediaMTX가 실행 중이어야 함
