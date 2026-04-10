"""
로컬 테스트용 Bridge (MediaMTX 없이)
카메라 영상을 화면에 보여주고 파일로 저장
"""

import cv2
import time

CAMERA_SOURCE = 0
OUTPUT_FILE = "test_output.avi"

def main():
    print("=" * 60)
    print("🎥 Bridge 로컬 테스트 (MediaMTX 없이)")
    print("=" * 60)
    
    # 카메라 열기
    print(f"[1] 카메라 연결 중: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    
    if not cap.isOpened():
        print(f"❌ 카메라를 열 수 없습니다.")
        print("해결 방법:")
        print("  - CAMERA_SOURCE를 0, 1, 2로 바꿔보세요")
        return
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    
    print(f"✅ 카메라 연결 성공!")
    print(f"   해상도: {width}x{height}")
    print(f"   FPS: {fps}")
    
    # 영상 저장용 (선택사항)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(OUTPUT_FILE, fourcc, fps, (width, height))
    
    print(f"\n[2] 카메라 화면 표시 중...")
    print(f"   저장 파일: {OUTPUT_FILE}")
    print(f"   종료: 'q' 키")
    print("=" * 60)
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("⚠️ 프레임 읽기 실패")
                break
            
            frame_count += 1
            
            # 정보 표시
            elapsed = time.time() - start_time
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            
            cv2.putText(
                frame,
                f"FPS: {current_fps:.1f} | Frame: {frame_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # 화면에 표시
            cv2.imshow('Bridge Test - Press Q to quit', frame)
            
            # 파일로 저장
            out.write(frame)
            
            # 'q' 키로 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[3] 종료 요청됨")
                break
    
    except KeyboardInterrupt:
        print("\n[3] Ctrl+C로 종료")
    
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        print(f"\n✅ 테스트 완료!")
        print(f"   총 프레임: {frame_count:,}")
        print(f"   저장 위치: {OUTPUT_FILE}")
        print("=" * 60)


if __name__ == "__main__":
    main()
