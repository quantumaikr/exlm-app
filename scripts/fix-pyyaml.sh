#!/bin/bash

# PyYAML 빌드 오류 해결 스크립트
# Python 3.11에서 PyYAML 설치 오류 발생 시 사용

set -e

echo "🔧 PyYAML 빌드 오류 해결 중..."
echo "================================"

# 컬러 출력 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 디렉토리 확인
if [ ! -f "app/main.py" ]; then
    print_error "backend 디렉토리에서 실행해주세요"
    exit 1
fi

# 가상환경 활성화
if [ -d "venv" ]; then
    print_status "가상환경 활성화 중..."
    source venv/bin/activate
else
    print_error "가상환경이 없습니다. 먼저 가상환경을 생성해주세요"
    exit 1
fi

# 기존 PyYAML 제거
print_status "기존 PyYAML 제거 중..."
pip uninstall -y PyYAML 2>/dev/null || true

# pip 업그레이드
print_status "pip 업그레이드 중..."
pip install --upgrade pip setuptools wheel build -q

# 방법 1: --no-build-isolation 옵션으로 설치
print_status "방법 1: --no-build-isolation 옵션으로 PyYAML 설치 시도..."
if pip install "PyYAML==6.0.1" --no-build-isolation -q; then
    print_success "PyYAML 설치 성공!"
    exit 0
else
    print_warning "방법 1 실패, 방법 2 시도..."
fi

# 방법 2: 시스템 패키지로 설치
print_status "방법 2: 시스템 패키지로 PyYAML 설치 시도..."
if apt update -qq && apt install -y python3-yaml; then
    print_success "시스템 PyYAML 설치 성공!"
    exit 0
else
    print_warning "방법 2 실패, 방법 3 시도..."
fi

# 방법 3: 이전 버전으로 설치
print_status "방법 3: 이전 버전으로 PyYAML 설치 시도..."
if pip install "PyYAML==5.4.1" -q; then
    print_success "PyYAML 5.4.1 설치 성공!"
    exit 0
else
    print_warning "방법 3 실패, 방법 4 시도..."
fi

# 방법 4: 소스에서 빌드
print_status "방법 4: 소스에서 PyYAML 빌드 시도..."
pip install "PyYAML==6.0.1" --no-binary :all: -q

print_success "PyYAML 설치 완료!"

# 설치 확인
print_status "설치 확인 중..."
python -c "import yaml; print(f'PyYAML: {yaml.__version__}')" 2>/dev/null || print_error "PyYAML 설치 실패"

print_success "PyYAML 문제 해결 완료!" 