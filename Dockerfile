# 1. 베이스 이미지
#FROM python:3.11-slim

FROM chatbot-base

# 2. 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libmariadb-dev \
    pkg-config \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리
WORKDIR /backend

# 4. pip 최신화 + 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=10
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --upgrade pip

# 5. requirements 분리 설치 (빌드 최적화 목적)
COPY requirements/ ./requirements/

# ✅ 먼저 base만 설치 (빨리 캐시됨)
RUN pip install --no-cache-dir --prefer-binary -r requirements/base.txt

# ✅ inference는 무거우므로 따로 설치 → 캐시 추적 가능
RUN pip install --no-cache-dir --prefer-binary -r requirements/inference.txt

# (선택) 개발 도구 설치
# RUN pip install --no-cache-dir -r requirements/dev.txt

# 6. 전체 프로젝트 복사
COPY . .

# 7. 개발 서버 실행
CMD ["python", "manage.py", "runserver", "0.0.0.0:11234"]
