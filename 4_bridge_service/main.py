"""
EyeCatch Bridge Service

흐름:
[최초 실행]
1. bridge_id 생성 → GET /bridges/{id}/status 확인
2. 미등록이면 POST /bridges/register → 6자리 페어링 코드 출력
3. 앱에서 코드 입력해서 페어링
4. GET /bridges/{id}/status 폴링 → paired 되면 stream_url 수신
5. FFmpeg 송출 시작

[재실행]
1. bridge_id 로드 → GET /bridges/{id}/status 확인
2. 이미 paired면 → 바로 stream_url 받아서 송출 시작
"""

import cv2
import subprocess
import sys
import time
import json
import os
import uuid
import threading
import requests

from config import (
    CAMERA_SOURCE,
    SERVER_URL,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    TARGET_FPS,
    BRIDGE_STATE_FILE,
    POLL_INTERVAL,
)


# ──────────────────────────────────────────
# STEP 0: bridge_id 로드 or 생성
# ──────────────────────────────────────────

def load_bridge_id() -> str:
    """로컬에 저장된 bridge_id 불러오기. 없으면 새로 생성."""
    if os.path.exists(BRIDGE_STATE_FILE):
        with open(BRIDGE_STATE_FILE, "r") as f:
            state = json.load(f)
            bridge_id = state.get("bridge_id")
            if bridge_id:
                print(f"✅ 기존 브릿지 ID 재사용: {bridge_id}")
                return bridge_id

    bridge_id = str(uuid.uuid4())
    with open(BRIDGE_STATE_FILE, "w") as f:
        json.dump({"bridge_id": bridge_id}, f)
    print(f"✅ 새 브릿지 ID 생성: {bridge_id}")
    return bridge_id


# ──────────────────────────────────────────
# STEP 1: 서버 상태 확인
# ──────────────────────────────────────────

def check_status(bridge_id: str) -> dict | None:
    """
    GET /bridges/{bridge_id}/status
    → {"status": "paired/pending/expired", "stream_url": ...}
    서버에 등록 안 된 경우 None 반환
    """
    try:
        resp = requests.get(
            f"{SERVER_URL}/bridges/{bridge_id}/status",
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None  # 미등록
    except requests.exceptions.ConnectionError:
        pass
    return None


# ──────────────────────────────────────────
# STEP 2: 서버에 등록 → 페어링 코드 발급
# ──────────────────────────────────────────

def register_bridge(bridge_id: str):
    """
    POST /bridges/register
    → pairing_code (6자리) 출력
    """
    print("\n📡 서버에 브릿지 등록 중...")

    while True:
        try:
            resp = requests.post(
                f"{SERVER_URL}/bridges/register",
                json={"bridge_id": bridge_id},
                timeout=5,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                pairing_code = data["pairing_code"]
                expires_at = data.get("expires_at", "")

                print("\n" + "=" * 50)
                print(f"  📱 앱에서 아래 코드를 입력해주세요")
                print(f"")
                print(f"       페어링 코드:  {pairing_code}")
                print(f"")
                print(f"  ⏱  유효시간: 10분  ({expires_at[:19] if expires_at else ''})")
                print("=" * 50 + "\n")
                return

            else:
                print(f"⚠️  등록 실패 (status: {resp.status_code}), {POLL_INTERVAL}초 후 재시도...")
        except requests.exceptions.ConnectionError:
            print(f"⚠️  서버 연결 실패 ({SERVER_URL}), {POLL_INTERVAL}초 후 재시도...")

        time.sleep(POLL_INTERVAL)


# ──────────────────────────────────────────
# STEP 3: 페어링 될 때까지 폴링
# ──────────────────────────────────────────

def wait_for_pairing(bridge_id: str) -> str:
    """
    GET /bridges/{bridge_id}/status 폴링
    paired 되면 stream_url 반환
    expired 되면 재등록 후 다시 대기
    """
    print("⏳ 앱에서 페어링 대기 중...\n")

    while True:
        data = check_status(bridge_id)

        if data:
            status = data.get("status")

            if status == "paired":
                stream_url = data.get("stream_url")
                print(f"✅ 페어링 완료!")
                print(f"   stream_url: {stream_url}")
                return stream_url

            elif status == "expired":
                print("⚠️  페어링 코드가 만료됐어요. 새 코드를 발급합니다...")
                register_bridge(bridge_id)

            # pending이면 그냥 대기

        time.sleep(POLL_INTERVAL)


# ──────────────────────────────────────────
# STEP 4: 카메라 열기
# ──────────────────────────────────────────

def open_camera():
    """카메라 열고 실제 해상도/FPS 반환"""
    print(f"\n[카메라] 연결 중: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)

    if not cap.isOpened():
        print(f"❌ 카메라를 열 수 없습니다: {CAMERA_SOURCE}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = int(cap.get(cv2.CAP_PROP_FPS)) or TARGET_FPS

    print(f"✅ 카메라 연결 성공! ({actual_w}x{actual_h} @ {actual_fps}fps)")
    return cap, actual_w, actual_h, actual_fps


# ──────────────────────────────────────────
# STEP 5: FFmpeg 송출
# ──────────────────────────────────────────

def start_streaming(cap, stream_url: str, width: int, height: int, fps: int):
    """FFmpeg로 MediaMTX에 스트림 송출"""
    print(f"\n[FFmpeg] 송출 시작: {stream_url}")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-g", str(fps * 2),
        "-b:v", "2000k",
        "-rtsp_transport", "tcp",
        "-f", "rtsp",
        stream_url,
    ]

    try:
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("❌ FFmpeg를 찾을 수 없습니다.")
        print("   Ubuntu/라즈베리파이: sudo apt-get install ffmpeg")
        print("   Mac: brew install ffmpeg")
        print("   Windows: https://ffmpeg.org/download.html")
        cap.release()
        sys.exit(1)

    threading.Thread(
        target=lambda: [print(line.decode(), end="") for line in ffmpeg_proc.stderr],
        daemon=True,
    ).start()

    print("⏳ MediaMTX 연결 확인 중...")
    time.sleep(3)
    if ffmpeg_proc.poll() is not None:
        print("❌ MediaMTX 서버에 연결할 수 없습니다.")
        cap.release()
        sys.exit(1)

    print("✅ 송출 시작! (종료: Ctrl+C)")
    print("=" * 50)

    frame_count = 0
    error_count = 0
    max_errors = 30
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                error_count += 1
                print(f"⚠️  프레임 읽기 실패 ({error_count}/{max_errors})")
                if error_count >= max_errors:
                    print("❌ 카메라 연결이 끊어졌습니다.")
                    break
                time.sleep(0.1)
                continue

            error_count = 0

            try:
                ffmpeg_proc.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("❌ FFmpeg 프로세스가 종료되었습니다.")
                break

            frame_count += 1
            if frame_count % (fps * 10) == 0:
                elapsed = time.time() - start_time
                print(f"📊 [{frame_count:,} 프레임] {frame_count/elapsed:.1f} FPS")

    except KeyboardInterrupt:
        print("\n사용자가 종료를 요청했습니다.")

    finally:
        print("\n정리 중...")
        cap.release()
        if ffmpeg_proc.stdin:
            ffmpeg_proc.stdin.close()
        try:
            ffmpeg_proc.wait(timeout=5)
        except Exception:
            ffmpeg_proc.kill()
        print("✅ Bridge Service 종료 완료!")
        print("=" * 50)


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    print("=" * 50)
    print("🎥 EyeCatch Bridge Service 시작")
    print("=" * 50)

    # STEP 0: bridge_id 로드 or 생성
    bridge_id = load_bridge_id()

    # STEP 1: 서버 상태 먼저 확인
    print("\n🔍 서버에서 등록 상태 확인 중...")
    data = check_status(bridge_id)

    if data and data.get("status") == "paired":
        # 이미 페어링된 브릿지 → 바로 송출 시작
        stream_url = data.get("stream_url")
        print(f"✅ 이미 등록된 브릿지입니다. 바로 송출을 시작합니다.")
        print(f"   stream_url: {stream_url}")
    else:
        # 미등록 or pending or expired → 등록 + 페어링 대기
        register_bridge(bridge_id)
        stream_url = wait_for_pairing(bridge_id)

    # STEP 4: 카메라 열기
    cap, width, height, fps = open_camera()

    # STEP 5: 송출 시작
    start_streaming(cap, stream_url, width, height, fps)


if __name__ == "__main__":
    main()