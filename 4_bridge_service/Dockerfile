FROM python:3.11-slim

WORKDIR /bridge

# FFmpeg 설치 (핵심!)
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행
CMD ["python", "main.py"]
