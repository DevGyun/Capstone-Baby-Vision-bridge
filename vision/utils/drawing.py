"""
OpenCV 시각화 유틸리티
- 바운딩 박스, 위험 구역, 경고 배너 그리기
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple


# 색상 정의 (BGR)
COLOR_ADULT = (0, 255, 0)      # 초록 - 성인
COLOR_BABY = (0, 165, 255)     # 주황 - 유아
COLOR_DANGER = (0, 0, 255)     # 빨강 - 위험
COLOR_ZONE = (255, 255, 0)     # 노랑 - 구역 경계


def draw_detections(frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """
    탐지된 객체의 바운딩 박스를 프레임에 그린다.

    Args:
        frame: 원본 프레임
        detections: detector.detect()의 반환값
    """
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        label = det["class_name"]
        conf = det["confidence"]

        color = COLOR_BABY if label == "baby" else COLOR_ADULT
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        text = f"{label} {conf:.2f}"
        cv2.putText(frame, text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return frame


def draw_zones(
    frame: np.ndarray,
    zones: List[Dict],
    frame_width: int,
    frame_height: int,
) -> np.ndarray:
    """
    위험 구역 다각형을 프레임에 반투명으로 그린다.

    Args:
        frame: 원본 프레임
        zones: [{"name": str, "points": [[nx, ny], ...]}, ...]
        frame_width: 프레임 가로 크기
        frame_height: 프레임 세로 크기
    """
    overlay = frame.copy()

    for zone in zones:
        # 정규화 좌표 → 픽셀 좌표
        pts = np.array([
            [int(p[0] * frame_width), int(p[1] * frame_height)]
            for p in zone["points"]
        ], dtype=np.int32)

        cv2.fillPoly(overlay, [pts], (0, 0, 255, 50))
        cv2.polylines(frame, [pts], True, COLOR_ZONE, 2)

        # 구역 이름 표시
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(frame, zone["name"], (cx - 20, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_ZONE, 2)

    # 반투명 오버레이 합성
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

    return frame


def draw_warning_banner(frame: np.ndarray, message: str) -> np.ndarray:
    """
    화면 상단에 빨간 경고 배너를 표시한다.

    Args:
        frame: 원본 프레임
        message: 경고 메시지 (예: "⚠ 유아가 주방에 진입!")
    """
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 50), COLOR_DANGER, -1)
    cv2.putText(frame, message, (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    return frame
