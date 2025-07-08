#!/bin/bash

# GPU 환경 설정 스크립트
# Ubuntu/Debian 기반 시스템에서 실행

set -e

echo "🚀 EXLM GPU 환경 설정을 시작합니다..."

# 시스템 정보 확인
echo "📋 시스템 정보 확인 중..."
OS=$(lsb_release -si)
VERSION=$(lsb_release -sr)
ARCH=$(uname -m)

echo "   OS: $OS $VERSION"
echo "   Architecture: $ARCH"

# NVIDIA GPU 확인
echo "🔍 NVIDIA GPU 확인 중..."
if command -v nvidia-smi &> /dev/null; then
    echo "   NVIDIA 드라이버가 설치되어 있습니다."
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
else
    echo "   ❌ NVIDIA 드라이버가 설치되어 있지 않습니다."
    echo "   NVIDIA 드라이버를 먼저 설치해주세요:"
    echo "   https://docs.nvidia.com/cuda/cuda-installation-guide-linux/"
    exit 1
fi

# Docker 설치 확인
echo "🐳 Docker 설치 확인 중..."
if command -v docker &> /dev/null; then
    echo "   Docker가 설치되어 있습니다."
    docker --version
else
    echo "   ❌ Docker가 설치되어 있지 않습니다."
    echo "   Docker를 먼저 설치해주세요:"
    echo "   https://docs.docker.com/engine/install/"
    exit 1
fi

# Docker Compose 설치 확인
echo "📦 Docker Compose 설치 확인 중..."
if command -v docker-compose &> /dev/null; then
    echo "   Docker Compose가 설치되어 있습니다."
    docker-compose --version
else
    echo "   ❌ Docker Compose가 설치되어 있지 않습니다."
    echo "   Docker Compose를 먼저 설치해주세요:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

# NVIDIA Container Toolkit 설치
echo "🔧 NVIDIA Container Toolkit 설치 중..."
if ! dpkg -l | grep -q nvidia-container-toolkit; then
    echo "   NVIDIA Container Toolkit을 설치합니다..."
    
    # 저장소 추가
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    
    # 패키지 업데이트 및 설치
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    
    # Docker 재시작
    sudo systemctl restart docker
    
    echo "   ✅ NVIDIA Container Toolkit 설치 완료"
else
    echo "   ✅ NVIDIA Container Toolkit이 이미 설치되어 있습니다."
fi

# GPU 테스트
echo "🧪 GPU 컨테이너 테스트 중..."
if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi; then
    echo "   ✅ GPU 컨테이너 테스트 성공"
else
    echo "   ❌ GPU 컨테이너 테스트 실패"
    echo "   NVIDIA Container Toolkit 설정을 확인해주세요."
    exit 1
fi

# 환경 변수 설정
echo "⚙️ 환경 변수 설정 중..."
if [ ! -f .env ]; then
    echo "   .env 파일을 생성합니다..."
    cat > .env << EOF
# 데이터베이스
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=exlm_db

# 빌드 환경
BUILD_ENV=gpu

# API 키들 (필요시 설정)
# OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_key
EOF
    echo "   ✅ .env 파일 생성 완료"
else
    echo "   ✅ .env 파일이 이미 존재합니다."
    # BUILD_ENV를 gpu로 설정
    if grep -q "BUILD_ENV=" .env; then
        sed -i 's/BUILD_ENV=.*/BUILD_ENV=gpu/' .env
    else
        echo "BUILD_ENV=gpu" >> .env
    fi
    echo "   ✅ BUILD_ENV를 gpu로 설정했습니다."
fi

# 디렉토리 생성
echo "📁 필요한 디렉토리 생성 중..."
mkdir -p uploads models logs
echo "   ✅ 디렉토리 생성 완료"

# GPU 환경 빌드
echo "🔨 GPU 환경 빌드 중..."
docker-compose -f docker-compose.gpu.yml build

echo ""
echo "🎉 GPU 환경 설정이 완료되었습니다!"
echo ""
echo "다음 명령어로 GPU 환경을 시작할 수 있습니다:"
echo "   make up-gpu"
echo "   또는"
echo "   docker-compose -f docker-compose.gpu.yml up -d"
echo ""
echo "서비스 접속 정보:"
echo "   - 프론트엔드: http://localhost:3000"
echo "   - 백엔드 API: http://localhost:8000"
echo "   - API 문서: http://localhost:8000/docs"
echo "   - Flower: http://localhost:5555"
echo "   - Grafana: http://localhost:3001"
echo ""
echo "GPU 환경에서 문제가 발생하면 다음을 확인해주세요:"
echo "   - nvidia-smi 명령어로 GPU 상태 확인"
echo "   - docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi"
echo "   - make logs-gpu 명령어로 로그 확인" 