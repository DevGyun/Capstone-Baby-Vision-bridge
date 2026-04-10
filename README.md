# Capstone-Baby-VisionBabyGuard-AI
AI 기반 유아 안전 사고 예방 실시간 관제 시스템 > 2026학년도 1학기 기초캡스톤디자인

## 프로젝트 소개
본 프로젝트는 홈캠 영상을 실시간으로 분석하여 유아가 위험 구역(주방, 발코니 등)에 진입할 경우 보호자에게 즉각적인 알림을 보내는 지능형 사고 예방 시스템입니다.

## 주요 기능
실시간 영상 스트리밍: 홈캠(또는 웹캠) 영상을 앱으로 실시간 송출

AI 객체 인식: YOLO 모델을 통해 유아와 성인을 실시간으로 구분

위험 구역 설정: 사용자가 앱에서 직접 위험 구역(Virtual Fence) 지정

침범 감지 알고리즘: 유아가 설정 구역 진입 시 즉시 판별

푸시 알림: 위험 감지 시 스마트폰으로 즉각적인 소리 및 메시지 전림(FCM)

## 기술 스택
#### 1. 언어 (Languages)
   
+ Python: AI 모델 학습 및 영상 처리, 서버 개발에 사용 (메인 언어)

+ Dart: Flutter를 이용한 안드로이드/iOS 앱 개발에 사용

#### 2. 인공지능 및 영상 처리 (AI & Vision)
   
+ YOLOv8 / v11: 영상 속에서 '사람'과 '유아'를 실시간으로 찾아내는 두뇌 역할

+ OpenCV: 웹캠 영상을 읽어오고, 화면에 위험 구역 선을 그리는 시각 효과 담당

#### 3. 백엔드 및 알림 (Backend & Notification)
   
+ FastAPI: AI의 위험 감지 신호를 받아 앱으로 전달하는 가볍고 빠른 서버

+ Firebase (FCM): 스마트폰으로 "위험!" 푸시 알림을 보내주는 구글 서비스

#### 4. 모바일 앱 (Mobile App)
   
+ Flutter: 안드로이드와 아이폰에서 동시에 작동하는 모니터링 앱 구현

## 프로젝트 구조

수정 가능성 多多

```
EyeCatch/
├── .gitignore              # 최상위 깃 설정 (node_modules, venv, .env, .pt 등 모두 제외)
├── README.md               # 프로젝트 전체 실행 방법 및 아키텍처 요약
│
├── docs/                   # ⭐️ [공통 구역] 1주차 필수 합의 문서 (가장 중요!)
│   ├── api_specs.md        # 프론트 <-> 메인 서버 간 API 명세서 (REST API)
│   └── event_schemas.json  # AI 모델 <-> 브릿지 <-> 메인 서버 간 통신할 JSON 데이터 규격
│
├── 1_frontend/             # 📱 [👤 프론트엔드 담당 구역 (React Native/Flutter)]
│   ├── src/                
│   │   ├── components/     # UI (위험 구역 그리는 투명 캔버스, 영상 플레이어)
│   │   ├── screens/        # 메인 관제 화면, 알림 기록 화면, 로그인 등
│   │   ├── services/       # 메인 서버 통신용 API 클라이언트 (Axios)
│   │   └── utils/          # 화면 좌표 <-> 영상 실제 좌표 변환(정규화) 로직
│   └── package.json        
│
├── 2_main_server/          # 🏢 [👤 메인 서버 담당 구역 (Node.js/Spring/FastAPI)]
│   ├── src/                
│   │   ├── routes/         # API 엔드포인트 (구역 저장, 유저 관리, 알림 내역 조회)
│   │   ├── controllers/    # 비즈니스 로직 처리
│   │   ├── models/         # 데이터베이스 스키마 (MySQL / MongoDB 등)
│   │   └── firebase/       # FCM 푸시 알림 전송 모듈 (Firebase Admin SDK)
│   └── .env                # DB 주소, Firebase 키 경로 (깃허브 업로드 X)
│
├── 3_ai_vision/            # 🧠 [👤 백엔드 모델 담당 구역 (Python)]
│   ├── models/             # YOLO-World 또는 MediaPipe 추론 클래스
│   ├── core/               # 위험 구역 계산 로직 (Shapely - 다각형 내 좌표 포함 여부)
│   ├── utils/              # OpenCV 프레임 전처리 및 시각화(Bounding Box 그리기)
│   ├── weights/            # 사전 학습된 모델 파일 (.pt) -> 깃허브 업로드 X
│   └── requirements.txt    
│
└── 4_bridge_service/       # 🌉 [👤 브릿지 담당 구역 (Python/Node/Redis 등)]
    ├── stream_proxy/       # AI가 처리한 실시간 영상을 프론트로 쏴주는 중계 서버 (WebRTC/RTSP)
    ├── event_broker/       # AI의 "위험 감지!" 신호를 메인 서버로 초고속 전달 (Redis Pub/Sub 또는 WebSocket)
    └── config.yaml         # 브릿지 라우팅 설정 파일
```

## 깃허브 규칙

#### 1. 커밋 메시지는 정해진 규칙 따르기: 예) feat: 로그인 기능 추가, fix: 영상 끊김 버그 수정

#### 2. 작업 전 Pull, 작업 후 Push: 항상 최신 코드를 유지

#### 3. Main 브랜치 직접 Push 금지: 각자 브랜치에서 작업 후 Pull Request를 통해 합치기

#### 4. Merge는 하지마세요.

## 🛠️ BabyGuard-AI 팀 코딩 컨벤션

#### 1. 깃(Git) 사용 및 커밋 메시지 규칙
   
+ 가장 중요한 규칙입니다. 누가 무엇을 수정했는지 한눈에 알 수 있어야 합니다.

+ 커밋 메시지 형식: 타입: 요약 내용
   
+ feat: 새로운 기능 추가
   
+ fix: 버그 수정
   
+ docs: 문서 수정 (README, 보고서 등)
   
+ refactor: 코드 리팩토링 (기능 변경 없이 코드 구조만 개선)
   
+ style: 코드 포맷팅, 세미콜론 누락 등 (코드 변경 없음)
   
+ 예시: feat: 유아 인식용 YOLOv8 모델 로드 기능 추가
   
+ 주의: 수정, ㅎㅇ, test 같은 무의미한 커밋 메시지는 절대 금지!

#### 2. 파이썬(Python) 규칙 (AI & Backend 파트)
   
+ 파이썬 표준인 PEP 8을 기본으로 합니다.
   
+ 변수 & 함수명: snake_case (소문자와 언더바 사용)
   
+ 예: baby_coords, detect_person()
   
+ 클래스명: PascalCase (첫 글자 대문자)
   
+ 예: VideoProcessor, NotificationManager
   
+ 들여쓰기: 스페이스 4칸 (Tab 대신 스페이스 권장)
   
+ 주석: 함수 상단에 이 함수가 무엇을 하는지 한 줄 설명을 적어주세요.

#### 3. 다트(Dart/Flutter) 규칙 (App 파트)
   
+ 구글의 공식 가이드를 따릅니다.
   
+ 변수 & 함수명: lowerCamelCase (소문자로 시작, 단어 사이 대문자)
   
+ 예: isDangerZone, updateStream()
   
+ 클래스 & 위젯명: UpperCamelCase (첫 글자 대문자)
   
+ 예: HomeScreen, AlarmButton
   
+ 파일명: snake_case
   
+ 예: home_screen.dart, main_provider.dart

#### 4. 공통 협업 규칙 (The Golden Rules)
      
+ 의미 있는 이름 짓기: a, b, temp1 같은 변수명은 금지입니다. user_id, frame_count처럼 이름을 보고 용도를 알 수 있어야 합니다.
   
+ 함수는 한 가지만 하기: 하나의 함수가 영상도 읽고, AI도 돌리고, 알림도 보내면 안 됩니다. 기능을 쪼개세요.
   
+ 하드코딩 금지: IP 주소, API 키, 파일 경로 등은 코드 중간에 직접 쓰지 말고 파일 상단에 CONSTANT로 선언하거나 별도 설정 파일(.env)에 모아둡니다.
   
+ 작업 전 Pull, 작업 후 Push: 코드를 짜기 전에 반드시 git pull을 해서 최신 상태를 만들고 시작하세요.
