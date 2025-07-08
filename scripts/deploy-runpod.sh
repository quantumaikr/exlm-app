#!/bin/bash

# EXLM Platform RunPod Deployment Script
# Usage: ./deploy-runpod.sh [TOKEN]

set -e

echo "🚀 EXLM Platform RunPod 배포 시작..."

# GitHub Personal Access Token 확인
if [ -z "$1" ]; then
    echo "❌ GitHub Personal Access Token이 필요합니다."
    echo "사용법: ./deploy-runpod.sh YOUR_GITHUB_TOKEN"
    echo ""
    echo "GitHub Token 생성 방법:"
    echo "1. GitHub → Settings → Developer settings → Personal access tokens"
    echo "2. 'Generate new token' 클릭"
    echo "3. 권한: repo, read:org 선택"
    exit 1
fi

GITHUB_TOKEN=$1
REPO_URL="https://${GITHUB_TOKEN}@github.com/quantumaikr/exlm-app.git"

# 시스템 업데이트
echo "📦 시스템 업데이트 중..."
apt-get update -qq
apt-get install -y git curl wget

# Docker 및 Docker Compose 설치 확인
if ! command -v docker &> /dev/null; then
    echo "🐳 Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Docker Compose 설치 중..."
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 저장소 클론
echo "📥 저장소 클론 중..."
if [ -d "exlm-app" ]; then
    echo "기존 디렉토리 제거 중..."
    rm -rf exlm-app
fi

git clone $REPO_URL
cd exlm-app

# 환경 변수 설정
echo "⚙️ 환경 변수 설정 중..."
cat > .env << EOF
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123!
POSTGRES_DB=exlm_db

# Build Environment
BUILD_ENV=gpu

# API Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs (선택사항 - 필요시 설정)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here

# HuggingFace
HF_TOKEN=your_huggingface_token_here

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin123!
EOF

# 필요한 디렉토리 생성
echo "📁 디렉토리 구조 생성 중..."
mkdir -p uploads models logs

# NVIDIA Container Toolkit 설치 (GPU 사용)
echo "🔧 NVIDIA Container Toolkit 설치 중..."
if command -v nvidia-smi &> /dev/null; then
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add - \
    && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    
    apt-get update
    apt-get install -y nvidia-docker2
    systemctl restart docker
    
    echo "✅ GPU 지원 활성화됨"
else
    echo "⚠️ NVIDIA GPU가 감지되지 않음. CPU 모드로 실행됩니다."
fi

# Docker 이미지 빌드
echo "🏗️ Docker 이미지 빌드 중..."
if command -v nvidia-smi &> /dev/null; then
    docker-compose -f docker-compose.gpu.yml build
else
    docker-compose build
fi

# 서비스 시작
echo "🚀 서비스 시작 중..."
if command -v nvidia-smi &> /dev/null; then
    docker-compose -f docker-compose.gpu.yml up -d
else
    docker-compose up -d
fi

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 30

echo "📊 서비스 상태 확인 중..."
if command -v nvidia-smi &> /dev/null; then
    docker-compose -f docker-compose.gpu.yml ps
else
    docker-compose ps
fi

# 포트 정보 출력
echo ""
echo "🎉 배포 완료!"
echo ""
echo "📡 접속 정보:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API 문서: http://localhost:8000/docs"
echo "- Grafana: http://localhost:3001 (admin/admin123!)"
echo "- Prometheus: http://localhost:9090"
echo "- Flower (Celery): http://localhost:5555"
echo ""
echo "🔧 관리 명령어:"
echo "- 로그 확인: docker-compose logs -f"
echo "- 서비스 재시작: docker-compose restart"
echo "- 서비스 중지: docker-compose down"
echo ""
echo "⚠️ RunPod에서 다음 포트들을 Public으로 설정하세요:"
echo "- 3000 (Frontend)"
echo "- 8000 (Backend API)"
echo "- 3001 (Grafana - 선택사항)"
echo "- 9090 (Prometheus - 선택사항)"
echo "- 5555 (Flower - 선택사항)" 