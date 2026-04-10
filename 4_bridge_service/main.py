"""
EyeCatch Bridge Service
카메라 영상을 MediaMTX로 전송하는 스트리밍 클라이언트
"""

import cv2
import subprocess
import sys
import time
from config import (
    CAMERA_SOURCE,
    RTSP_OUTPUT_URL,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    TARGET_FPS
)


def main():
    """메인 실행 함수"""
    
    print("=" * 60)
    print("🎥 EyeCatch Bridge Service 시작")
    print("=" * 60)
    
    # 1. 카메라 열기
    print(f"[1/4] 카메라 연결 중: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    
    if not cap.isOpened():
        print(f"❌ [오류] 카메라를 열 수 없습니다: {CAMERA_SOURCE}")
        print("\n해결 방법:")
        print("  - 웹캠: CAMERA_SOURCE = 0 (또는 1, 2)")
        print("  - IP캠: CAMERA_SOURCE = 'rtsp://IP주소:포트/경로'")
        sys.exit(1)
    
    # 카메라 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    
    # 실제 적용된 값 확인
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = int(cap.get(cv2.CAP_PROP_FPS)) or TARGET_FPS
    
    print(f"✅ 카메라 연결 성공!")
    print(f"   해상도: {actual_width}x{actual_height}")
    print(f"   FPS: {actual_fps}")
    
    # 2. FFmpeg 명령어 구성
    print(f"\n[2/4] FFmpeg 프로세스 시작 중...")
    print(f"   출력: {RTSP_OUTPUT_URL}")
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',  # 덮어쓰기 허용
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{actual_width}x{actual_height}',
        '-r', str(actual_fps),
        '-i', '-',  # stdin으로 입력받기
        
        # 인코딩 설정 (실시간 최적화)
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-g', str(actual_fps * 2),  # GOP 크기
        '-b:v', '2000k',  # 비트레이트
        
        # RTSP 출력
        '-f', 'rtsp',
        RTSP_OUTPUT_URL
    ]
    
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ FFmpeg 프로세스 시작 완료!")
    except FileNotFoundError:
        print("❌ [오류] FFmpeg를 찾을 수 없습니다.")
        print("\n설치 방법:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  Mac: brew install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
        cap.release()
        sys.exit(1)
    
    # 3. 스트리밍 시작
    print(f"\n[3/4] 스트리밍 시작!")
    print(f"   앱에서 접속: {RTSP_OUTPUT_URL}")
    print(f"   종료: Ctrl+C")
    print("=" * 60)
    
    frame_count = 0
    start_time = time.time()
    error_count = 0
    max_errors = 30  # 연속 30번 실패하면 종료
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                error_count += 1
                print(f"⚠️  [경고] 프레임 읽기 실패 ({error_count}/{max_errors})")
                
                if error_count >= max_errors:
                    print("❌ [오류] 카메라 연결이 끊어졌습니다.")
                    break
                
                time.sleep(0.1)
                continue
            
            # 에러 카운트 리셋
            error_count = 0
            
            # FFmpeg로 프레임 전송
            try:
                ffmpeg_process.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("❌ [오류] FFmpeg 프로세스가 종료되었습니다.")
                break
            
            frame_count += 1
            
            # 10초마다 상태 출력
            if frame_count % (actual_fps * 10) == 0:
                elapsed = time.time() - start_time
                current_fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"📊 [{frame_count:,} 프레임] {current_fps:.1f} FPS")
    
    except KeyboardInterrupt:
        print("\n\n[4/4] 사용자가 종료를 요청했습니다.")
    
    except Exception as e:
        print(f"\n❌ [오류] 예상치 못한 에러: {e}")
    
    finally:
        # 정리 작업
        print("\n정리 중...")
        cap.release()
        
        if ffmpeg_process.stdin:
            ffmpeg_process.stdin.close()
        
        ffmpeg_process.wait(timeout=5)
        
        print("✅ Bridge Service 종료 완료!")
        print("=" * 60)


if __name__ == "__main__":
    main()
