# API 명세서 (프론트엔드 ↔ 메인 서버)

> 프론트엔드와 메인 서버 간 REST API 규격입니다.
> 양쪽 담당자가 이 문서를 기준으로 개발합니다.

---

## Base URL

```
http://<서버IP>:8000/api
```

---

## 1. 위험 구역 관리

### 1-1. 구역 목록 조회
- **GET** `/zones`
- Response:
```json
{
  "zones": [
    {
      "zone_id": "zone_001",
      "name": "주방",
      "points": [[0.1, 0.2], [0.5, 0.2], [0.5, 0.8], [0.1, 0.8]],
      "created_at": "2026-03-31T12:00:00Z"
    }
  ]
}
```
> points는 **정규화 좌표** (0.0~1.0)입니다. 프론트에서 화면 크기에 맞춰 변환하세요.

### 1-2. 구역 생성
- **POST** `/zones`
- Request:
```json
{
  "name": "발코니",
  "points": [[0.6, 0.1], [0.9, 0.1], [0.9, 0.5], [0.6, 0.5]]
}
```

### 1-3. 구역 삭제
- **DELETE** `/zones/{zone_id}`

---

## 2. 알림

### 2-1. 알림 내역 조회
- **GET** `/alerts?limit=20&offset=0`
- Response:
```json
{
  "alerts": [
    {
      "alert_id": "alert_001",
      "zone_name": "주방",
      "detected_at": "2026-03-31T14:30:00Z",
      "confidence": 0.92,
      "thumbnail_url": "/static/captures/alert_001.jpg"
    }
  ],
  "total": 45
}
```

---

## 3. 사용자 / 디바이스

### 3-1. FCM 토큰 등록
- **POST** `/users/fcm-token`
- Request:
```json
{
  "fcm_token": "dKjF83kd..."
}
```

---

## 4. 스트림

### 4-1. 실시간 영상 스트림 URL 조회
- **GET** `/stream/url`
- Response:
```json
{
  "stream_url": "http://<브릿지IP>:9000/live"
}
```

---

> ⚠️ 이 문서는 개발 진행에 따라 수정될 수 있습니다. 변경 시 반드시 팀원에게 공유하세요.
