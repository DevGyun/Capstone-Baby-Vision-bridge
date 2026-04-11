import subprocess

rtsp_url = "rtsp://0.tcp.jp.ngrok.io:16854/2710f574-2d20-4b3f-ba26-eadf0f688c4b"

print(f"🔍 RTSP 서버 연결 테스트: {rtsp_url}")
print("=" * 60)

# FFmpeg로 연결만 테스트
cmd = [
    'ffmpeg',
    '-timeout', '5000000',
    '-i', rtsp_url,
    '-t', '1',  # 1초만
    '-f', 'null',
    '-'
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("✅ 서버 연결 성공!")
    else:
        print("❌ 서버 연결 실패!")
        print("\n에러 메시지:")
        print(result.stderr)
        
except subprocess.TimeoutExpired:
    print("❌ 타임아웃! 서버가 응답하지 않습니다.")
except Exception as e:
    print(f"❌ 에러: {e}")