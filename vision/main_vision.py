"""
EyeCatch AI Vision 메인 실행 스크립트
- 웹캠 영상 읽기 → YOLO 탐지 → 구역 침범 체크 → 브릿지로 이벤트 전송
"""

import cv2
import time
import json
import requests
from models.detector import PersonDetector
from core.zone_checker import ZoneManager
from utils.drawing import draw_detections, draw_zones, draw_warning_banner


# ========== 설정 (환경에 맞게 수정) ==========
CAMERA_SOURCE = 0                                  # 웹캠 번호 (0 = 기본 카메라)
MODEL_PATH = "weights/best.pt"                     # YOLO 모델 경로
BRIDGE_EVENT_URL = "http://localhost:9000/event"   # 브릿지 이벤트 수신 주소
MAIN_SERVER_URL = "http://localhost:8000/api"      # 메인 서버 주소
ALERT_COOLDOWN = 5                                 # 같은 구역 재알림 대기 시간(초)
# =============================================


def fetch_zones_from_server() -> list:
    """메인 서버에서 위험 구역 목록을 가져온다."""
    try:
        response = requests.get(f"{MAIN_SERVER_URL}/zones", timeout=5)
        data = response.json()
        return data.get("zones", [])
    except Exception as e:
        print(f"[경고] 구역 정보 로드 실패: {e}")
        return []


def send_alert_to_bridge(event: dict):
    """브릿지 서비스로 위험 감지 이벤트를 전송한다."""
    try:
        requests.post(BRIDGE_EVENT_URL, json=event, timeout=3)
    except Exception as e:
        print(f"[경고] 브릿지 이벤트 전송 실패: {e}")


def main():
    """메인 루프: 영상 캡처 → 탐지 → 구역 체크 → 알림"""

    # 1. 모델 로드
    print("[시작] YOLO 모델 로딩...")
    detector = PersonDetector(model_path=MODEL_PATH)

    # 2. 위험 구역 로드
    print("[시작] 위험 구역 로딩...")
    zone_manager = ZoneManager()
    raw_zones = fetch_zones_from_server()
    zone_manager.load_zones(raw_zones)
    print(f"[정보] {len(zone_manager.zones)}개 구역 로드 완료")

    # 3. 카메라 열기
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        print("[오류] 카메라를 열 수 없습니다.")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[정보] 카메라 해상도: {frame_width}x{frame_height}")

    # 알림 쿨다운 추적
    last_alert_time = {}
    frame_count = 0

    print("[시작] 실시간 감지 시작... (q 키로 종료)")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # 4. 객체 탐지
        detections = detector.detect(frame)

        # 5. 유아만 필터링 → 구역 침범 체크
        warning_message = None

        for det in detections:
            if det["class_name"] != "baby":
                continue

            cx, cy = det["center"]
            intruded_zones = zone_manager.check_intrusion(
                cx, cy, frame_width, frame_height
            )

            for zone in intruded_zones:
                now = time.time()
                last_time = last_alert_time.get(zone.zone_id, 0)

                if now - last_time > ALERT_COOLDOWN:
                    last_alert_time[zone.zone_id] = now
                    warning_message = f"WARNING: Baby in [{zone.name}]!"

                    # 브릿지로 이벤트 전송
                    event = {
                        "event_type": "ZONE_INTRUSION",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "zone_id": zone.zone_id,
                        "zone_name": zone.name,
                        "detections": [{
                            "class_name": det["class_name"],
                            "confidence": det["confidence"],
                            "bbox": list(det["bbox"]),
                            "center": list(det["center"]),
                        }],
                        "frame_id": frame_count,
                    }
                    send_alert_to_bridge(event)
                    print(f"[알림] {warning_message}")

        # 6. 시각화
        draw_detections(frame, detections)
        if raw_zones:
            draw_zones(frame, raw_zones, frame_width, frame_height)
        if warning_message:
            draw_warning_banner(frame, warning_message)

        cv2.imshow("EyeCatch AI Vision", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[종료] AI Vision 종료")


if __name__ == "__main__":
    main()
