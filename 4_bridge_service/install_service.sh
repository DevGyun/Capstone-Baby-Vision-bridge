#!/bin/bash
# EyeCatch Bridge 부팅 자동실행 설치 스크립트
# 라즈베리파이에서 실행: sudo bash install_service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/eyecatch-bridge.service"
SERVICE_NAME="eyecatch-bridge"

echo "================================================"
echo "  EyeCatch Bridge 자동실행 설치"
echo "================================================"

# 프로젝트 경로가 다를 경우 service 파일 경로 자동 수정
ACTUAL_PATH="$SCRIPT_DIR"
sed -i "s|/home/pi/Capstone-Baby-Vision-bridge/4_bridge_service|$ACTUAL_PATH|g" "$SERVICE_FILE"
echo "경로 설정: $ACTUAL_PATH"

# 서비스 파일 복사
cp "$SERVICE_FILE" /etc/systemd/system/

# systemd 리로드 및 서비스 활성화
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

echo ""
echo "✅ 설치 완료!"
echo ""
echo "유용한 명령어:"
echo "  상태 확인:  sudo systemctl status $SERVICE_NAME"
echo "  로그 보기:  sudo journalctl -u $SERVICE_NAME -f"
echo "  중지:       sudo systemctl stop $SERVICE_NAME"
echo "  비활성화:   sudo systemctl disable $SERVICE_NAME"
echo "================================================"
