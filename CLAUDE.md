# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Capstone-Baby-Vision** (백엔드 레포)는 실시간 유아 안전 모니터링 시스템의 서버 컴포넌트입니다. YOLO 기반 위험구역 침범 감지, RTSP 스트리밍, FastAPI REST API를 포함합니다.

관련 레포지토리:
- `Capstone-Baby-Vision-Frontend` — Flutter 모바일 앱
- `Capstone-Baby-Vision-Bridge` — 고객 기기(라즈베리파이/PC)에서 실행되는 카메라 캡처 클라이언트

## 실행 방법

```bash
# 루트에서 전체 서비스 실행
cp .env.example .env   # 값 채운 후
docker compose up --build
```

## 아키텍처

```
Flutter App  ──HTTP/JWT──►  api (FastAPI, port 8000)
                               │
                         PostgreSQL (port 5432)

vision (YOLO) ──────────────► api (감지 이벤트 전송)
       │
  mediamtx (RTSP, port 8554) ◄── Bridge Client (고객 기기)
       │
  Flutter App (스트림 수신)
```

### 서비스 구성 (`docker-compose.yml`)

| 서비스     | 포트  | 설명                                 |
|-----------|-------|--------------------------------------|
| `api`     | 8000  | FastAPI (빌드: `./api`)              |
| `db`      | 5432  | PostgreSQL 16                        |
| `pgadmin` | 5050  | DB 관리 UI                           |
| `mediamtx`| 8554  | RTSP 스트림 서버 (공식 이미지)        |
| `vision`  | -     | YOLO 감지 루프 (빌드: `./vision`)    |

### 디렉터리 역할

- **`api/`** — FastAPI 앱. `main.py` → lifespan에서 DB 테이블 자동 생성.
  - `routers/` — users, cameras, danger_zones, alerts
  - `db/` — SQLAlchemy async 모델 및 엔진
  - `core/security.py` — JWT, bcrypt
  - `schemas/` — Pydantic 모델

- **`vision/`** — YOLO 감지 루프. `main_vision.py`가 카메라 읽기 → 탐지 → 구역 침범 체크 → api로 이벤트 전송.
  - `models/detector.py` — `PersonDetector` (YOLO 래퍼, class 0=adult / 1=baby)
  - `core/zone_checker.py` — `ZoneManager`, `DangerZone` (Shapely 폴리곤)
  - `utils/drawing.py` — OpenCV 시각화
  - `weights/` — `best.pt` 모델 파일 위치 (.gitignore됨)

- **`mediamtx/mediamtx.yml`** — MediaMTX 설정 파일

## 환경 변수 (`.env`)

| 변수 | 설명 |
|------|------|
| `POSTGRES_USER/PASSWORD/DB` | PostgreSQL 접속 정보 |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@db:5432/dbname` |
| `SERVER_HOST` | 카메라 RTSP URL 생성 시 사용할 호스트 |
| `PGADMIN_DEFAULT_EMAIL/PASSWORD` | pgAdmin 접속 정보 |

## API 주요 엔드포인트

API 상세 스펙: `docs/api_specs.md` / 이벤트 스키마: `docs/event_schemas.json`

- `POST /users/login` → JWT 토큰
- `GET/POST/DELETE /danger-zones` — 정규화(0~1) 좌표 폴리곤
- `GET /alerts` — 알림 목록
- `GET /cameras` — 카메라 목록 (RTSP URL 포함)

## 데이터베이스

AsyncSQLAlchemy + asyncpg. 모델: `api/db/models.py` (`User`, `Camera`, `DangerZone`, `DetectionEvent`, `Alert`). Alembic 미초기화 — 테이블은 FastAPI 시작 시 자동 생성.

## 코딩 컨벤션

**Python** — PEP 8, `snake_case` 함수/변수, `PascalCase` 클래스.  
**Git** — `feat/fix/docs/refactor/style: 설명` 형식. feature 브랜치에서 작업, PR로 머지.
