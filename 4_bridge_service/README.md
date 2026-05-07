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

## 동작 흐름

```
1. python main.py 실행
   → 서버에 브릿지 자동 등록 (POST /bridges)
   → bridge_state.json에 bridge_id / token 저장

2. 앱에서 '새 카메라 추가' → 이 기기 선택 → 이름 입력
   → 서버가 stream_url 발급

3. 브릿지가 배정 감지 (GET /bridges/{id}/cameras 폴링)
   → 자동으로 FFmpeg 송출 시작
```

> 재실행 시 bridge_state.json이 있으면 재등록 없이 바로 폴링 시작합니다.

## 빠른 시작

```bash
# FFmpeg 설치
sudo apt-get install ffmpeg       # Ubuntu
brew install ffmpeg               # Mac

# Python 패키지 설치
pip install -r requirements.txt

# 서버 주소 설정 (기본값: http://localhost:8000)
export SERVER_URL=http://서버IP:8000   # 원격 서버 사용 시

# 실행
python main.py
```

## 설정 변경

### `config.py`

```python
# 카메라 소스
CAMERA_SOURCE = 0                        # 웹캠 (기본)
CAMERA_SOURCE = "rtsp://192.168.0.10:554/stream"  # IP캠

# 서버 주소 (환경변수로도 설정 가능)
SERVER_URL = "http://localhost:8000"

# 영상 품질
TARGET_WIDTH = 640
TARGET_HEIGHT = 480
TARGET_FPS = 30
```

**제출본 전환은 `CAMERA_SOURCE` 1줄만 바꾸면 끝!**

## 스트림 확인 방법

```bash
# VLC
vlc rtsp://localhost:8554/{uuid}

# FFplay
ffplay rtsp://localhost:8554/{uuid}
```

uuid는 앱에서 카메라 등록 후 서버가 발급한 값입니다.

## 트러블슈팅

### 카메라를 못 찾을 때
```python
# config.py에서 다른 번호 시도
CAMERA_SOURCE = 0  # 안 되면 1, 2 시도
```

### 서버 연결 실패
```bash
# SERVER_URL 확인
export SERVER_URL=http://서버IP:8000
```

### FFmpeg 에러
```bash
ffmpeg -version  # 설치 확인
```

### 브릿지 재등록이 필요할 때
```bash
rm bridge_state.json  # 삭제 후 재실행하면 새로 등록됨
python main.py
```

## 성능 튜닝

```python
# config.py

# 고화질 (네트워크 좋을 때)
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TARGET_FPS = 30

# 저화질 (네트워크 안 좋을 때)
TARGET_WIDTH = 320
TARGET_HEIGHT = 240
TARGET_FPS = 15
```

## 라즈베리파이 설정

```bash
# 웹캠 연결 확인
ls /dev/video*   # /dev/video0 나오면 OK

# 권한 설정
sudo usermod -a -G video $USER

# 실행 (config.py 설정은 동일)
python main.py
```

## 주의사항

- **FFmpeg 필수**: 시스템에 FFmpeg 설치 필요
- **카메라 독점**: 한 번에 하나의 프로그램만 카메라 사용 가능
- **서버 먼저**: Bridge 실행 전에 메인 서버와 MediaMTX가 실행 중이어야 함
- **bridge_state.json**: 자동 생성되는 파일로 삭제 시 재등록됨, `.gitignore`에 포함 권장
