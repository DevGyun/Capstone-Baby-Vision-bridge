"""
YOLO 기반 객체 탐지 모듈
- 유아(baby)와 성인(adult)을 실시간으로 구분
"""

from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Tuple


class PersonDetector:
    """YOLO 모델로 사람을 탐지하고 유아/성인을 분류하는 클래스"""

    def __init__(self, model_path: str = "weights/best.pt", confidence: float = 0.5):
        """
        모델 로드 및 초기화

        Args:
            model_path: 학습된 YOLO 모델 파일 경로
            confidence: 최소 신뢰도 임계값
        """
        self.model = YOLO(model_path)
        self.confidence = confidence
        # 학습 데이터의 클래스 매핑 (학습 후 수정 필요)
        self.class_names = {0: "adult", 1: "baby"}

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        한 프레임에서 사람을 탐지한다.

        Args:
            frame: OpenCV BGR 이미지

        Returns:
            탐지 결과 리스트:
            [{"class_name": str, "confidence": float, "bbox": (x1,y1,x2,y2), "center": (cx,cy)}]
        """
        results = self.model(frame, conf=self.confidence, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # 바운딩 박스 하단 중심 (발 위치 추정)
                center_x = (x1 + x2) // 2
                center_y = y2

                detections.append({
                    "class_name": self.class_names.get(class_id, "unknown"),
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                    "center": (center_x, center_y),
                })

        return detections
