"""
위험 구역 침범 판별 모듈
- Shapely 라이브러리로 다각형 내 좌표 포함 여부 계산
"""

from shapely.geometry import Point, Polygon
from typing import List, Dict, Tuple


class DangerZone:
    """하나의 위험 구역을 표현하는 클래스"""

    def __init__(self, zone_id: str, name: str, points: List[List[float]]):
        """
        Args:
            zone_id: 구역 고유 ID
            name: 구역 이름 (예: "주방")
            points: 정규화 좌표 리스트 [[x, y], ...] (0.0~1.0)
        """
        self.zone_id = zone_id
        self.name = name
        self.points = points
        self.polygon = Polygon(points)

    def contains(self, x: float, y: float) -> bool:
        """
        주어진 좌표가 이 구역 안에 있는지 확인한다.

        Args:
            x: 정규화된 x 좌표
            y: 정규화된 y 좌표
        """
        return self.polygon.contains(Point(x, y))


class ZoneManager:
    """여러 위험 구역을 관리하는 매니저 클래스"""

    def __init__(self):
        self.zones: Dict[str, DangerZone] = {}

    def load_zones(self, zone_list: List[Dict]):
        """
        서버에서 받은 구역 목록을 로드한다.

        Args:
            zone_list: [{"zone_id": str, "name": str, "points": [[x,y], ...]}, ...]
        """
        self.zones.clear()
        for z in zone_list:
            zone = DangerZone(
                zone_id=z["zone_id"],
                name=z["name"],
                points=z["points"],
            )
            self.zones[zone.zone_id] = zone

    def check_intrusion(
        self, center_x: int, center_y: int, frame_width: int, frame_height: int
    ) -> List[DangerZone]:
        """
        탐지된 객체의 중심점이 어떤 위험 구역에 들어갔는지 확인한다.

        Args:
            center_x: 객체 중심 x (픽셀)
            center_y: 객체 중심 y (픽셀)
            frame_width: 프레임 가로 크기
            frame_height: 프레임 세로 크기

        Returns:
            침범한 구역 리스트
        """
        # 픽셀 좌표 → 정규화 좌표 변환
        norm_x = center_x / frame_width
        norm_y = center_y / frame_height

        intruded = []
        for zone in self.zones.values():
            if zone.contains(norm_x, norm_y):
                intruded.append(zone)

        return intruded
