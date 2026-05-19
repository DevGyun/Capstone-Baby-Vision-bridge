"""
EyeCatch Bridge 진입점

흐름:
[최초 실행 - 와이파이 없음]
→ ble_server.py 실행
→ 앱에서 BLE로 와이파이 정보 전송
→ 와이파이 연결
→ main.py 실행

[재실행 - 와이파이 연결됨]
→ 바로 main.py 실행
"""

import subprocess
import sys
import time


def is_wifi_connected() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "STATE", "general"],
            capture_output=True, text=True, timeout=5
        )
        return "connected" in result.stdout
    except Exception:
        return True


def main():
    print("=" * 50)
    print("🎥 EyeCatch Bridge 시작")
    print("=" * 50)

    if is_wifi_connected():
        print("✅ 와이파이 연결됨 → 브릿지 바로 시작")
        import main as bridge
        bridge.main()
    else:
        print("📶 와이파이 미연결 → BLE 셋업 시작")
        import ble_server
        ble_server.main()


if __name__ == "__main__":
    main()